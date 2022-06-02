from typing import List

from omnisdk.omnitron.endpoints import (ChannelProductStockEndpoint,
                                        ChannelIntegrationActionEndpoint,
                                        ChannelBatchRequestEndpoint,
                                        ChannelExtraProductStockEndpoint)
from omnisdk.omnitron.models import ProductStock

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.data import BatchRequestResponseDto
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
        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        stock_integration_actions = endpoint.list(
            params={
                "local_batch_id": self.integration.batch_request.local_batch_id,
                "status": IntegrationActionStatus.processing,
                "channel_id": self.integration.channel_id
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
            params={"stock_list": self.stock_list_id}
        )
        for stock_batch in endpoint.iterator:
            stocks.extend(stock_batch)
            if len(stocks) >= self.BATCH_SIZE:
                break
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
                "status": IntegrationActionStatus.processing
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
    Fetches updated and not sent stock objects from Omnitron

    Batch request state transition to fail or done
     :return: List[ProductStock] as output of do_action
    """
    path = "inserts"


class GetInsertedProductStocks(GetUpdatedProductStocks):
    """
    Fetches inserted stock data from Omnitron.

    Batch request state transition to fail or done

     :return: List[ProductStock] as output of do_action
    """
    path = "inserts"

    def get_stocks_with_available(self, stocks: List[ProductStock]):
        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        product_ids = [str(stock.product) for stock in stocks]
        product_ias = endpoint.list(
            params={"object_id__in": ",".join(product_ids),
                    "content_type_name": ContentType.product.value,
                    "status": IntegrationActionStatus.success,
                    "channel_id": self.integration.channel_id,
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
            for channel_item in channel_response:
                # TODO: comment
                sku = self.get_barcode(obj=product)
                if channel_item.sku != sku:
                    continue
                remote_item = channel_item
                channel_items_by_product_id[product_id] = remote_item
                break
        return channel_items_by_product_id
