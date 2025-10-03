from contextlib import contextmanager
import json
import os
import traceback
from typing import Optional
import uuid
from datetime import datetime, timezone
import boto3
from sqlalchemy.orm import scoped_session, sessionmaker

from channel_app.database.models import (
    LogFlowModel,
    LogStepExceptionModel,
    LogStepModel,
)
from channel_app.database.services import DatabaseService
from channel_app.logs.encoders import UUIDEncoder
from channel_app.logs.enums import LogFlowAuthor, LogStepStatus


class LogService:
    database_service = DatabaseService()

    def __init__(self):
        self.flow = {}
        self.steps = []
        self.exceptions = []

        self.db_engine = self.database_service.create_engine()
        self.s3_client = S3Client()

    def create_flow(
        self,
        name: str,
        transaction_id: str = None,
        flow_author: LogFlowAuthor = LogFlowAuthor.system,
    ):
        self.flow = {
            "id": uuid.uuid4(),
            "transaction_id": transaction_id or str(uuid.uuid4()),
            "flow_name": name,
            "flow_author": flow_author.value,
            "started_at": datetime.now(timezone.utc),
        }

    @contextmanager
    def step(self, name: str, metadata: Optional[dict] = None):
        now = datetime.now(timezone.utc)
        self._add_step(name, start=True, metadata=metadata)
        try:
            yield
            self._add_step(name, end=True)
        except Exception as exc:
            self.add_exception(exc)
            for step in reversed(self.steps):
                if (
                    step["step_name"] == name
                    and step.get("status") == LogStepStatus.in_progress.value
                ):
                    step["end_time"] = now
                    step["status"] = LogStepStatus.failure.value
                    step["error"] = str(exc)
                    break
            raise

    def _add_step(self, name, start=False, end=False, metadata=None):
        now = datetime.now(timezone.utc)
        if start:
            self.steps.append(
                {
                    "id": uuid.uuid4(),
                    "step_name": name,
                    "start_time": now,
                    "status": LogStepStatus.in_progress.value,
                    "metadata": metadata or {},
                }
            )
        elif end:
            for step in reversed(self.steps):
                if (
                    step["step_name"] == name
                    and step["status"] == LogStepStatus.in_progress.value
                ):
                    step["end_time"] = now
                    step["status"] = LogStepStatus.success.value
                    step["duration_ms"] = int(
                        (now - step["start_time"]).total_seconds() * 1000
                    )

    def add_exception(self, exc: Exception):
        tb = traceback.format_exc()
        exc_obj = {
            "id": uuid.uuid4(),
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": tb,
        }
        self.exceptions.append(exc_obj)
        # If this flow has related step, update the step to FAILURE
        if self.steps:
            self.steps[-1]["status"] = LogStepStatus.failure.value
            self.steps[-1]["error"] = str(exc)
            self.steps[-1].setdefault("exceptions", []).append(exc_obj)

    def save(self):
        self.flow["ended_at"] = datetime.now(timezone.utc)
        full_log_content = {
            **self.flow,
            "steps": self.steps,
            "exceptions": self.exceptions,
        }
        s3_key = f"logs/{self.flow['flow_name']}/{self.flow['transaction_id']}.json"

        self.s3_client.upload_object(s3_key, full_log_content)

        log_flow_object = LogFlowModel(
            id=self.flow["id"],
            transaction_id=str(self.flow["transaction_id"]),
            flow_name=self.flow["flow_name"],
            flow_author=self.flow["flow_author"],
            started_at=self.flow["started_at"],
            ended_at=self.flow["ended_at"],
            status=(
                self.steps[-1]["status"] if self.steps else LogStepStatus.failure.value
            ),
            s3_key=s3_key,
        )
        
        step_models = []
        exception_models = []
        for step in self.steps:
            step_model = LogStepModel(
                id=step["id"],
                flow_id=self.flow["id"],
                step_name=step["step_name"],
                status=step["status"],
                start_time=step["start_time"],
                end_time=step.get("end_time"),
                duration_ms=step.get("duration_ms"),
                error_message=step.get("error"),
                step_metadata=step.get("metadata"),
            )
            step_models.append(step_model)

            for exc in step.get("exceptions", []):
                exception_models.append(
                    LogStepExceptionModel(
                        id=exc["id"],
                        step_id=step["id"],
                        type=exc["type"],
                        message=exc["message"],
                        traceback=exc["traceback"],
                        created_at=self.flow["ended_at"],
                    )
                )
        
        self._save_to_db(log_flow_object, step_models, exception_models)

    def _save_to_db(self, flow_obj, step_objs, exception_objs):
        session = scoped_session(sessionmaker(bind=self.db_engine))
        try:
            session.add(flow_obj)
            session.add_all(step_objs)
            if exception_objs:
                session.add_all(exception_objs)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class S3Client:
    def __init__(self):
        self._validate_credentials()
        self.client = boto3.client("s3")
        self.bucket = os.getenv("S3_BUCKET_NAME", "default-bucket-name")

    def _validate_credentials(self):
        required_env_vars = {
            "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
            "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "AWS_REGION": os.getenv("S3_REGION_NAME"),
            "S3_BUCKET_NAME": os.getenv("S3_BUCKET_NAME"),
        }

        missing_vars = [
            name for name, value in required_env_vars.items() if value is None
        ]

        if missing_vars:
            raise ValueError(
                f"S3 Client initialization failed: missing AWS credentials: {', '.join(missing_vars)}"
            )

    def set_bucket(self, bucket_name: str):
        self.bucket = bucket_name
        return self

    def upload_object(self, key: str, content: dict):
        try:
            body = json.dumps(content, indent=2, cls=UUIDEncoder).encode("utf-8")
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType="application/json",
            )
        except Exception as e:
            print(f"[S3 Upload Error] {e}")
            raise
