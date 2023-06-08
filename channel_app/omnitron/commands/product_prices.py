from typing import List

from omnisdk.omnitron.endpoints import ChannelIntegrationActionEndpoint, \
    ChannelProductPriceEndpoint, ChannelBatchRequestEndpoint, \
    ChannelExtraProductPriceEndpoint, ChannelExtraProductStockEndpoint
from omnisdk.omnitron.models import ProductPrice, Product

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.data import BatchRequestResponseDto
from channel_app.core.utilities import split_list
from channel_app.omnitron.commands.batch_requests import ProcessBatchRequests
from channel_app.omnitron.constants import (ContentType, BatchRequestStatus,
                                            IntegrationActionStatus,
                                            FailedReasonType)


class GetUpdatedProductPrices(OmnitronCommandInterface):
    endpoint = ChannelProductPriceEndpoint
    path = "updates"
    BATCH_SIZE = 100
    content_type = ContentType.product_price.value

    def get_data(self) -> List[ProductPrice]:
        prices = self.get_product_prices()
        prices = self.get_integration_actions(prices)
        return prices

    def get_product_prices(self) -> List[ProductPrice]:
        prices = self.endpoint(
            path=self.path,
            channel_id=self.integration.channel_id
        ).list(
            params={
                "limit": self.BATCH_SIZE
            }
        )
        prices = prices[:self.BATCH_SIZE]
        objects_data = self.create_batch_objects(data=prices,
                                                 content_type=self.content_type)
        self.update_batch_request(objects_data=objects_data)
        return prices

    def get_integration_actions(self, prices: List[ProductPrice]):
        if not prices:
            return []
        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        price_integration_actions = endpoint.list(
            params={
                "local_batch_id": self.integration.batch_request.local_batch_id,
                "status": IntegrationActionStatus.processing,
                "channel_id": self.integration.channel_id,
                "sort": "id"
            })
        for price_batch in endpoint.iterator:
            price_integration_actions.extend(price_batch)
        price_ia_dict = {ia.object_id: ia for ia in price_integration_actions}
        for price in prices:
            price_ia = price_ia_dict[price.pk]
            price.remote_id = price_ia.remote_id
        return prices


class GetInsertedProductPrices(GetUpdatedProductPrices):
    path = "inserts"

    def get_integration_actions(self, prices: List[ProductPrice]):
        if not prices:
            return []
        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        product_ids = [str(price.product) for price in prices]
        product_ias = endpoint.list(
            params={"object_id__in": ",".join(product_ids),
                    "content_type_name": ContentType.product.value,
                    "status": IntegrationActionStatus.success,
                    "channel_id": self.integration.channel_id,
                    "sort": "id"
                    })
        for product_batch in endpoint.iterator:
            product_ias.extend(product_batch)
        product_integrations_by_id = {ia.object_id: ia for ia in product_ias}

        for price in prices:
            if price.product in product_integrations_by_id:
                product_ia = product_integrations_by_id[price.product]
                price.remote_id = product_ia.remote_id
            else:
                price.failed_reason_type = FailedReasonType.channel_app.value
                self.failed_object_list.append(
                    (price, ContentType.product_price.value,
                     "Product has not been sent"))
        return prices


class GetUpdatedProductPricesFromExtraPriceList(OmnitronCommandInterface):
    endpoint = ChannelExtraProductPriceEndpoint
    path = "updates"
    BATCH_SIZE = 100
    content_type = ContentType.product_price.value

    def get_data(self) -> List[ProductPrice]:
        self.price_list_id = self.objects
        prices = self.get_product_prices()
        prices = self.get_integration_actions(prices)
        return prices

    def get_product_prices(self) -> List[ProductPrice]:
        endpoint = self.endpoint(path=self.path,
                                 channel_id=self.integration.channel_id)
        prices = endpoint.list(
            params={"price_list": self.price_list_id,
                    "limit": self.BATCH_SIZE}
        )

        prices = prices[:self.BATCH_SIZE]
        objects_data = self.create_batch_objects(data=prices,
                                                 content_type=self.content_type)
        self.update_batch_request(objects_data=objects_data)
        return prices

    def get_integration_actions(self, prices: List[ProductPrice]):
        if not prices:
            return []
        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        price_integration_actions = endpoint.list(
            params={
                "local_batch_id": self.integration.batch_request.local_batch_id,
                "status": IntegrationActionStatus.processing,
                "sort": "id"
            })
        for price_batch in endpoint.iterator:
            price_integration_actions.extend(price_batch)
        price_ia_dict = {ia.object_id: ia for ia in price_integration_actions}
        for price in prices:
            price_ia = price_ia_dict[price.pk]
            price.remote_id = price_ia.remote_id
        return prices


class GetInsertedProductPricesFromExtraPriceList(
    GetUpdatedProductPricesFromExtraPriceList):
    path = "inserts"

    def get_integration_actions(self, prices: List[ProductPrice]):
        if not prices:
            return []
        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        product_ids = [str(price.product) for price in prices]
        product_ias = endpoint.list(
            params={"object_id__in": ",".join(product_ids),
                    "content_type_name": ContentType.product.value,
                    "channel_id": self.integration.channel_id,
                    "sort": "id"
                    })
        for product_batch in endpoint.iterator:
            product_ias.extend(product_batch)
        product_integrations_by_id = {ia.object_id: ia for ia in product_ias}

        for price in prices:
            if price.product in product_integrations_by_id:
                product_ia = product_integrations_by_id[price.product]
                price.remote_id = product_ia.remote_id
            else:
                price.failed_reason_type = FailedReasonType.channel_app.value
                self.failed_object_list.append(
                    (price, ContentType.product_price.value,
                     "Product has not been sent"))
        return prices


class GetProductStocksFromProductPrices(OmnitronCommandInterface):
    endpoint = ChannelExtraProductStockEndpoint
    content_type = ContentType.product_stock.value
    CHUNK_SIZE = 50

    def get_data(self) -> List[ProductPrice]:
        product_prices = self.objects
        self.get_product_stock(product_prices)
        return product_prices

    def normalize_response(self, data, response) -> List[object]:
        object_list = []
        failed_prices = [failed_product_prices[0] for failed_product_prices in
                         self.failed_object_list]
        product_price_object_list = self.create_batch_objects(
            data=failed_prices,
            content_type=ContentType.product_price.value)
        object_list.extend(product_price_object_list)

        self.create_integration_actions(data, object_list)
        self.update_batch_request(object_list)
        return data

    def create_integration_actions(self, data, object_list):
        commit_product_stocks = [product_prices.productstock for product_prices
                                 in data
                                 if not getattr(product_prices,
                                                "failed_reason_type",
                                                None)]
        product_stock_object_list = self.create_batch_objects(
            data=commit_product_stocks,
            content_type=ContentType.product_stock.value)
        object_list.extend(product_stock_object_list)

    def get_product_stock(self, product_prices: List[ProductPrice]) -> List[
        ProductPrice]:
        if not product_prices:
            empty_list: List[ProductPrice] = []
            return empty_list

        product_ids = []
        for pp in product_prices:
            if not getattr(pp, "failed_reason_type", None):
                if isinstance(pp.product, Product):
                    product_ids.append(str(pp.product.pk))
                else:
                    product_ids.append(pp.product)

        endpoint = self.endpoint(channel_id=self.integration.channel_id)
        stocks = []
        for chunk in split_list(product_ids, self.CHUNK_SIZE):
            stock_batch = self.get_stocks(chunk, endpoint)
            if not stock_batch:
                break
            stocks.extend(stock_batch)

        product_stocks = {s.product: s for s in stocks}

        for index, product_price in enumerate(product_prices):
            if getattr(product_price, "failed_reason_type", None):
                continue
            try:
                if isinstance(product_price.product, Product):
                    product_price.productstock = product_stocks[
                        product_price.product.pk]
                else:
                    product_price.productstock = product_stocks[
                        product_price.product]
            except KeyError:
                product_price.failed_reason_type = FailedReasonType.channel_app.value
                self.failed_object_list.append(
                    (product_price, ContentType.product_price.value,
                     "StockNotFound"))
                continue

        return product_prices

    def get_stocks(self, chunk, endpoint):
        stock_list = getattr(self, "param_stock_list",
                             self.integration.catalog.stock_list)
        stock_batch = endpoint.list(params={"product__pk__in": ",".join(chunk),
                                            "stock_list": stock_list,
                                            "limit": len(chunk)})
        return stock_batch


class ProcessPriceBatchRequests(OmnitronCommandInterface, ProcessBatchRequests):
    endpoint = ChannelBatchRequestEndpoint
    content_type = ContentType.product_price.value
    CHUNK_SIZE = 50
    BATCH_SIZE = 100

    def get_data(self):
        return self.objects

    def validated_data(self, data: List[BatchRequestResponseDto]):
        for item in data:
            assert isinstance(item, BatchRequestResponseDto)
        return data

    def send(self, validated_data):
        result = self.process_item(validated_data)
        return result

    @property
    def update_state(self, *args, **kwargs) -> BatchRequestStatus:
        return BatchRequestStatus.done

    def check_run(self, is_ok, formatted_data):
        if not is_ok and self.is_batch_request:
            self.integration.batch_request.objects = None
            self.batch_service(self.integration.channel_id).to_fail(
                self.integration.batch_request)
        return False

    def get_channel_items_by_reference_object_ids(self, channel_response,
                                                  model_items_by_content,
                                                  integration_actions):
        product_ids = [str(item) for item in
                       model_items_by_content["productprice"]]

        model_items_by_content_product = self.get_products(product_ids)

        channel_items_by_product_id = {}
        for product_id, product in model_items_by_content_product.items():
            sku = self.get_barcode(obj=product)
            for channel_item in channel_response:
                # TODO: comment
                if channel_item.sku != sku:
                    continue
                remote_item = channel_item
                channel_items_by_product_id[product_id] = remote_item
                break
        return channel_items_by_product_id
