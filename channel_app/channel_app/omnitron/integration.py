from channel_app.core.clients import OmnitronApiClient

from channel_app.core.integration import BaseIntegration
from channel_app.omnitron.batch_request import ClientBatchRequest
from channel_app.omnitron.commands.batch_requests import GetBatchRequests, \
    BatchRequestUpdate
from channel_app.omnitron.commands.error_reports import \
    CreateAddressErrorReports, \
    CreateErrorReports
from channel_app.omnitron.commands.integration_actions import \
    CreateIntegrationActions, \
    GetIntegrationActionsWithObjectId, GetIntegrationActionsWithRemoteId, \
    UpdateIntegrationActions, \
    GetIntegrationActions, GetObjectsFromIntegrationAction
from channel_app.omnitron.commands.orders.addresses import GetOrCreateAddress
from channel_app.omnitron.commands.orders.cargo_companies import GetCargoCompany
from channel_app.omnitron.commands.orders.customers import GetOrCreateCustomer
from channel_app.omnitron.commands.orders.orders import (
    CreateOrders,
    CreateOrderShippingInfo,
    GetCancellationRequestUpdates,
    CreateCancellationRequest,
    GetOrders,
    ProcessOrderBatchRequests,
    CreateOrderCancel,
    GetCancellationRequest,
    GetOrderItems,
    GetOrderItemsWithOrder, UpdateOrderItems)
from channel_app.omnitron.commands.product_images import (
    GetUpdatedProductImages, GetInsertedProductImages,
    ProcessImageBatchRequests)
from channel_app.omnitron.commands.product_prices import (
    GetUpdatedProductPrices, ProcessPriceBatchRequests,
    GetInsertedProductPrices, GetInsertedProductPricesFromExtraPriceList,
    GetUpdatedProductPricesFromExtraPriceList,
    GetProductStocksFromProductPrices)
from channel_app.omnitron.commands.product_stocks import (
    GetUpdatedProductStocks, ProcessStockBatchRequests,
    GetInsertedProductStocks, GetUpdatedProductStocksFromExtraStockList,
    GetInsertedProductStocksFromExtraStockList,
    GetProductPricesFromProductStocks)
from channel_app.omnitron.commands.products import (
    GetInsertedProducts,
    GetUpdatedProducts,
    ProcessProductBatchRequests,
    GetDeletedProducts,
    ProcessDeletedProductBatchRequests,
    GetMappedProducts,
    GetProductPrices,
    GetProductStocks,
    GetInsertedOrUpdatedProducts,
    GetProductCategoryNodes, GetProductObjects, GetProductsFromBatchrequest,
    GetProductPricesWithOutCommit, GetProductStocksWithOutCommit,
    GetMappedProductsWithOutCommit,
    GetProductCategoryNodesWithIntegrationAction)
from channel_app.omnitron.commands.setup import (
    CreateOrUpdateCategoryTreeAndNodes, CreateOrUpdateCategoryAttributes,
    GetCategoryIds, CreateOrUpdateChannelAttributeSet,
    GetOrCreateChannelAttributeSetConfig, CreateOrUpdateChannelAttribute,
    CreateOrUpdateChannelAttributeConfig, CreateOrUpdateChannelAttributeValue,
    GetOrCreateChannelAttributeValueConfig,
    AsyncCreateOrUpdateCategoryAttributes, GetOrCreateChannelAttributeSchema,
    UpdateChannelConfSchema, GetChannelAttributeSetConfigs,
    GetChannelAttributeSets)


class OmnitronIntegration(BaseIntegration):
    """
    Communicates with the Omnitron Api services through the commands defined. It manages
    OmnitronApiClient object on enter and exit methods.

    """
    actions = {
        "get_inserted_products": GetInsertedProducts,
        "get_updated_products": GetUpdatedProducts,
        "get_inserted_or_updated_products": GetInsertedOrUpdatedProducts,
        "get_deleted_products": GetDeletedProducts,
        "get_mapped_products": GetMappedProducts,
        "get_mapped_products_without_commit": GetMappedProductsWithOutCommit,
        "get_product_prices": GetProductPrices,
        "get_product_prices_without_commit": GetProductPricesWithOutCommit,
        "get_product_stocks": GetProductStocks,
        "get_product_stocks_without_commit": GetProductStocksWithOutCommit,
        "get_product_categories": GetProductCategoryNodes,
        "get_product_categories_with_integration_action": GetProductCategoryNodesWithIntegrationAction,
        "get_batch_requests": GetBatchRequests,
        "get_updated_stocks": GetUpdatedProductStocks,
        "get_inserted_stocks": GetInsertedProductStocks,
        "get_updated_stocks_from_extra_stock_list": GetUpdatedProductStocksFromExtraStockList,
        "get_prices_from_product_stocks": GetProductPricesFromProductStocks,
        "get_stocks_from_product_prices": GetProductStocksFromProductPrices,
        "get_inserted_stocks_from_extra_stock_list": GetInsertedProductStocksFromExtraStockList,
        "get_updated_prices": GetUpdatedProductPrices,
        "get_inserted_prices": GetInsertedProductPrices,
        "get_inserted_prices_from_extra_price_list": GetInsertedProductPricesFromExtraPriceList,
        "get_updated_prices_from_extra_price_list": GetUpdatedProductPricesFromExtraPriceList,
        "get_updated_images": GetUpdatedProductImages,
        "get_inserted_images": GetInsertedProductImages,
        "process_product_batch_requests": ProcessProductBatchRequests,
        "process_stock_batch_requests": ProcessStockBatchRequests,
        "process_price_batch_requests": ProcessPriceBatchRequests,
        "process_image_batch_requests": ProcessImageBatchRequests,
        "process_order_batch_requests": ProcessOrderBatchRequests,
        "process_delete_product_batch_requests": ProcessDeletedProductBatchRequests,
        "get_or_create_customer": GetOrCreateCustomer,
        "get_or_create_address": GetOrCreateAddress,
        "get_cargo_company": GetCargoCompany,
        "create_order": CreateOrders,
        "get_orders": GetOrders,
        "get_order_items": GetOrderItems,
        "get_order_items_with_order": GetOrderItemsWithOrder,
        "create_order_shipping_info": CreateOrderShippingInfo,
        "create_or_update_category_tree_and_nodes": CreateOrUpdateCategoryTreeAndNodes,
        "create_or_update_category_attributes": CreateOrUpdateCategoryAttributes,
        "create_or_update_category_attributes_async": AsyncCreateOrUpdateCategoryAttributes,
        "create_address_error_report": CreateAddressErrorReports,
        "create_error_report": CreateErrorReports,
        "get_integration_with_object_id": GetIntegrationActionsWithObjectId,
        "get_integration_with_remote_id": GetIntegrationActionsWithRemoteId,
        "get_integrations": GetIntegrationActions,
        "get_content_objects_from_integrations": GetObjectsFromIntegrationAction,
        "create_integration": CreateIntegrationActions,
        "update_integration": UpdateIntegrationActions,
        "get_category_ids": GetCategoryIds,
        "create_or_update_channel_attribute_set": CreateOrUpdateChannelAttributeSet,
        "get_or_create_channel_attribute_set_config": GetOrCreateChannelAttributeSetConfig,
        "create_or_update_channel_attribute": CreateOrUpdateChannelAttribute,
        "get_or_create_channel_attribute_schema": GetOrCreateChannelAttributeSchema,
        "create_or_update_channel_attribute_config": CreateOrUpdateChannelAttributeConfig,
        "get_channel_attribute_set_configs": GetChannelAttributeSetConfigs,
        "get_channel_attribute_set": GetChannelAttributeSets,
        "create_or_update_channel_attribute_value": CreateOrUpdateChannelAttributeValue,
        "get_or_create_channel_attribute_value_config": GetOrCreateChannelAttributeValueConfig,
        "batch_request_update": BatchRequestUpdate,
        "create_order_cancel": CreateOrderCancel,
        "update_channel_conf_schema": UpdateChannelConfSchema,
        "get_product_objects": GetProductObjects,
        "get_product_from_batch_request": GetProductsFromBatchrequest,
        "get_cancellation_requests": GetCancellationRequest,
        "get_cancellation_requests_update": GetCancellationRequestUpdates,
        "create_cancellation_requests": CreateCancellationRequest,
        "update_order_items": UpdateOrderItems
        # "fetch_cancellation_plan": FetchCancellationPlan
    }

    def __init__(self, create_batch=True, content_type=None):
        """
        Some environment parameters are stored in the integration object for convenience.

        :param create_batch: Flag to decide whether a batch request to be created

        """
        from channel_app.core import settings
        self.create_batch = create_batch
        self.content_type = content_type
        if create_batch and not content_type:
            raise Exception("ContentType not defined")
        self.channel_id = settings.OMNITRON_CHANNEL_ID
        self.catalog_id = settings.OMNITRON_CATALOG_ID
        self.base_url = settings.OMNITRON_URL
        self.username = settings.OMNITRON_USER
        self.password = settings.OMNITRON_PASSWORD
        # TODO initialize api in init and check whether it is already initialized on enter method

    def __enter__(self):
        self.api = OmnitronApiClient(base_url=self.base_url,
                                     username=self.username,
                                     password=self.password)
        self.channel_is_active = self.channel.is_active
        if not self.channel_is_active:
            return
        if self.create_batch:
            self.batch_request = ClientBatchRequest(
                channel_id=self.channel_id).create()
            self.batch_request.content_type = self.content_type
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.api
        if isinstance(exc_val, Exception) and not self.channel_is_active:
            return True
