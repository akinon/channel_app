import random
import uuid
from typing import List, Any, Tuple

from omnisdk.omnitron.models import Product, BatchRequest

from channel_app.core.commands import CommandInterface, ChannelCommandInterface
from channel_app.core.data import ProductBatchRequestResponseDto, ErrorReportDto
from channel_app.omnitron.constants import ResponseStatus


class SendInsertedProducts(ChannelCommandInterface):
    param_sync = True

    def get_data(self) -> List[Product]:
        data = self.objects
        return data

    def validated_data(self, data) -> object:
        return data

    def transform_data(self, data) -> object:
        return data

    def send_request(self, transformed_data) -> object:
        response = self.__mocked_request(data=transformed_data)
        return response

    def normalize_response(self, data, validated_data, transformed_data,
                           response) -> Tuple[
         List[ProductBatchRequestResponseDto], List[ErrorReportDto], Any]:
        report: List[ErrorReportDto] = self.create_report(response)
        if not self.param_sync:
            remote_batch_id = response.get("remote_batch_request_id")
            self.batch_request.remote_batch_id = remote_batch_id
            return "", report, data
        else:
            response_data = []
            for row in response:
                response_data.append(ProductBatchRequestResponseDto(
                    sku=row["sku"],
                    message=row["message"],
                    remote_id=row["remote_id"],
                    status=row["status"]
                ))

            response_data: List[ProductBatchRequestResponseDto]
            return response_data, report, data

    def __mocked_request(self, data):
        """
        Mock a request and response for the send operation to mimic actual channel data
        :param data:
        """
        batch_id = str(uuid.uuid4())
        self.integration._sent_data[batch_id] = data
        return {"remote_batch_request_id": batch_id}

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


class SendUpdatedProducts(SendInsertedProducts):
    pass


class SendDeletedProducts(SendInsertedProducts):
    def __mocked_request(self, data):
        """
        Mock a request and response for the send operation to mimic actual channel data
        :param data:
        """
        batch_id = str(uuid.uuid4())
        self.integration._sent_data[batch_id] = data
        return {"remote_batch_request_id": batch_id}


class CheckProducts(ChannelCommandInterface):

    def get_data(self) -> BatchRequest:
        batch_request = self.objects
        return batch_request

    def validated_data(self, data) -> object:
        return data

    def transform_data(self, data) -> object:
        return data

    def send_request(self, transformed_data: BatchRequest) -> object:
        """
            Sends a post request to the channel client to insert the products
        :param transformed_data:
        :return: list
            [{ remote_data},]
        """

        response = self.__mocked_request(
            data=self.integration._sent_data[transformed_data.remote_batch_id],
            remote_batch_id=transformed_data.remote_batch_id)
        return response

    def normalize_response(self, data, validated_data, transformed_data,
                       response) -> Tuple[List[ProductBatchRequestResponseDto],
                                          List[ErrorReportDto], Any]:
        response_data = []
        for row in response:
            obj = ProductBatchRequestResponseDto(
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
        :return: list

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


class CheckDeletedProducts(CheckProducts):
    pass
