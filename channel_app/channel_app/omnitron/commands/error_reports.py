from omnisdk.omnitron.endpoints import ChannelErrorReportEndpoint, \
    ContentTypeEndpoint
from omnisdk.omnitron.models import ErrorReport

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.data import ErrorReportDto
from channel_app.omnitron.constants import CONTENT_TYPE_IDS


class CreateAddressErrorReports(OmnitronCommandInterface):
    endpoint = ChannelErrorReportEndpoint

    def get_data(self) -> list:
        data = self.objects
        return data

    def send(self, validated_data) -> object:
        endpoint = self.endpoint(
            channel_id=self.integration.channel_id,
            raw=True,
            path=validated_data["type"])
        obj = endpoint.create(item=validated_data)
        return obj

    def row_send_error_report(self):
        pass

    def send_error_report(self, raw_request, raw_response):
        pass

    def check_run(self, is_ok, formatted_data):
        return False

class CreateErrorReports(OmnitronCommandInterface):
    endpoint = ChannelErrorReportEndpoint

    def get_data(self) -> object:
        return self.objects

    def validated_data(self, data):
        assert isinstance(data, ErrorReportDto)
        return data

    def send(self, validated_data: ErrorReportDto) -> object:
        error_report = ErrorReport(
            action_content_type=self.get_content_type(
                validated_data.action_content_type),
            action_object_id=validated_data.action_object_id,
            target_content_type=self.get_content_type(
                validated_data.target_content_type or "channel"),
            target_object_id=validated_data.target_object_id or self.integration.channel_id,
            obj_modified_date=validated_data.modified_date,
            error_code=validated_data.error_code or "custom",
            error_desc=validated_data.error_description or "custom",
            raw_request=validated_data.raw_request,
            raw_response=validated_data.raw_response,
            is_ok=validated_data.is_ok
        )
        report = self.endpoint(
            channel_id=self.integration.channel_id).create(item=error_report)
        return [report]

    def get_content_type(self, content_type: str):
        try:
            return CONTENT_TYPE_IDS[content_type]
        except KeyError:
            pass
        content_type = ContentTypeEndpoint().list(
            params={"model": content_type})
        if not content_type:
            raise Exception("Invalid Content Type")
        if len(content_type) > 1:
            raise Exception("Invalid Content Type")

        content_type_id = content_type[0].id
        CONTENT_TYPE_IDS[content_type[0].model] = content_type_id
        return content_type_id

    def row_send_error_report(self):
        pass

    def send_error_report(self, raw_request, raw_response):
        pass

    def check_run(self, is_ok, formatted_data):
        return False
