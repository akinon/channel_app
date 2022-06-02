import random
import uuid
from typing import Tuple, List, Any

from omnisdk.omnitron.models import ProductPrice, BatchRequest

from channel_app.core.commands import ChannelCommandInterface
from channel_app.core.data import BatchRequestResponseDto, ErrorReportDto
from channel_app.omnitron.constants import ResponseStatus


class SendUpdatedPrices(ChannelCommandInterface):
    param_sync = True

    def get_data(self) -> List[ProductPrice]:
        product_prices = self.objects
        return product_prices

    def validated_data(self, data) -> object:
        return data

    def transform_data(self, data) -> object:
        return data

    def send_request(self, transformed_data) -> object:
        if not self.param_sync:
            response = self.__mocked_request(data=transformed_data)
        else:
            response = self.__mock_request_sync(data=transformed_data)

        return response

    def normalize_response(self, data, validated_data, transformed_data,
                           response) -> Tuple[List[BatchRequestResponseDto],
                                              ErrorReportDto, Any]:
        report = self.create_report(response)
        if not self.param_sync:
            remote_batch_id = response.get("remote_batch_request_id")
            self.batch_request.remote_batch_id = remote_batch_id
            return "", report, data
        else:
            response_data = []
            for row in response:
                response_data.append(BatchRequestResponseDto(
                    sku=row["sku"],
                    message=row["message"],
                    remote_id=row["remote_id"],
                    status=row["status"]
                ))

            response_data: List[BatchRequestResponseDto]
            return response_data, report, data

    def __mock_request_sync(self, data):
        result = []
        for row in data:
            obj = dict(
                sku=row["sku"],
                message=row["message"],
                remote_id=row["remote_id"],
                status=row["status"])
            result.append(obj)
        return result

    def __mocked_request(self, data):
        """
        Mock a request and response for the send operation to mimic actual channel data
        :param data:
        :return:
        """
        batch_id = str(uuid.uuid4())
        self.integration._sent_data[batch_id] = data
        return {"remote_batch_request_id": batch_id}


class SendInsertedPrices(SendUpdatedPrices):
    pass


class CheckPrices(ChannelCommandInterface):
    def get_data(self) -> BatchRequest:
        batch_request = self.objects
        return batch_request

    def validated_data(self, data):
        return data

    def transform_data(self, data) -> object:
        return data

    def send_request(self, transformed_data) -> object:
        """
        Sends a post request to the channel client to check the prices
        param validated_data:
        """

        response = self.__mocked_request(
            data=self.integration._sent_data[transformed_data.remote_batch_id],
            remote_batch_id=transformed_data.remote_batch_id)
        return response

    def normalize_response(self, data, validated_data, transformed_data,
                           response) -> Tuple[List[BatchRequestResponseDto],
                                              ErrorReportDto, Any]:
        response_data = []
        for row in response:
            obj = BatchRequestResponseDto(
                sku=row["sku"],
                message=row["message"],
                remote_id=row["remote_id"],
                status=row["status"])
            response_data.append(obj)
        report = self.create_report(response)
        return response_data, report, data

    def __mocked_request(self, data, remote_batch_id):
        """
        Mock a request and response for the send operation to mimic actual channel data
        :param data:
        :return:

        [{
            "status": "SUCCESS",
            "remote_id": "123a1",
            "sku": "1KBATC0197",
            "message": ""
         },]
        """

        response_data = []
        prefix = remote_batch_id[-8:]
        for index, item in enumerate(data):
            if random.random() < 0.8:
                response_item = {
                    'sku': item.sku,
                    'message': "",
                    'remote_id': "{}_{}".format(prefix, index),
                    'status': ResponseStatus.success
                }
            else:
                response_item = {
                    "status": ResponseStatus.fail,
                    "remote_id": None,
                    "sku": item.sku,
                    "message": "exception message"
                }
            response_data.append(response_item)
        return response_data
