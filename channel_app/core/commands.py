import logging
import traceback
from datetime import datetime
from io import StringIO
from typing import List, Any

from omnisdk.omnitron.models import BatchRequest
from requests import HTTPError, Request, Response

from channel_app.core.data import ErrorReportDto
from channel_app.core.integration import BaseIntegration
from channel_app.omnitron.batch_request import ClientBatchRequest
from channel_app.omnitron.constants import BatchRequestStatus, ContentType
from channel_app.omnitron.exceptions import (CountryException, CityException,
                                             TownshipException,
                                             DistrictException)

logger = logging.getLogger(__name__)


class LogService(object):
    pass


class CommandInterface(object):
    def get_data(self) -> object:
        """
        This method fetches the input data for the command.
        """
        raise NotImplementedError()

    def transform_data(self, data) -> object:
        """
        This method can be used to format the input data before it is executed on the run method.
        """
        raise NotImplementedError()

    def validated_data(self, data) -> dict:
        """
        If the input data needs to satisfy some conditions or contain required a parameter, the
        validation is done here.
        """
        return data

    def send(self, validated_data) -> object:
        """
        If the command sends a request using input data to achieve the main object of the
        command, it is recommended to place those operations in this method.

        :param validated_data:
        """
        raise NotImplementedError()


class ChannelCommandInterface(CommandInterface):
    def __init__(self, integration, objects=None, batch_request=None, **kwargs):
        self.objects = objects
        self.integration = integration
        self.batch_request = batch_request
        self.failed_object_list = []
        self.session = integration._session
        self.CHUNK_SIZE = 50
        self.BATCH_SIZE = 100

        for key, value in kwargs.items():
            setattr(self, "param_{}".format(key), value)

    def get_data(self) -> object:
        raise NotImplementedError

    def validated_data(self, data) -> object:
        raise NotImplementedError

    def transform_data(self, data) -> object:
        raise NotImplementedError

    def send_request(self, transformed_data) -> object:
        """
        If the command sends a request using input data to achieve the main object of the
        command, it is recommended to place those operations in this method.
        """
        raise NotImplementedError()

    def normalize_response(self, data, validated_data, transformed_data,
                           response):
        raise NotImplementedError

    def run(self):
        """
        Main flow of the command. `do_action` method of the integration class executes this method.
        This method must also call necessary command interface methods.
        :return: returns to response of the command if it has one.
        """
        data = self.get_data()
        validated_data = self.validated_data(data)
        transformed_data = self.transform_data(validated_data)
        response = self.send_request(transformed_data=transformed_data)
        normalize_data = self.normalize_response(
            data=data,
            validated_data=validated_data,
            transformed_data=transformed_data,
            response=response)
        return normalize_data

    def create_report(self, response):
        if not self.is_batch_request:
            return
        name = self.__class__.__name__
        report_list = []
        report = ErrorReportDto(
            action_content_type=ContentType.batch_request.value,
            action_object_id=self.batch_request.pk,
            modified_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            error_code=f"{self.batch_request.local_batch_id}-{name}",
            error_description=f"{self.batch_request.local_batch_id}-{name}",
            raw_request=f"{response.request.method}-"
                        f"{response.request.url}-"
                        f"{response.request.body}",
            raw_response=f"{response.text}"
        )
        is_ok = self.check_response_is_ok(response=response)
        if is_ok:
            report.is_ok = True
        else:
            report.is_ok = False
        report_list.append(report)
        for failed_obj in self.failed_object_list:
            raw_report = ErrorReportDto(
                action_content_type=failed_obj[1],
                action_object_id=failed_obj[0].pk,
                modified_date=failed_obj[0].modified_date,
                error_code=f"{self.batch_request.local_batch_id}-{name}",
                error_description=f"{self.batch_request.local_batch_id}-{name}",
                raw_request="",
                raw_response=f"{failed_obj[0].failed_reason_type}-{failed_obj[2]}",
                is_ok=False
            )
            report_list.append(raw_report)
        return report_list

    def check_response_is_ok(self, response):
        if str(response.status_code).startswith("2"):
            return True
        return False

    @property
    def is_batch_request(self) -> bool:
        is_object = getattr(
            self, 'batch_request', None)
        return bool(is_object)


class OmnitronCommandInterface(CommandInterface):
    """
    Commands implement list of steps to achieve a task. A command can contain a simple get request
    or a complicated business logic with lots of validation.

    """
    batch_service = ClientBatchRequest
    content_type = None

    def __init__(self, integration: BaseIntegration, objects: Any = None,
                 batch_request: BatchRequest = None, **kwargs):
        """
        :param integration: Integration object
        :param objects: Input to the command
        :param batch_request: Related batch request to keep track of the whole task

        """
        self.objects = objects
        self.batch_request = batch_request
        self.integration = integration
        self.failed_object_list = []
        for key, value in kwargs.items():
            setattr(self, "param_{}".format(key), value)

    def get_data(self) -> object:
        return self.objects

    def send(self, validated_data) -> object:
        return validated_data

    def normalize_response(self, data, response) -> List[object]:
        return response

    def run(self) -> Any:
        """
        Main flow of the command. `do_action` method of the integration class executes this method.
        This method must also call necessary command interface methods.
        :return: Response of the command or None
        """
        is_ok = True
        formatted_data = None
        raw_request, raw_response = None, None
        try:
            model_items = self.validated_data(self.get_data())
            response = self.send(validated_data=model_items)
            normalize_data = self.normalize_response(data=model_items,
                                                     response=response)
            if isinstance(normalize_data, list):
                formatted_data = [model_obj for model_obj in normalize_data
                                  if
                                  not getattr(model_obj, "failed_reason_type",
                                              None)]
            self.row_send_error_report()
        except HTTPError as e:
            request = e.request
            raw_request = f"{request.method} - {request.url} - {request.body}"
            raw_response = e.response.text
            is_ok = False
            logger.error(f"{raw_request}-/-{raw_response}")
        except CountryException as e:
            is_ok = False
            raw_response = str(e.params)
        except (CityException, TownshipException, DistrictException) as e:
            is_ok = False
            self.integration.do_action(
                key='create_address_error_report',
                objects=e.params)
            raw_response = str(e.params)
        except Exception as e:
            is_ok = False
            raw_response = f"{str(e)} - {traceback.format_exc()}"
            request = getattr(e, "request", "")
            if request:
                raw_request = f"{request.method} - {request.url} - {request.body}"
            logger.error(f"{raw_request}-/-{raw_response}")

        finally:
            if not is_ok:
                self.send_error_report(raw_request, raw_response)

        is_check_and_update_batch_service = self.check_run(
            is_ok=is_ok, formatted_data=formatted_data)
        if not is_check_and_update_batch_service:
            return []

        return formatted_data

    def check_run(self, is_ok, formatted_data):
        if is_ok and not formatted_data and self.is_batch_request:
            self.batch_service(self.integration.channel_id).to_done(
                self.integration.batch_request)
            return False
        elif not is_ok and self.is_batch_request:
            self.integration.batch_request.objects = None
            self.batch_service(self.integration.channel_id).to_fail(
                self.integration.batch_request)
            return False
        return True

    def row_send_error_report(self):
        name = self.__class__.__name__
        for failed_obj in self.failed_object_list:
            report = ErrorReportDto(
                action_content_type=failed_obj[1],
                action_object_id=failed_obj[0].pk,
                modified_date=failed_obj[0].modified_date,
                error_code=f"{self.integration.batch_request.local_batch_id}-{name}",
                error_description=f"{self.integration.batch_request.local_batch_id}-{name}",
                raw_request="",
                raw_response=f"{failed_obj[0].failed_reason_type}-{failed_obj[2]}",
                is_ok=False
            )
            self.integration.do_action(key='create_error_report',
                                       objects=report)

    def send_error_report(self, raw_request, raw_response):
        if not self.is_batch_request:
            return

        name = self.__class__.__name__

        report = ErrorReportDto(
            action_content_type=ContentType.batch_request.value,
            action_object_id=self.integration.batch_request.pk,
            modified_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            error_code=f"{self.integration.batch_request.local_batch_id}-{name}",
            error_description=f"{self.integration.batch_request.local_batch_id}-{name}",
            raw_request=raw_request,
            raw_response=raw_response
        )
        self.integration.do_action(
            key='create_error_report',
            objects=report)

    @property
    def is_batch_request(self) -> bool:
        is_object = getattr(
            self.integration, 'batch_request', None)
        return bool(is_object)

    def create_log_file(self, message: str = None, raw_request: Request = None,
                        raw_response: Response = None, **kwargs):
        """
        Log files are attached to batch requests. If you need to attach logs
        to a problematic command or want to see detailed logs for standard a
        command, you can use this method. However, if you do not use a batch request
        for a command and still want to see the logs, You will need to manage the command
        with a batch request.

        :param message: Reason of the exception/entry logged
        :param raw_request:
        :param raw_response:
        """
        bytes_io = StringIO()
        if raw_request and raw_response:
            context = f"""
            "message": {message},
            "url": {raw_request.url},
            "request_body": {raw_request.body},
            "response_text": {raw_response.text},
            "response_reason": {raw_response.reason},
            "response_status_code": {raw_response.status_code}
            """
        else:
            context = f"""
                        "message": {message}
                        """
        bytes_io.write(context)
        bytes_io.seek(0)
        return bytes_io

    @property
    def update_state(self, *args, **kwargs) -> BatchRequestStatus:
        return BatchRequestStatus.commit

    def update_batch_request(self, objects_data: list):
        """
        Batch requests are used to track state of long-running processes across multiple
        systems. State of those requests can be managed through this method.

        :param content_type: String values of the ContentType enum model
        :param remote_batch_id: Batch request id of the
        :param objects_data:

        """
        self.integration.batch_request.objects = objects_data
        service = self.batch_service(self.integration.channel_id)
        state = getattr(service, f'to_{self.update_state.value}')(
            self.integration.batch_request)
        return state

    def create_batch_objects(self, data: list, content_type: str) -> List[dict]:
        """
        In batch requests, you can attach Omnitron objects that are being processed in that batch
        so that they are excluded from further calls until that batch is finalized with done or
        fail statuses.

        :param data: List of objects which are being processed for this batch request
        :param content_type: String values of the ContentType enum model

        """
        objects = []
        for item in data:
            object = {
                "pk": item.pk,
                "failed_reason_type": getattr(item, "failed_reason_type", None),
                "remote_id": getattr(item, "remote_id", None),
                "version_date": item.modified_date,
                "content_type": content_type
            }
            objects.append(object)
        return objects
