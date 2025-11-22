from datetime import datetime, timezone
import uuid
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Enum as SqlEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship

from channel_app.logs.enums import LogFlowAuthor, LogStepStatus


class Base(DeclarativeBase):
    pass


class LogFlowModel(Base):
    __tablename__ = "log_flows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), unique=True, nullable=False)
    flow_name = Column(String(255), nullable=False)
    flow_author = Column(SqlEnum(LogFlowAuthor), default=LogFlowAuthor.system, nullable=False)

    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(SqlEnum(LogStepStatus), nullable=True)
    s3_key = Column(Text, nullable=True)

    def __repr__(self):
        return f"<FlowLog(transaction_id={self.transaction_id}, flow_name={self.flow_name})>"
    

class LogStepModel(Base):
    __tablename__ = "log_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("log_flows.id", ondelete="CASCADE"), nullable=False)
    step_name = Column(String(255), nullable=False)
    status = Column(SqlEnum(LogStepStatus, native_enum=False), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    error_message = Column(String)
    step_metadata = Column(JSON)

    exceptions = relationship("LogStepExceptionModel", back_populates="step", cascade="all, delete-orphan")
    

class LogStepExceptionModel(Base):
    __tablename__ = "log_step_exceptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_id = Column(UUID(as_uuid=True), ForeignKey("log_steps.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(128), nullable=False)
    message = Column(String)
    traceback = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False)

    step = relationship("LogStepModel", back_populates="exceptions")
