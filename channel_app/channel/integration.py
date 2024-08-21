import requests

from channel_app.channel.commands.orders.orders import (
    GetCancellationRequests, GetOrders, CheckOrders, SendUpdatedOrders, 
    GetCancelledOrders, GetUpdatedOrderItems, UpdateCancellationRequest)
from channel_app.channel.commands.product_images import (
    SendUpdatedImages, SendInsertedImages, CheckImages)
from channel_app.channel.commands.product_prices import (
    CheckPrices, SendInsertedPrices, SendUpdatedPrices)
from channel_app.channel.commands.product_stocks import (
    SendUpdatedStocks, CheckStocks, SendInsertedStocks)
from channel_app.channel.commands.products import (
    SendInsertedProducts, CheckProducts, CheckDeletedProducts,
    SendUpdatedProducts, SendDeletedProducts)
from channel_app.channel.commands.setup import (
    GetCategoryTreeAndNodes, GetCategoryAttributes, GetChannelConfSchema,
    GetAttributes)
from channel_app.core.integration import BaseIntegration


class ChannelIntegration(BaseIntegration):
    """
    Communicates with the Channel Api services through the commands defined.

    If an Api Client class is developed, initialization and deletion should be handled in
    ChannelIntegration class so that commands have easier access to the api object.
    """
    _sent_data = {}
    actions = {
        "send_inserted_products": SendInsertedProducts,
        "send_updated_products": SendUpdatedProducts,
        "send_deleted_products": SendDeletedProducts,
        "check_products": CheckProducts,
        "check_deleted_products": CheckDeletedProducts,
        "send_updated_stocks": SendUpdatedStocks,
        "send_inserted_stocks": SendInsertedStocks,
        "send_updated_prices": SendUpdatedPrices,
        "send_inserted_prices": SendInsertedPrices,
        "send_updated_images": SendUpdatedImages,
        "send_inserted_images": SendInsertedImages,
        "check_stocks": CheckStocks,
        "check_prices": CheckPrices,
        "check_images": CheckImages,
        "get_category_tree_and_nodes": GetCategoryTreeAndNodes,
        "get_channel_conf_schema": GetChannelConfSchema,
        "get_category_attributes": GetCategoryAttributes,
        "get_attributes": GetAttributes,
        "get_orders": GetOrders,
        "get_updated_order_items": GetUpdatedOrderItems,
        "send_updated_orders": SendUpdatedOrders,
        "check_orders": CheckOrders,
        "get_cancelled_orders": GetCancelledOrders,
        "get_cancellation_requests": GetCancellationRequests,
        "update_cancellation_request": UpdateCancellationRequest,
    }

    def __init__(self):
        from channel_app.core import settings
        self.channel_id = settings.OMNITRON_CHANNEL_ID
        self.catalog_id = settings.OMNITRON_CATALOG_ID

    def create_session(self):
        from channel_app.core import settings

        session = requests.Session()
        connections = self.channel.conf.get(
            'connection_pool_count', settings.DEFAULT_CONNECTION_POOL_COUNT)
        max_size = self.channel.conf.get(
            'connection_pool_max_size', settings.DEFAULT_CONNECTION_POOL_MAX_SIZE)
        retry = self.channel.conf.get(
            'connection_pool_retry', settings.DEFAULT_CONNECTION_POOL_RETRY)

        adapter = requests.adapters.HTTPAdapter(pool_connections=connections,
                                                pool_maxsize=max_size,
                                                max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    @property
    def _session(self):
        __session = getattr(self, "__session", None)
        if __session:
            return __session

        session = self.create_session()
        setattr(self, "__session", session)
        return session


