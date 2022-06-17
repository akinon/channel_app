from omnisdk.omnitron.endpoints import ChannelBatchRequestEndpoint
from omnisdk.omnitron.models import BatchRequest

from channel_app.omnitron.constants import BatchRequestStatus


class ClientBatchRequest(object):
    """
    Batch requests work as a state machine. They are used to track state of a flow that must
    be running across multiple systems. It starts at initialized state.
    """
    def __init__(self, channel_id):
        self.channel_id = channel_id
        self.endpoint = ChannelBatchRequestEndpoint()

    def create(self) -> BatchRequest:
        batch_request = BatchRequest(channel=self.channel_id)
        return self.endpoint(channel_id=self.channel_id).create(item=batch_request)

    def to_commit(self, batch_request: BatchRequest) -> BatchRequest:
        """
        Once objects are fetched by Channel app, state is updated to commit and object
        integration are marked(if sent) on Omnitron side.
        :param batch_request:
        :return:
        """
        br = BatchRequest(channel=self.channel_id)
        br.objects = batch_request.objects
        br.status = BatchRequestStatus.commit.value
        br.content_type = batch_request.content_type
        batch_request.status = br.status
        return self.endpoint(channel_id=self.channel_id).update(id=batch_request.pk, item=br)

    def to_sent_to_remote(self, batch_request: BatchRequest) -> BatchRequest:
        """
        If objects are sent to channel, state must be updated to sent_to_remote
        and channel batch id is stored if it sent one.
        :param batch_request:
        :return:
        """
        br = BatchRequest(channel=self.channel_id)
        br.remote_batch_id = batch_request.remote_batch_id
        br.status = BatchRequestStatus.sent_to_remote.value
        batch_request.status = br.status
        return self.endpoint(channel_id=self.channel_id).update(
            id=batch_request.pk, item=br)

    def to_ongoing(self, batch_request: BatchRequest) -> BatchRequest:
        """
        If channel has not finished the batch yet, once we query for it after an interval, we
        update the state to ongoing.
        :param batch_request:
        :return:
        """
        br = BatchRequest(channel=self.channel_id)
        br.status = BatchRequestStatus.ongoing.value
        batch_request.status = br.status
        return self.endpoint(channel_id=self.channel_id).update(
            id=batch_request.pk, item=br)

    def to_fail(self, batch_request: BatchRequest) -> BatchRequest:
        """
        If channel fails completing the batch, batch request is finalized with fail state.
        :param batch_request:
        :return:
        """
        br = BatchRequest(channel=self.channel_id)
        br.objects = batch_request.objects
        br.status = BatchRequestStatus.fail.value
        batch_request.status = br.status
        return self.endpoint(channel_id=self.channel_id).update(
            id=batch_request.pk, item=br)

    def to_done(self, batch_request: BatchRequest) -> BatchRequest:
        """
        If all objects are processed disregarding the fact that they succeeded or failed,
        batch request is finalized with done.
        :param batch_request:
        :return:
        """
        br = BatchRequest(channel=self.channel_id)
        br.objects = batch_request.objects
        br.status = BatchRequestStatus.done.value
        batch_request.status = br.status
        return self.endpoint(channel_id=self.channel_id).update(
            id=batch_request.pk, item=br)

