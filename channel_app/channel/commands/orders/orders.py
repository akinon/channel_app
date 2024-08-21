import datetime
from random import random
from typing import Tuple, Any, List

from omnisdk.omnitron.models import Order, BatchRequest

from channel_app.core.commands import ChannelCommandInterface
from channel_app.core.data import (BatchRequestResponseDto, 
                                   CancellationRequestDto, 
                                   ChannelCancellationRequestDto, 
                                   ErrorReportDto, 
                                   ChannelCreateOrderDto, AddressDto, 
                                   CustomerDto, ChannelOrderDto, OrderItemDto, 
                                   OrderBatchRequestResponseDto,
                                   CancelOrderDto, ChannelUpdateOrderItemDto)
from channel_app.omnitron.constants import ResponseStatus


class GetOrders(ChannelCommandInterface):
    def get_data(self):

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
                           response) -> Tuple[ChannelCreateOrderDto,
                                              ErrorReportDto, Any]:
        """
        Convert channel order to the format OmnitronIntegration
        requires
        """
        for response_order_data in response:
            order_data = response_order_data["order"]
            customer_data = order_data.pop("customer")
            shipping_address_data = order_data.pop("shipping_address")
            billing_address_data = order_data.pop("billing_address")

            order_items_data = response_order_data["order_items"]

            shipping_address = AddressDto(**shipping_address_data)

            billing_address = AddressDto(**billing_address_data)

            customer = CustomerDto(**customer_data)

            channel_order_data = {
                "billing_address": billing_address,
                "shipping_address": shipping_address,
                "customer": customer,
                "cargo_company": order_data["cargo_company"]
            }
            channel_order_data.update(order_data)
            channel_order_dto = ChannelOrderDto(**channel_order_data)

            order_items_dto = []
            for order_item_data in order_items_data:
                order_item = OrderItemDto(**order_item_data)
                order_items_dto.append(order_item)

            order_items_dto: List[OrderItemDto]
            channel_create_order = ChannelCreateOrderDto(
                order=channel_order_dto,
                order_item=order_items_dto)

            report = self.create_report(response_order_data)
            yield channel_create_order, report, None

    def __mocked_request(self, data):
        number = str(int(random() * 1000000))
        return [{
            "order": {
                "status": "400",
                "remote_id": number,
                "number": number,
                "channel": "1",
                "currency": "try",
                "amount": "17",
                "shipping_amount": "0.0",
                "shipping_tax_rate": "18",
                "extra_field": {},
                "created_at": str(datetime.datetime.now()),
                "customer": {
                    "email": "dummy@dummy.com",
                    "phone_number": None,
                    "first_name": "Dummy",
                    "last_name": "Dummy",
                    "channel_code": "1212",
                    "extra_field": None,
                    "is_active": True
                },
                "shipping_address": {
                    "email": "dummy@dummy.com",
                    "phone_number": "05540000000",
                    "first_name": "dummy",
                    "last_name": "dummy",
                    "country": "Türkiye",
                    "city": "İstanbul",
                    "line": "dummy 3 dummy cd"
                },
                "billing_address": {
                    "email": "dummy@dummy.com",
                    "phone_number": "05540000000",
                    "first_name": "dummy",
                    "last_name": "dummy",
                    "country": "Türkiye",
                    "city": "İstanbul",
                    "line": "dummy 3 dummy cd"
                },
                "cargo_company": "aras"
            },
            "order_items": [
                {
                    "remote_id": "1234567816",
                    "product": "1234",
                    "price_currency": "try",
                    "price": "17.0",
                    "tax_rate": "18",
                    "retail_price": "20.0",
                    "extra_field": {"tracking_number": "1231"},
                    "status": "400"
                }
            ]
        }]


class SendUpdatedOrders(ChannelCommandInterface):
    param_sync = True

    def get_data(self) -> List[Order]:
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
            List[OrderBatchRequestResponseDto], List[ErrorReportDto], Any]:
        response_data = []
        for row in response:
            obj = OrderBatchRequestResponseDto(
                status=row["status"],
                remote_id=row["remote_id"],
                number=row["number"],
                message=row["message"])
            response_data.append(obj)

        report = self.create_report(response)
        return response_data, report, data

    def __mocked_request(self, data):
        """
        Mock a request and response for the send operation to mimic actual
        channel data

        :return:

        [{
            "status": "SUCCESS",
            "remote_id": "123a1",
            "number": "1234567",
            "message": ""
         },]
        """
        response_data = []
        prefix = "order"
        for index, item in enumerate(data):
            if random() < 0.8:
                response_item = {
                    'number': item.number,
                    'message': "",
                    'remote_id': "{}_{}".format(prefix, index),
                    'status': ResponseStatus.success
                }
            else:
                response_item = {
                    "status": ResponseStatus.fail,
                    "remote_id": None,
                    "number": item.number,
                    "message": "exception message"
                }
            response_data.append(response_item)
        return response_data


class CheckOrders(ChannelCommandInterface):
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
        :return:
            [{ remote_data},]
        """

        response = self.__mocked_request(
            data=self.integration._sent_data[transformed_data.remote_batch_id],
            remote_batch_id=transformed_data.remote_batch_id)
        return response

    def normalize_response(self, data, validated_data, transformed_data,
                           response) -> Tuple[
            List[OrderBatchRequestResponseDto], List[ErrorReportDto], Any]:
        response_data = []
        for row in response:
            obj = OrderBatchRequestResponseDto(
                status=row["status"],
                remote_id=row["remote_id"],
                number=row["number"],
                message=row["message"])
            response_data.append(obj)

        report = self.create_report(response)
        return response_data, report, data

    def __mocked_request(self, data, remote_batch_id):
        """
        Mock a request and response for the send operation to mimic actual
        channel data

        :return:

        [{
            "status": "SUCCESS",
            "remote_id": "123a1",
            "number": "1234567",
            "message": ""
         },]
        """
        response_data = []
        prefix = remote_batch_id[-8:]
        for index, item in enumerate(data):
            if random() < 0.8:
                response_item = {
                    'number': item.number,
                    'message': "",
                    'remote_id': "{}_{}".format(prefix, index),
                    'status': ResponseStatus.success
                }
            else:
                response_item = {
                    "status": ResponseStatus.fail,
                    "remote_id": None,
                    "number": item.number,
                    "message": "exception message"
                }
            response_data.append(response_item)
        return response_data


class GetCancelledOrders(ChannelCommandInterface):
    def get_data(self) -> None:
        return self.objects

    def validated_data(self, data) -> object:
        return data

    def transform_data(self, data) -> object:
        return data

    def send_request(self, transformed_data: BatchRequest) -> object:
        """
            Sends a post request to the channel client to insert the products
        :param transformed_data:
        :return:
            [{ remote_data},]
        """

        response = self.__mocked_request(
            data=self.integration._sent_data[transformed_data],
            remote_batch_id=transformed_data)
        return response

    def normalize_response(self, data, validated_data, transformed_data,
                           response) -> Tuple[List[CancelOrderDto],
                                              ErrorReportDto, Any]:
        report = self.create_report(response)

        for row in response:
            obj = CancelOrderDto(
                order=row["order"],
                cancel_items=row["cancel_items"],
                reasons=row["reasons"]
            )

            yield obj, report, data

    def __mocked_request(self, data, remote_batch_id):
        """
        Mock a request and response for the send operation to mimic actual
        channel data

        :return:

        [{
            "order": "orderNumber123",
            "cancel_items": ["remote_item_1", "remote_item_2"],
            "reasons": {"remote_item_1": "remote_reason_code",
                        "remote_item_2": "remote_reason_code"}
         },]
        """
        response_data = []
        for index, item in enumerate(data):
            response_item = {
                'order': item.number,
                'cancel_items': item.cancel_items,
                'reasons': item.reasons,
            }
            response_data.append(response_item)
        return response_data


class GetUpdatedOrderItems(ChannelCommandInterface):
    def get_data(self):
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
                           response) -> Tuple[ChannelUpdateOrderItemDto,
                                              ErrorReportDto, Any]:
        """
        Convert ChannelUpdateOrderItemDto to the format OmnitronIntegration
        """
        for order_item_data in response:
            report = self.create_report(order_item_data)
            channel_update_order_item = ChannelUpdateOrderItemDto(
                **order_item_data)

            yield channel_update_order_item, report, None

    def __mocked_request(self, data):
        return [{
            "remote_id": "XYAD123213",
            "order_remote_id": "1234",
            "order_number": "1234",
            "status": "550",
            "invoice_number": "1234",
            "invoice_date": None,
            "tracking_number": "400",
            "extra_field": {"tracking_number": "1231"},
        }]


class GetCancellationRequests(ChannelCommandInterface):
    def get_data(self):
        data = self.objects
        return data

    def validated_data(self, data) -> object:
        return data

    def transform_data(self, data) -> object:
        return data

    def send_request(self, transformed_data) -> object:
        response = self.__mocked_request(data=transformed_data)
        return response

    def normalize_response(
            self, data, validated_data, transformed_data,
            response) -> Tuple[CancellationRequestDto, ErrorReportDto, Any]:
        report = self.create_report(response)
        for row in response:
            obj = CancellationRequestDto(
                order_item=row["order_item"],
                reason=row["reason"],
                cancellation_type=row["cancellation_type"],
                remote_id=row["remote_id"]
            )

            yield obj, report, data

    def __mocked_request(self, data):
        """
        Mock a request and response for the send operation to mimic actual
        channel data

        :return:

        [{
            "order_item": "remote_item_1",
            "reason": "remote_reason_code",
            "cancellation_type": "remote_cancellation_type"
         },]
        """
        response_data = [
            {
                'order_item': "1234567816",
                'reason': "iptal",
                'cancellation_type': "refund",
                'remote_id': "1234567816_1"
            }
        ]
        return response_data


class UpdateCancellationRequest(ChannelCommandInterface):
    def get_data(self) -> ChannelCancellationRequestDto:
        isinstance(self.objects, ChannelCancellationRequestDto)
        data = self.objects
        return data

    def validated_data(self, data) -> object:
        return data

    def transform_data(self, data) -> object:
        return data

    def send_request(self, transformed_data) -> object:
        response = self.__mocked_request(data=transformed_data)
        return response

    def normalize_response(
            self, data, validated_data, transformed_data,
            response) -> Tuple[BatchRequestResponseDto, ErrorReportDto, Any]:

        obj = BatchRequestResponseDto(
            status=response["status"],
            remote_id=response["remote_id"],
            sku=response["sku"],
            message=response["message"])
        
        report = self.create_report(response)
        return obj, report, data

    def __mocked_request(self, data):
        """
        Mock a request and response for the send operation to mimic actual
        channel data

        :return:
            
            {
                "status": "SUCCESS",
                "remote_id": "123a1",
                "sku": "1234567",
                "message": ""
            }
        """
        return {
            "status": ResponseStatus.success,
            "remote_id": data.remote_id,
            "sku": data.remote_id,
            "message": data.status
        }
        
