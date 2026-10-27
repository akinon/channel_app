from omnisdk.omnitron.endpoints import ChannelOperationalEventEndpoint
from omnisdk.omnitron.models import OperationalEvent

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.data import OperationalEventDto


class CreateOperationalEvent(OmnitronCommandInterface):
    endpoint = ChannelOperationalEventEndpoint

    def get_data(self) -> object:
        return self.objects

    def validated_data(self, data):
        assert isinstance(data, OperationalEventDto)
        return data

    def send(self, validated_data: OperationalEventDto) -> object:
        event = OperationalEvent(
            event_type=validated_data.event_type,
            level=validated_data.level,
            source=validated_data.source,
            message=validated_data.message,
            context=validated_data.context or {},
            tags=validated_data.tags or {},
            action_content_type=validated_data.action_content_type,
            action_object_id=validated_data.action_object_id,
            trace_id=validated_data.trace_id,
            span_id=validated_data.span_id,
            parent_span_id=validated_data.parent_span_id,
            raw_data=validated_data.raw_data,
        )
        result = self.endpoint(
            channel_id=self.integration.channel_id
        ).create(item=event)
        return [result]

    def row_send_error_report(self):
        pass

    def send_error_report(self, raw_request, raw_response):
        pass

    def check_run(self, is_ok, formatted_data):
        return False


class GetOperationalEvents(OmnitronCommandInterface):
    endpoint = ChannelOperationalEventEndpoint

    def get_data(self):
        return self.objects

    def send(self, validated_data) -> list:
        params = validated_data or {}
        results = self.endpoint(
            channel_id=self.integration.channel_id
        ).list(params=params)
        return results

    def row_send_error_report(self):
        pass

    def send_error_report(self, raw_request, raw_response):
        pass

    def check_run(self, is_ok, formatted_data):
        return False
