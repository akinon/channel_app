from dataclasses import asdict
from typing import Any, List

from requests import exceptions as requests_exceptions

from omnisdk.omnitron.endpoints import (ChannelCreateOrderEndpoint,
                                        ChannelIntegrationActionEndpoint,
                                        ChannelOrderShippingInfoEndpoint,
                                        ChannelOrderItemEndpoint,
                                        ChannelBatchRequestEndpoint,
                                        ChannelOrderEndpoint,
                                        ChannelCargoEndpoint,
                                        ChannelCancellationRequestEndpoint)
from omnisdk.omnitron.models import Order, OrderShippingInfo, \
    CancellationRequest

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.data import (OrderBatchRequestResponseDto,
                                   OmnitronCreateOrderDto, OmnitronOrderDto,
                                   OrderItemDto, CancelOrderDto, 
                                   CancellationRequestDto)
from channel_app.core.utilities import split_list
from channel_app.omnitron.batch_request import ClientBatchRequest
from channel_app.omnitron.commands.batch_requests import ProcessBatchRequests
from channel_app.omnitron.constants import (ContentType, BatchRequestStatus)
from channel_app.omnitron.exceptions import AppException, OrderException


class GetOrders(OmnitronCommandInterface):
    endpoint = ChannelOrderEndpoint
    batch_service = ClientBatchRequest
    content_type = ContentType.order.value
    path = "updates"
    BATCH_SIZE = 100

    def get_data(self) -> List[Order]:
        orders = self.get_orders()
        return orders

    def get_orders(self) -> List[Order]:
        orders = self.endpoint(
            path=self.path, channel_id=self.integration.channel_id
        ).list(
            params={
                "limit": self.BATCH_SIZE
            }
        )
        orders = orders[:self.BATCH_SIZE]

        objects_data = self.create_batch_objects(
            data=orders, content_type=self.content_type)
        self.update_batch_request(objects_data=objects_data)

        return orders


class GetOrderItems(OmnitronCommandInterface):
    endpoint = ChannelOrderItemEndpoint

    def get_data(self):
        order = self.objects
        order_items = self.get_order_items(order)
        for order_item in order_items:
            order_item.content_type = ContentType.order_item.value
        self.integration.do_action(key="get_integration_with_object_id",
                                   objects=order_items)
        return order_items

    def get_order_items(self, order):
        params = {"order": order.pk, "sort": "id"}
        endpoint = self.endpoint(channel_id=self.integration.channel_id)
        order_items = endpoint.list(params=params)
        for item in endpoint.iterator:
            if not item:
                break
            order_items.extend(item)
        return order_items


class GetOrderItemsWithOrder(GetOrderItems):
    endpoint = ChannelOrderItemEndpoint

    def get_data(self):
        orders = self.objects
        for order in orders:
            order_items = self.get_order_items(order)
            order.orderitem_set = order_items

        return orders


class ProcessOrderBatchRequests(OmnitronCommandInterface, ProcessBatchRequests):
    """
    Not finalized batch requests with content type `order` is managed in this command
    """
    endpoint = ChannelBatchRequestEndpoint
    content_type = ContentType.order.value
    BATCH_SIZE = 100
    CHUNK_SIZE = 50

    def validated_data(self, data: List[OrderBatchRequestResponseDto]):
        for item in data:
            assert isinstance(item, OrderBatchRequestResponseDto)
        return data

    def send(self, validated_data):
        result = self.process_item(validated_data)
        return result

    @property
    def update_state(self, *args, **kwargs) -> BatchRequestStatus:
        return BatchRequestStatus.commit

    def get_remote_order_number(self, obj, integration_actions):
        for integration_action in integration_actions:
            content_type = integration_action.content_type["model"]
            if content_type != "order":
                continue
            if integration_action.object_id == obj.pk:
                return integration_action.remote_id

    def get_channel_items_by_reference_object_ids(self, channel_response,
                                                  model_items_by_content,
                                                  integration_actions):
        channel_items_by_order_id = {}
        for order_id, order in model_items_by_content["order"].items():
            number = self.get_remote_order_number(
                obj=order, integration_actions=integration_actions)
            for channel_item in channel_response:
                # TODO: comment
                if channel_item.number != number:
                    continue
                remote_item = channel_item
                channel_items_by_order_id[order_id] = remote_item
                break
        return channel_items_by_order_id

    def get_orders(self, id_list) -> dict:
        if not id_list:
            return {}

        end_point = ChannelOrderEndpoint(
            channel_id=self.integration.channel_id)
        orders = []
        for chunk_id_list in split_list(id_list, self.CHUNK_SIZE):
            orders_batch = end_point.list(
                params={"pk__in": ",".join(chunk_id_list),
                        "limit": len(chunk_id_list)})
            orders.extend(orders_batch)
        return {order.pk: order for order in orders}

    def group_model_items_by_content_type(self, items_by_content):
        batch_items = {}
        for model, model_pks in items_by_content.items():
            if model != "order":
                continue
            group_items = self.get_orders(model_pks)
            batch_items[model] = group_items
        return batch_items


class CreateOrders(OmnitronCommandInterface):
    endpoint = ChannelCreateOrderEndpoint
    content_type = ContentType.order.value
    CHUNK_SIZE = 50

    def get_data(self) -> dict:
        assert isinstance(self.objects, OmnitronCreateOrderDto)

        order = self.objects.order
        order_item = self.objects.order_item
        order_items = self.prepare_order_items(order_items=order_item)
        extra_field = self.get_extra_field(order)
        data = {
            "order_item": order_items,
            "order": {
                "number": order.number[:128],
                "status": order.status,
                "channel": self.integration.channel_id,
                "customer": order.customer,
                "shipping_address": order.shipping_address,
                "billing_address": order.billing_address,
                "currency": order.currency,
                "amount": order.amount,
                "shipping_amount": order.shipping_amount,
                "shipping_tax_rate": order.shipping_tax_rate,
                "extra_field": extra_field,
                "delivery_type": order.delivery_type,
                "cargo_company": order.cargo_company,
                "discount_amount": order.discount_amount or 0,
                "net_shipping_amount": order.net_shipping_amount,
                "tracking_number": (order.tracking_number and
                                    order.tracking_number[:256]),
                "carrier_shipping_code": (order.carrier_shipping_code and
                                          order.carrier_shipping_code[:256]),
                "remote_addr": order.remote_addr,
                "has_gift_box": order.has_gift_box,
                "gift_box_note": order.gift_box_note[:160],
                "client_type": "default",
                "language_code": order.language_code,
                "notes": order.notes[:320],
                "delivery_range": order.delivery_range,
                "shipping_option_slug": order.shipping_option_slug[:128],
                "date_placed": str(order.created_at)
            }
        }
        return data

    def get_extra_field(self, order: OmnitronOrderDto):
        extra_field = order.extra_field or {}
        if "id" not in extra_field and order.remote_id:
            extra_field.update({"id": order.remote_id})
        return extra_field

    def send(self, validated_data) -> object:
        order_obj = Order(**validated_data)
        order_endpoint = ChannelOrderEndpoint
        try:
            order_number = order_obj.order.get("number")
            is_order_exists = order_endpoint(
                channel_id=self.integration.channel_id
            ).list(
                params={
                    "number": order_number,
                    "channel_id": self.integration.channel_id
                    }
            )
            if is_order_exists:
                raise OrderException(params="Order Already Exist On Omnitron")

        except OrderException:
            return is_order_exists
        try:
            order = self.endpoint(
                channel_id=self.integration.channel_id
            ).create(item=order_obj)
        except requests_exceptions.HTTPError as exc:
            raise OrderException(params=exc.response.text)

        self._update_batch_request(order)
        return order

    def normalize_response(self, data, response) -> List[object]:
        return [data]

    def _update_batch_request(self, order):
        order.remote_id = order.extra_field.get("id")
        objects_data_order = self.create_batch_objects(data=[order],
                                                       content_type=ContentType.order.value)
        order_items = self.get_order_items(order_pk=order.pk)
        for item in order_items:
            item.remote_id = item.extra_field["id"]
        objects_data_order_items = self.create_batch_objects(
            data=order_items,
            content_type=ContentType.order_item.value)
        objects_data = []
        objects_data.extend(objects_data_order)
        objects_data.extend(objects_data_order_items)
        self.update_batch_request(objects_data=objects_data)

    def get_order_items(self, order_pk):
        params = {"order": order_pk, "sort": "id"}
        endpoint = ChannelOrderItemEndpoint(
            channel_id=self.integration.channel_id)
        order_items = endpoint.list(params=params)
        for item in endpoint.iterator:
            if not item:
                break
            order_items.extend(item)
        return order_items

    @property
    def update_state(self, *args, **kwargs) -> BatchRequestStatus:
        return BatchRequestStatus.commit

    def prepare_order_items(self, order_items: List[OrderItemDto]):
        product_dict = self.get_products(order_items)
        items = []
        for item in order_items:
            price_list = self.integration.catalog.price_list
            stock_list = self.integration.catalog.stock_list
            if item.product not in product_dict:
                raise AppException(
                    "Product not found: remote_id={}".format(item.product))
            order_item_data = {
                "product": product_dict[item.product],
                "status": item.status or "400",
                "price_currency": item.price_currency,
                "price": item.price,
                "tax_rate": item.tax_rate,
                "extra_field": self.get_order_item_extra_field(item),
                "price_list": item.price_list or price_list,
                "stock_list": item.stock_list or stock_list,
                "tracking_number": item.tracking_number,
                "carrier_shipping_code": item.carrier_shipping_code[:256],
                "discount_amount": item.discount_amount,
                "retail_price": item.retail_price,
                "attributes": item.attributes or {},
                "attributes_kwargs": item.attributes_kwargs or {},
                "parent": item.parent,
                "delivered_date": item.delivered_date,
                "estimated_delivery_date": item.delivered_date,
            }
            items.append(order_item_data)
        return items

    def get_order_item_extra_field(self, order_item: OrderItemDto):
        extra_field = order_item.extra_field
        if "id" not in extra_field and order_item.remote_id:
            extra_field.update({"id": order_item.remote_id})
        return extra_field

    def get_products(self, order_items: List[OrderItemDto]) -> dict:
        product_remote_ids = self.get_product_remote_id_list(order_items)
        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        product_integration_actions = []
        for chunk in split_list(product_remote_ids, self.CHUNK_SIZE):
            params = {"channel": self.integration.channel_id,
                      "content_type_name": ContentType.product.value,
                      "remote_id__in": ",".join(chunk),
                      "sort": "id"}
            ia = endpoint.list(params=params)
            for item in endpoint.iterator:
                if not item:
                    break
                ia.extend(item)

            product_integration_actions.extend(ia)

        return {ia.remote_id: ia.object_id for ia in
                product_integration_actions}

    def get_product_remote_id_list(self, order_items: List[OrderItemDto]):
        product_remote_ids = list(set(item.product for item in order_items))
        return product_remote_ids

    def check_run(self, is_ok, formatted_data):
        if is_ok and formatted_data and self.is_batch_request:
            return True
        return False


class CreateOrderShippingInfo(OmnitronCommandInterface):
    endpoint = ChannelOrderShippingInfoEndpoint

    def get_data(self) -> dict:
        order: Order = self.objects
        cargo_is_send = self.integration.channel.conf.get(
            "send_shipping_info", False)
        shipping_company = self.get_shipping_company(
            cargo_company_id=order.cargo_company)
        data = {
            "order": order.pk,
            "order_number": order.number,
            "shipping_company": shipping_company,
            "is_send": cargo_is_send
        }
        return data

    def get_shipping_company(self, cargo_company_id):
        endpoint = ChannelCargoEndpoint(channel_id=self.integration.channel_id)
        cargo_company = endpoint.retrieve(id=cargo_company_id)
        return cargo_company

    def send(self, validated_data) -> object:
        """
        :param validated_data: data for order
        :return: order objects
        """
        order_shipping_info_obj = OrderShippingInfo(**validated_data)
        order = self.endpoint(channel_id=self.integration.channel_id).create(
            item=order_shipping_info_obj)
        return order

    def check_run(self, is_ok, formatted_data):
        if not is_ok:
            return False
        return True


class CreateOrderCancel(OmnitronCommandInterface):
    endpoint = ChannelOrderEndpoint
    path = "{pk}/cancel"

    def get_data(self):
        assert isinstance(self.objects, CancelOrderDto)
        cancel_data = self.objects
        order_pk = self.get_order_pk(order_remote_id=cancel_data.order)
        order_item_dict = self.get_order_item_dict(
            cancel_items=cancel_data.cancel_items)
        order_item_pk_list = []
        for key, pk_list in order_item_dict.items():
            order_item_pk_list.extend(pk_list)

        reasons = self.get_reasons_data(order_item_dict=order_item_dict,
                                        reasons=cancel_data.reasons)

        data = {
            "cancel_items": order_item_pk_list,
            "order": order_pk,
            "reasons": reasons,
            "forced_refund_amount": cancel_data.forced_refund_amount
        }
        return data

    def get_order_pk(self, order_remote_id):
        end_point = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        params = {"channel": self.integration.channel_id,
                  "content_type_name": ContentType.order.value,
                  "remote_id__exact": order_remote_id}
        integration_actions = end_point.list(params=params)
        if not integration_actions:
            raise Exception(
                "Order not found: number={}".format(order_remote_id))
        if len(integration_actions) != 1:
            raise Exception(
                "CancelOrder.get_order_pk query incorrect: params={}".format(
                    params))

        integration_action = integration_actions[0]
        object_id = integration_action.object_id
        return object_id

    def get_order_item_dict(self, cancel_items: List[str]) -> dict:
        """
        cancel_items: ["121", "232"] -> omnitron orderitem remote_id list
        :return: dict
            {orderitem_remote_id: [omnitron_id1, omnitronid2]}
            {"121": [1001]}
            {"232": [1002, 1003]}
        """
        end_point = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)

        object_ids = {}
        for order_item_remote_id in cancel_items:
            params = {"channel": self.integration.channel_id,
                      "content_type_name": ContentType.order_item.value,
                      "remote_id__exact": order_item_remote_id,
                      "sort": "id"}
            integration_actions = end_point.list(params=params)
            for item in end_point.iterator:
                if not item:
                    break
                integration_actions.extend(item)

            if not integration_actions:
                raise Exception(
                    "CreateOrderCancel: OrderItem not found, number={}".format(
                        order_item_remote_id))
            ids = [integration_action.object_id
                   for integration_action in integration_actions]

            object_ids[order_item_remote_id] = ids

        return object_ids

    def get_reasons_data(self, order_item_dict: dict, reasons: dict):
        """
        order_item_dict: dict  # {remote_basketitem_id: [id1,id2]}
        reasons: dict # {order_item_remote_id: remote_reason_code}
        """
        reasons_dict = {}  # order_item_id: reason_id
        for order_item_remote_id, reason_remote_code in reasons.items():
            order_item_id_list = order_item_dict[order_item_remote_id]
            reason_mapping = self.integration.channel.conf.get(
                "reason_mapping", {})
            try:
                cancellation_reason_id = reason_mapping[reason_remote_code]
            except KeyError:
                cancellation_reason_id = self.integration.channel.conf.get(
                    "cancellation_reason_id")

            for order_item_id in order_item_id_list:
                reasons_dict[order_item_id] = cancellation_reason_id
        return reasons_dict

    def send(self, validated_data) -> Order:
        path = self.path.format(pk=validated_data["order"])
        endpoint = self.endpoint(path=path,
                                 channel_id=self.integration.channel_id,
                                 raw=True)
        response = endpoint.create(item=validated_data)
        return response

    def normalize_response(self, data, response) -> List[object]:
        return [data]


class GetCancellationRequest(OmnitronCommandInterface):
    endpoint = ChannelCancellationRequestEndpoint
    content_type = ContentType.cancellation_request.value
    CHUNK_SIZE = 50

    def get_data(self):
        """
        {"status": "approved", "cancellation_type": "refund or cancel"}
        """
        assert isinstance(self.objects, dict)
        query_params = self.objects
        if not query_params.get("limit", None):
            query_params["limit"] = self.CHUNK_SIZE
        return self.get_cancellation_requests(query_params=query_params)

    def get_cancellation_requests(self, query_params={}) -> List[
            CancellationRequest]:
        endpoint = self.endpoint(channel_id=self.integration.channel_id)
        cancellation_requests = endpoint.list(params=query_params)
        for batch in endpoint.iterator:
            if not batch:
                break
            cancellation_requests.extend(batch)
        
        objects_data = self.create_batch_objects(
            data=cancellation_requests, content_type=self.content_type)
        self.update_batch_request(objects_data=objects_data)
                
        return cancellation_requests
    
    def check_run(self, is_ok, formatted_data):
        if not is_ok:
            return False
        return True


class GetCancellationRequestUpdates(GetCancellationRequest):
    endpoint = ChannelCancellationRequestEndpoint
    path = "updates"

    def get_cancellation_requests(self, query_params={}) -> List[CancellationRequest]:
        endpoint = self.endpoint(channel_id=self.integration.channel_id,
                                 path=self.path)
        cancellation_requests = endpoint.list(params=query_params)
        for batch in endpoint.iterator:
            if not batch:
                break
            cancellation_requests.extend(batch)
        
        for cr in cancellation_requests:
            cr.pk = cr.id
            
        objects_data = self.create_batch_objects(
            data=cancellation_requests, content_type=self.content_type)
        self.update_batch_request(objects_data=objects_data)
        return cancellation_requests

    def check_run(self, is_ok, formatted_data):
        if not is_ok:
            return False
        return True


class CreateCancellationRequest(OmnitronCommandInterface):
    endpoint = ChannelCancellationRequestEndpoint

    def get_data(self):
        assert isinstance(self.objects, CancellationRequestDto)
        cancellation_request = self.objects
        # omnitron donusumleri yapilir.
        omnitron_reason = self.get_omnitron_reason(cancellation_request.reason)
        # omnitron reason
        cancellation_request.reason = omnitron_reason
        # remote_id
        cancellation_request.remote_id = cancellation_request.remote_id
        # omnitron order_item
        omnitron_order_item = self.get_omnitron_order_item(cancellation_request.order_item)
        cancellation_request.order_item = omnitron_order_item
        
        data = asdict(cancellation_request)
        return CancellationRequest(**data)
    
    def send(self, validated_data) -> CancellationRequest:
        """
        :param validated_data: data for order
        :return: cancellationrequest objects
        """
        endpoint = self.endpoint(channel_id=self.integration.channel_id)

        response_cancellation_request = endpoint.create(item=validated_data)
        response_cancellation_request.remote_id = validated_data.remote_id
        response_cancellation_request.pk = response_cancellation_request.id
        objects_data = self.create_batch_objects(
            data=[response_cancellation_request], 
            content_type=ContentType.cancellation_request.value)
        
        self.update_batch_request(objects_data=objects_data)
        return response_cancellation_request
    
    def normalize_response(self, data, response) -> List[object]:
        return [response]
    
    def check_run(self, is_ok, formatted_data):
        if not is_ok:
            return False
        return True

    def get_omnitron_order_item(self, channel_order_item):
        """
        order_item_remote_id -> omnitron orderitem remote_id str
        :return: int
        """
        end_point = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        
        params = {"channel": self.integration.channel_id,
                  "content_type_name": ContentType.order_item.value,
                  "remote_id__exact": channel_order_item,
                  "sort": "id"}
        integration_actions = end_point.list(params=params)
        for item in end_point.iterator:
            if not item:
                break
            integration_actions.extend(item)

        if not integration_actions:
            raise AppException(
                "OrderItem not found, number={}".format(
                    channel_order_item))
        if len(integration_actions) != 1:
            raise AppException("Multiple records returned from Omnitron "
                               "for a single order item: remote_id: {}".format(
                                   channel_order_item))
        return integration_actions[0].object_id
            
    def get_omnitron_reason(self, channel_reason):
        configuration = self.integration.channel.conf
        omnitron_reason = configuration.get("reason_mapping", {}).get(channel_reason)
        if omnitron_reason:
            return omnitron_reason
        return 10
    

class UpdateOrderItems(OmnitronCommandInterface):
    endpoint = ChannelOrderItemEndpoint
    order_item_pk = None
    order_item = None

    def get_data(self) -> object:
        """
        {
            "remote_id": "12049323",
            "status": 550,
            "invoice_number": "xyz",
            "invoice_date": None",
            "tracking_number": "TRACK-1"
        }
        """
        order_item = self.objects
        self.order_item_pk = self.get_order_item_pk(order_item.remote_id)
        self.order_item = self.get_order_item(self.order_item_pk)
        if not self.order_item_pk or not self.order_item:
            return
        return order_item

    def validated_data(self, data):
        if not data:
            return
        validated_data = asdict(data)
        validated_data.pop("remote_id")
        validated_data.pop("order_remote_id")
        validated_data = filter(lambda item: bool(item[1]) is True,
                                validated_data.items())
        validated_data = dict(validated_data)

        for key, val in validated_data.items():
            if getattr(self.order_item, key) != val:
                break
        else:   # if no changes detected, return None
            return

        return validated_data

    def get_order_item(self, pk):
        if not pk:      # if get_order_item_pk returns None
            return
        end_point = ChannelOrderItemEndpoint(
            channel_id=self.integration.channel_id)

        order_item = end_point.retrieve(id=pk)
        return order_item

    def get_order_item_pk(self, order_item_remote_id):
        end_point = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        params = {"channel": self.integration.channel_id,
                  "content_type_name": ContentType.order_item.value,
                  "remote_id__exact": order_item_remote_id}
        integration_actions = end_point.list(params=params)
        if not integration_actions and len(integration_actions) != 1:
            return
        integration_action = integration_actions[0]
        object_id = integration_action.object_id
        return object_id

    def send(self, validated_data) -> object:
        if not validated_data:
            return
        response = self.endpoint(
            channel_id=self.integration.channel_id, raw=True
        ).update(
            id=self.order_item_pk, item=validated_data
        )
        return response

    def normalize_response(self, data, response) -> List[object]:
        return [response]

    def update_state(self, *args, **kwargs) -> BatchRequestStatus:
        return BatchRequestStatus.commit
