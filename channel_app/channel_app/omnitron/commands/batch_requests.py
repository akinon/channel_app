import functools
from collections import defaultdict

from omnisdk.omnitron.endpoints import (ChannelBatchRequestEndpoint,
                                        ChannelIntegrationActionEndpoint,
                                        ChannelProductEndpoint,
                                        ChannelProductPriceEndpoint,
                                        ChannelProductStockEndpoint,
                                        ChannelProductImageEndpoint)

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.utilities import split_list
from channel_app.omnitron.constants import FailedReasonType, ResponseStatus


class GetBatchRequests(OmnitronCommandInterface):
    """
    Fetches BatchRequest entries. For example, we can fetch
    BatchRequests with status 'sent_to_remote'

    There is no state transition in this command.

     :return: List[BatchRequest] as output of do_action
    """
    endpoint = ChannelBatchRequestEndpoint

    def get_data(self):
        """
        
        [{
            "pk": 22,
            "channel": 6,
            "local_batch_id": "89bb31b0-6700-4a9d-8bae-308ac938649c",
            "remote_batch_id": "028b8e66-2a4c-45b5-912f-9ab90036c78a",
            "content_type": "product",
            "status": "sent_to_remote"
        },]
        :return:
        """
        params = getattr(self, "param_{}".format("params"), None)
        if not params:
            return []

        params.update({"channel": self.integration.channel_id})

        batch_requests = self.endpoint(
            channel_id=self.integration.channel_id
        ).list(params=params)
        return batch_requests


class BatchRequestUpdate(OmnitronCommandInterface):
    endpoint = ChannelBatchRequestEndpoint

    def send(self, validated_data) -> object:
        result = self.endpoint(channel_id=self.integration.channel_id).update(
            id=validated_data.pk, item=validated_data)
        return result


class ProcessBatchRequests(object):
    def get_integration_actions_to_processing(self):
        integration_action_endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        batch_integration_action = integration_action_endpoint.list(
            params={
                "local_batch_id": self.integration.batch_request.local_batch_id,
                "channel_id": self.integration.channel_id,
                "status": "processing",
                "limit": self.CHUNK_SIZE,
                "sort": "id"})
        for batch in integration_action_endpoint.iterator:
            if not batch:
                break
            batch_integration_action.extend(batch)
        return batch_integration_action

    def group_model_items_by_content_type(self, items_by_content):
        """
        :return {
            "product": {pk1: product1, pk2: product2, pk3: product3},
            "productstock": {pk1: productstock1, pk2: productstock1, pk3: productstock3},
            "productprice": {pk1: productprice1, pk2: productprice2, pk3: productprice3},
            ...
        }
        """
        batch_items = {}
        for model, model_pks in items_by_content.items():
            if model == "product":
                group_items = self.get_products(model_pks)
            elif model == "productstock":
                group_items = self.get_stocks(model_pks)
            elif model == "productprice":
                group_items = self.get_prices(model_pks)
            elif model == "productimage":
                group_items = self.get_images(model_pks)
            else:
                raise NotImplementedError
            batch_items[model] = group_items
        return batch_items

    def group_integration_actions_by_content_type(self,
                                                  batch_integration_actions):
        """

        :param batch_integration_actions:
        :return: {
            "product": [product_pk1, product_pk2, product_pk3, ...],
            "productprice": [productprice_pk1, productprice_pk2, ...]
        }
        """
        items_by_content = {}
        for integration_action in batch_integration_actions:
            content_type = integration_action.content_type["model"]
            if content_type not in items_by_content:
                items_by_content[content_type] = []
            items_by_content[content_type].append(
                str(integration_action.object_id))
        return items_by_content

    def get_products(self, id_list) -> dict:
        end_point = ChannelProductEndpoint(
            channel_id=self.integration.channel_id)
        products = []
        for chunk_id_list in split_list(id_list, self.CHUNK_SIZE):
            products_batch = end_point.list(
                params={"pk__in": ",".join(chunk_id_list),
                        "limit": len(chunk_id_list)})
            products.extend(products_batch)

        return {s.pk: s for s in products}

    def get_prices(self, id_list: list) -> dict:
        """
        param id_list: productprice pk list
        :return: dict of prices with key product id
        {
            1111:{"pk":2222, "stock":5, ...},
        }
        """
        if not id_list:
            return {}

        endpoint = ChannelProductPriceEndpoint(
            channel_id=self.integration.channel_id)
        prices = []
        for chunk in split_list(id_list, self.CHUNK_SIZE):
            # TODO should we check the size of chunk (len(chunk) == len(stock_batch))
            #  to validate something is missing on omnitron side?
            price_batch = endpoint.list(params={"pk__in": ",".join(chunk),
                                                "limit": len(chunk)})
            prices.extend(price_batch)
        return {p.product: p for p in prices if str(p.pk) in id_list}

    def get_stocks(self, id_list: list) -> dict:
        """
        :param id_list:
        :return: dict of stocks with key product id
        {
            1111:{"pk":3333, price:19.99, ...},
        }
        """
        if not id_list:
            return {}
        endpoint = ChannelProductStockEndpoint(
            channel_id=self.integration.channel_id)
        stocks = []
        for chunk in split_list(id_list, self.CHUNK_SIZE):
            # TODO should we check the size of chunk (len(chunk) == len(stock_batch))
            #  to validate something is missing on omnitron side?
            stock_batch = endpoint.list(params={"pk__in": ",".join(chunk),
                                                "limit": len(chunk)})
            stocks.extend(stock_batch)
            if not stock_batch:
                break
        return {s.product: s for s in stocks if str(s.pk) in id_list}

    def get_images(self, id_list):
        if not id_list:
            return {}
        endpoint = ChannelProductImageEndpoint(
            channel_id=self.integration.channel_id)
        images = []
        for chunk in split_list(id_list, self.CHUNK_SIZE):
            image_batch = endpoint.list(params={"id__in": ",".join(chunk),
                                                "limit": len(chunk)})
            images.extend(image_batch)
            if not image_batch:
                break
        product_images = defaultdict(list)
        [product_images[i.product].append(i) for i in images]
        return product_images

    def get_barcode(self, obj):
        """
        # The barcode uniquely identifying a
        # certain product line across
        remote_id_attribute = ["attributes","barcode"], ["sku"]
        :param obj:
        :return: String (required)
        """
        remote_id_attribute = self.integration.channel.conf.get(
            "remote_id_attribute")
        if remote_id_attribute:
            return self.get_reduce_data(remote_id_attribute, obj.__dict__)
        return obj.sku

    @staticmethod
    def get_reduce_data(code, value):
        try:
            data = functools.reduce(
                lambda d, key: d.get(key, None) if isinstance(d,
                                                              dict) else None,
                code.split("__"), value)
            return data
        except TypeError:
            return None

    def _update_batch_request(self, model_items_by_content):
        object_list = []
        for key, model_items in model_items_by_content.items():
            if isinstance(model_items, dict):
                model_items_obj = [value for key, value in model_items.items()]
            else:
                model_items_obj = []
            objects = self.create_batch_objects(data=model_items_obj,
                                                content_type=key)
            object_list.extend(objects)
        self.update_batch_request(objects_data=object_list)

    def update_other_objects(self, channel_items_by_object_id: dict,
                             model_items_by_content: dict):
        for key, model_items in model_items_by_content.items():
            for reference_object_id, model_item in model_items.items():
                if not isinstance(model_item, list):
                    model_item = [model_item]
                for mi in model_item:
                    try:
                        remote_item = channel_items_by_object_id[
                            reference_object_id]
                    except KeyError:
                        mi.failed_reason_type = FailedReasonType.channel_app.value
                        message = f'This item information was not sent from the channel. ID is {reference_object_id}'
                        self.failed_object_list.append((mi, key, message))
                        continue

                    if remote_item.status == ResponseStatus.fail:
                        mi.failed_reason_type = FailedReasonType.channel_app.value
                        self.failed_object_list.append(
                            (mi, key, remote_item.message))
                    else:
                        mi.remote_id = remote_item.remote_id

    def get_channel_items_by_reference_object_ids(self, channel_response,
                                                  model_items_by_content,
                                                  integration_actions):
        raise NotImplementedError

    def process_item(self, channel_response):
        # [1] Get all integration actions of this batch request
        batch_integration_actions = self.get_integration_actions_to_processing()
        if not batch_integration_actions:
            raise Exception("No records was found not with BatchRequest")

        # [2] Group integration actions by content type and each object_ids of them
        integration_items_by_content = self.group_integration_actions_by_content_type(
            batch_integration_actions)
        # [3] Group model items by content type and their object id
        model_items_by_content = self.group_model_items_by_content_type(
            integration_items_by_content)

        # [4] Link Omnitron and Channel items
        channel_items_by_product_id = self.get_channel_items_by_reference_object_ids(
            channel_response=channel_response,
            model_items_by_content=model_items_by_content,
            integration_actions=batch_integration_actions)

        # [5] Updates statuses of related models by monkey patching them
        # Creates failed_object_list
        self.update_other_objects(channel_items_by_product_id,
                                  model_items_by_content)

        # [6] update batch request and object list
        self._update_batch_request(model_items_by_content)
