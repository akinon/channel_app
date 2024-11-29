from typing import List

from omnisdk.omnitron.endpoints import (ChannelProductStockEndpoint,
                                        ChannelIntegrationActionEndpoint,
                                        ChannelBatchRequestEndpoint,
                                        ChannelExtraProductStockEndpoint,
                                        ChannelExtraProductPriceEndpoint)
from omnisdk.omnitron.models import ProductStock, Product

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.data import BatchRequestResponseDto
from channel_app.core.utilities import split_list
from channel_app.omnitron.commands.batch_requests import ProcessBatchRequests
from channel_app.omnitron.constants import (ContentType, BatchRequestStatus,
                                            IntegrationActionStatus,
                                            FailedReasonType)


class GetUpdatedProductStocks(OmnitronCommandInterface):
    """
    Fetches updated and not sent stock objects from Omnitron

    Batch request state transition to fail or done
     :return: List[ProductStock] as output of do_action
    """
    endpoint = ChannelProductStockEndpoint
    path = "updates"
    BATCH_SIZE = 100
    content_type = ContentType.product_stock.value

    def get_data(self) -> List[ProductStock]:
        stocks = self.get_product_stocks()
        stocks = self.get_stocks_with_available(stocks)
        return stocks

    def get_product_stocks(self) -> List[ProductStock]:
        stocks = self.endpoint(
            path=self.path,
            channel_id=self.integration.channel_id
        ).list(
            params={"limit": self.BATCH_SIZE}
        )
        stocks = stocks[:self.BATCH_SIZE]
        objects_data = self.create_batch_objects(data=stocks,
                                                 content_type=self.content_type)
        self.update_batch_request(objects_data=objects_data)
        return stocks

    def get_stocks_with_available(self, stocks: List[ProductStock]):
        if not stocks:
            return []

        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        stock_integration_actions = endpoint.list(
            params={
                "local_batch_id": self.integration.batch_request.local_batch_id,
                "status": IntegrationActionStatus.processing,
                "channel_id": self.integration.channel_id,
                "sort": "id"
            })
        for stock_batch in endpoint.iterator:
            stock_integration_actions.extend(stock_batch)
        stock_ia_dict = {ia.object_id: ia for ia in stock_integration_actions}
        for stock in stocks:
            stock_ia = stock_ia_dict[stock.pk]
            stock.remote_id = stock_ia.remote_id
        return stocks


class GetUpdatedProductStocksFromExtraStockList(OmnitronCommandInterface):
    """
    Fetches updated and not sent stock objects from Omnitron

    Batch request state transition to fail or done
     :return: List[ProductStock] as output of do_action
    """
    endpoint = ChannelExtraProductStockEndpoint
    path = "updates"
    BATCH_SIZE = 100
    content_type = ContentType.product_stock.value

    def get_data(self) -> List[ProductStock]:
        self.stock_list_id = self.objects
        stocks = self.get_product_stocks()
        stocks = self.get_integration_actions(stocks)
        return stocks

    def get_product_stocks(self) -> List[ProductStock]:
        endpoint = self.endpoint(path=self.path,
                                 channel_id=self.integration.channel_id)
        stocks = endpoint.list(
            params={"stock_list": self.stock_list_id,
                    "limit": self.BATCH_SIZE}
        )
        stocks = stocks[:self.BATCH_SIZE]
        objects_data = self.create_batch_objects(data=stocks,
                                                 content_type=self.content_type)
        self.update_batch_request(objects_data=objects_data)
        return stocks

    def get_integration_actions(self, stocks: List[ProductStock]):
        if not stocks:
            return []
        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        stock_integration_actions = endpoint.list(
            params={
                "local_batch_id": self.integration.batch_request.local_batch_id,
                "status": IntegrationActionStatus.processing,
                "sort": "id"
            })
        for stock_batch in endpoint.iterator:
            stock_integration_actions.extend(stock_batch)
        stock_ia_dict = {ia.object_id: ia for ia in stock_integration_actions}
        for stock in stocks:
            stock_ia = stock_ia_dict[stock.pk]
            stock.remote_id = stock_ia.remote_id
        return stocks


class GetInsertedProductStocksFromExtraStockList(
    GetUpdatedProductStocksFromExtraStockList):
    """
    Fetches inserted stock data from Omnitron.

    Batch request state transition to fail or done
     :return: List[ProductStock] as output of do_action
    """
    path = "inserts"

    def get_integration_actions(self, stocks: List[ProductStock]):
        if not stocks:
            return []

        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        product_ids = [str(stock.product) for stock in stocks]
        product_ias = endpoint.list(
            params={"object_id__in": ",".join(product_ids),
                    "content_type_name": ContentType.product.value,
                    "channel_id": self.integration.channel_id,
                    "sort": "id"
                    })

        for product_batch in endpoint.iterator:
            product_ias.extend(product_batch)
        product_integrations_by_id = {ia.object_id: ia for ia in product_ias}

        for stock in stocks:
            if stock.product in product_integrations_by_id:
                product_ia = product_integrations_by_id[stock.product]
                stock.remote_id = product_ia.remote_id
            else:
                stock.failed_reason_type = FailedReasonType.channel_app.value
                self.failed_object_list.append(
                    (stock, ContentType.product_stock.value,
                     "Product has not been sent"))
        return stocks


class GetInsertedProductStocks(GetUpdatedProductStocks):
    """
    Fetches inserted stock data from Omnitron.

    Batch request state transition to fail or done

     :return: List[ProductStock] as output of do_action
    """
    path = "inserts"

    def get_stocks_with_available(self, stocks: List[ProductStock]):
        if not stocks:
            return []

        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        product_ids = [str(stock.product) for stock in stocks]
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

        for stock in stocks:
            if stock.product in product_integrations_by_id:
                product_ia = product_integrations_by_id[stock.product]
                stock.remote_id = product_ia.remote_id
            else:
                stock.failed_reason_type = FailedReasonType.channel_app.value
                self.failed_object_list.append(
                    (stock, ContentType.product_stock.value,
                     "Product has not been sent"))
        return stocks


class GetProductPricesFromProductStocks(OmnitronCommandInterface):
    endpoint = ChannelExtraProductPriceEndpoint
    CHUNK_SIZE = 50
    content_type = ContentType.product_price.value

    def get_data(self) -> List[ProductStock]:
        product_stocks = self.objects
        self.get_product_price(product_stocks)
        return product_stocks

    def normalize_response(self, data, response) -> List[object]:
        object_list = []
        failed_stocks = [failed_product_stocks[0] for failed_product_stocks in
                         self.failed_object_list]
        product_stock_object_list = self.create_batch_objects(
            data=failed_stocks,
            content_type=ContentType.product_stock.value)
        object_list.extend(product_stock_object_list)

        self.create_integration_actions(data, object_list)
        self.update_batch_request(object_list)
        return data

    def create_integration_actions(self, data, object_list):
        commit_product_prices = [product_stocks.productprice for product_stocks
                                 in data
                                 if not getattr(product_stocks,
                                                "failed_reason_type",
                                                None)]
        product_price_object_list = self.create_batch_objects(
            data=commit_product_prices,
            content_type=ContentType.product_price.value)
        object_list.extend(product_price_object_list)

    def get_product_price(self, product_stocks: List[ProductStock]) -> List[
        ProductStock]:
        if not product_stocks:
            empty_list: List[ProductStock] = []
            return empty_list

        endpoint = self.endpoint(channel_id=self.integration.channel_id)
        product_ids = []
        for ps in product_stocks:
            if not getattr(ps, "failed_reason_type", None):
                if isinstance(ps.product, Product):
                    product_ids.append(str(ps.product.pk))
                else:
                    product_ids.append(str(ps.product))

        prices = []
        for chunk in split_list(product_ids, self.CHUNK_SIZE):
            price_batch = self.get_prices(chunk, endpoint)
            if not price_batch:
                break
            prices.extend(price_batch)

        product_prices = {s.product: s for s in prices}

        for index, product_stock in enumerate(product_stocks):
            if getattr(product_stock, "failed_reason_type", None):
                continue
            try:
                if isinstance(product_stock.product, Product):
                    product_stock.productprice = product_prices[
                        product_stock.product.pk]
                else:
                    product_stock.productprice = product_prices[
                        product_stock.product]
            except KeyError:
                product_stock.failed_reason_type = FailedReasonType.channel_app.value
                self.failed_object_list.append(
                    (product_stock, ContentType.product_stock.value,
                     "PriceNotFound"))
                continue

        return product_stocks

    def get_prices(self, chunk, endpoint):
        price_list = getattr(self, "param_price_list",
                             self.integration.catalog.price_list)
        price_batch = endpoint.list(params={"product__pk__in": ",".join(chunk),
                                            "price_list": price_list,
                                            "limit": len(chunk)})
        return price_batch


class ProcessStockBatchRequests(OmnitronCommandInterface, ProcessBatchRequests):
    """
    Processes response of the channel for the stock update/insert task.
    It updates the stock and related model integration action data according to the
    channel response.

    As input;

    objects : List[BatchRequestResponseDto]. Represents channel response for the
    stock items that are in the BatchRequest.

    batch_request: If related batch request is not supplied, Omnitron will not
    be notified of the results.
    omnitron_integration.batch_request = batch_request

    Batch Request state transition to fail or done

     :return: None
    """
    endpoint = ChannelBatchRequestEndpoint
    content_type = ContentType.product_stock.value
    CHUNK_SIZE = 50
    BATCH_SIZE = 100

    def get_data(self):
        return self.objects

    def validated_data(self, data: List[BatchRequestResponseDto]):
        for item in data:
            assert isinstance(item, BatchRequestResponseDto)
        return data

    def send(self, validated_data):
        self.process_item(validated_data)

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
                       model_items_by_content["productstock"]]

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
