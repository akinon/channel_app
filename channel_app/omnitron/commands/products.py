from typing import List, Union

from omnisdk.omnitron.endpoints import ChannelBatchRequestEndpoint, \
    ChannelIntegrationActionEndpoint, ChannelAttributeConfigEndpoint, \
    ChannelCategoryNodeEndpoint, ChannelCategoryTreeEndpoint, \
    ChannelProductCategoryEndpoint
from omnisdk.omnitron.endpoints import ChannelProductEndpoint, \
    ChannelProductStockEndpoint, \
    ChannelProductPriceEndpoint, ChannelMappedProductEndpoint
from omnisdk.omnitron.models import Product, IntegrationAction, \
    ChannelAttributeConfig, ProductStock, ProductPrice
from requests import HTTPError

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.data import ProductBatchRequestResponseDto
from channel_app.core.utilities import split_list
from channel_app.omnitron.commands.batch_requests import ProcessBatchRequests
from channel_app.omnitron.constants import ContentType, FailedReasonType, \
    BatchRequestStatus, ResponseStatus


class GetInsertedProducts(OmnitronCommandInterface):
    endpoint = ChannelProductEndpoint
    path = "inserts"
    BATCH_SIZE = 100
    content_type = ContentType.product.value

    def get_data(self) -> List[Product]:
        limit = self.BATCH_SIZE
        if self.objects and "limit" in self.objects:
            limit = self.objects["limit"]
        products = self.get_products(limit=limit)
        return products

    @property
    def update_state(self, *args, **kwargs):
        return BatchRequestStatus.commit

    def validated_data(self, data: List[Product]) -> List[Product]:
        formatted_data = [product for product in data
                          if not getattr(product, "failed_reason_type", None)]
        return formatted_data

    def get_products(self, limit: int) -> List[Product]:
        params = {"product_type": 0, "limit": limit}
        language = getattr(self, "param_language", None)
        if language:
            products = self.endpoint(
                path=self.path,
                channel_id=self.integration.channel_id).list(
                headers={"Accept-Language": language}, params=params)
        else:
            products = self.endpoint(
                path=self.path,
                channel_id=self.integration.channel_id).list(params=params)

        products = products[:limit]

        object_list = self.create_batch_objects(
            data=products,
            content_type=ContentType.product.value)
        self.update_batch_request(object_list)

        return products


class GetProductCategoryNodes(OmnitronCommandInterface):
    endpoint = ChannelCategoryNodeEndpoint
    BATCH_SIZE = 100
    content_type = ContentType.product.value

    def get_data(self) -> List[Product]:
        """
        :return:
        """
        products = self.objects
        self.get_product_category(products)
        return products

    def normalize_response(self, data, response) -> List[object]:
        failed_products = [failed_product[0] for failed_product in
                           self.failed_object_list]
        object_list = self.create_batch_objects(
            data=failed_products,
            content_type=ContentType.product.value)
        self.update_batch_request(object_list)
        return data

    def get_product_category(self, products: List[Product]) -> List[Product]:
        if not products:
            empty_list: List[Product] = []
            return empty_list

        category_tree_id = self.integration.channel.category_tree
        category_tree = ChannelCategoryTreeEndpoint(
            channel_id=self.integration.channel_id).retrieve(
            id=category_tree_id)
        category_tree_path = category_tree.category_root["path"]

        product_category_endpoint = ChannelProductCategoryEndpoint(
            channel_id=self.integration.channel_id, path="detailed")

        for product in products:
            product_categories = product_category_endpoint.list(
                params={"product": product.pk})
            for item in product_category_endpoint.iterator:
                product_categories.extend(item)
            category_node_list = []
            for product_category in product_categories:
                if not str(product_category.category["path"]).startswith(
                        category_tree_path):
                    continue
                category_node_list.append(product_category.category)
            if not category_node_list:
                product.failed_reason_type = FailedReasonType.channel_app.value
                self.failed_object_list.append(
                    (product, ContentType.product.value,
                     "ProductCategoryNotFound"))
                continue
            product.category_nodes = category_node_list
        return products


class GetProductCategoryNodesWithIntegrationAction(GetProductCategoryNodes):

    def get_data(self) -> List[Product]:
        """
        :return:
        """
        products = super(GetProductCategoryNodesWithIntegrationAction,
                         self).get_data()
        self.get_category_node_integration_action(products)
        return products

    def get_category_node_integration_action(self, products: List[Product]):
        if not products:
            return []

        category_node_ias_map = {}
        for chunk in split_list(products, 20):
            endpoint = ChannelIntegrationActionEndpoint(
                channel_id=self.integration.channel_id)
            products_category_node_ids = [
                str(product.category_nodes[0].get('pk')) for product
                in chunk if product.category_nodes[0].get('pk')]
            category_node_ias = endpoint.list(
                params={"object_id__in": ",".join(products_category_node_ids),
                        "content_type_name": ContentType.category_node.value,
                        "channel_id": self.integration.channel_id,
                        "sort": "id"
                        })

            for category_node_ias_batch in endpoint.iterator:
                category_node_ias.extend(category_node_ias_batch)

            category_node_integrations_by_id = {ia.object_id: ia for ia in
                                                category_node_ias}
            category_node_ias_map.update(category_node_integrations_by_id)

        for product in products:
            product.category_nodes[0][
                'integration_action'] = category_node_ias_map.get(
                product.category_nodes[0].get('pk'))

        return products


class GetMappedProducts(OmnitronCommandInterface):
    endpoint = ChannelMappedProductEndpoint
    content_type = ContentType.product.value

    def get_data(self) -> List[Product]:
        products = self.get_mapping(self.objects)
        return products

    def normalize_response(self, data, response) -> List[object]:
        failed_products = [failed_product[0] for failed_product in
                           self.failed_object_list]
        object_list = self.create_batch_objects(
            data=failed_products,
            content_type=ContentType.product.value)
        self.update_batch_request(object_list)
        return data

    def validated_data(self, data) -> List[Product]:
        """
        mapped_attributes = {
            "pk": 370,
            "mapped_attributes": {
                "Araba Ağırlığı": "",
                "Yaş Grubu": "",
                "Garanti Süresi": "2",
                "Taşıma Kapasitesi": "",
                "Renk": "Kırmızı",
                "Ek Özellikler": "WHITE_fixed-deger-123_1",
                "Taşma Emniyeti": "WHITE",
                "Cinsiyet": "std",
                "Desi": "",
                "Materyal": "WHITE"
            },
            "attribute_set_id": 1,
            "attribute_set_name": "3 Tekerlekli Bebek Arabası",
            "attribute_set_remote_id": null,
            "mapped_attribute_values": {
                "attribute_omnitron_id": {
                    "attribute_name": "Cinsiyet",
                    "label": "Erkek",
                    "value": "1",
                    "attribute_remote_id": 22,
                    "is_required": false,
                    "is_variant": false,
                    "is_custom": false,
                    "is_meta": false
                },
                "attribute_omnitron_id": {
                    "attribute_name": "Renk",
                    "attribute_remote_id": 24,
                    "is_required": false,
                    "is_variant": false,
                    "is_custom": true,
                    "is_meta": false
                }
            }
        }
        :param data:
        :return:
        """
        attribute_set_ids = {}
        for product in data:
            self.check_product(product=product,
                               attribute_set_ids=attribute_set_ids)

        return data

    def check_product(self, product, attribute_set_ids):
        if not getattr(product, "mapped_attributes", None):
            return
        attribute_set_id = product.mapped_attributes.attribute_set_id
        if not attribute_set_id:
            return

        mapped_attribute_values = getattr(product.mapped_attributes,
                                          'mapped_attribute_values', None)
        if not mapped_attribute_values:
            return

        if attribute_set_id in attribute_set_ids:
            attribute_config_list = attribute_set_ids[attribute_set_id]
        else:
            params = {"attribute_set": attribute_set_id, "limit": 10}
            attribute_config_list = self.get_attribute_config_list(
                params=params)
            attribute_set_ids[attribute_set_id] = attribute_config_list

        for config in attribute_config_list:
            self.update_and_check_product(config=config, product=product)

    def update_and_check_product(self, config: ChannelAttributeConfig,
                                 product: Product):
        mapped_attributes = product.mapped_attributes
        mapped_attribute_values = product.mapped_attributes.mapped_attribute_values
        attribute_id = str(config.attribute["pk"])
        attribute_value_conf = mapped_attribute_values.get(attribute_id)
        if not attribute_value_conf:
            if not product.mapped_attributes.mapped_attribute_values.get(
                    attribute_id, None):
                product.mapped_attributes.mapped_attribute_values[
                    attribute_id] = {
                    "attribute_name": config.attribute.get("name"),
                    "attribute_remote_id": config.attribute_remote_id,
                    "is_required": config.is_required,
                    "is_variant": config.is_variant,
                    "is_custom": config.is_custom,
                    "is_meta": config.is_meta}
            return False
        try:
            self.check_attribute_value_defined(config, mapped_attributes)
            self.check_required(product, config,
                                mapped_attributes.mapped_attributes)

        except Exception as e:
            product.failed_reason_type = FailedReasonType.channel_app.value
            self.failed_object_list.append(
                (product, ContentType.product.value, str(e))
            )
            return False

        product.mapped_attributes.mapped_attribute_values[attribute_id].update(
            {"is_required": config.is_required,
             "is_variant": config.is_variant,
             "is_custom": config.is_custom,
             "is_meta": config.is_meta})
        return True

    def get_attribute_config_list(self, params: dict) -> List[
        ChannelAttributeConfig]:
        config_endpoint = ChannelAttributeConfigEndpoint(path="detailed",
                                                         channel_id=self.integration.channel_id)
        configs_data = config_endpoint.list(params=params)
        for config_batch in config_endpoint.iterator:
            configs_data.extend(config_batch)
        return configs_data

    def check_attribute_value_defined(self, config, mapped_attributes_obj):
        mapped_attributes = mapped_attributes_obj.mapped_attributes
        mapped_attribute_values = mapped_attributes_obj.mapped_attribute_values
        attribute_id = str(config.attribute["pk"])

        mapped_value = mapped_attributes.get(config.attribute["name"])
        attribute_value_conf = mapped_attribute_values.get(attribute_id, None)
        if mapped_value and not config.is_custom and not attribute_value_conf:
            message = f'{config.attribute["name"]} : {mapped_value} was not defined' \
                      f' for {config.attribute_set["name"]} attribute set'
            raise Exception(message)

    def check_required(self, product, config, mapped_attributes):
        attribute_name = config.attribute["name"]
        mapped_value = mapped_attributes.get(attribute_name)
        message = f'Missing Required AttributeValue for Product sku: {product.sku}, ' \
                  f'{self.integration.channel_id} - {mapped_value} : {attribute_name}'

        if config.is_required and attribute_name not in mapped_attributes:
            raise Exception(message)
        if config.is_required and mapped_attributes[attribute_name] in (
                None, ""):
            raise Exception(message)

    def get_mapping(self, products: List[Product]) -> List[Product]:
        """
        Get mapping output of the products according to the schema
        definitions for this channel and product

        :param products: List[Product]
        :return: List[Product]
        """
        language = getattr(self, "param_language", None)
        if language:
            headers = {"Accept-Language": language}
        else:
            headers = {}

        mapped_product_endpoint = self.endpoint(
            channel_id=self.integration.channel_id)

        for index, product in enumerate(list(products)):
            try:
                attributes = mapped_product_endpoint.retrieve(headers=headers,
                                                              id=product.pk)
                product.mapped_attributes = attributes
            except HTTPError:
                product.mapped_attributes = {}
                product.failed_reason_type = FailedReasonType.mapping.value
                self.failed_object_list.append(
                    (product, ContentType.product.value, "MappingError"))
                continue

        return products


class GetMappedProductsWithOutCommit(GetMappedProducts):
    def validated_data(self, data) -> List[Product]:
        return data

    def update_batch_request(self, objects_data: list):
        pass


class GetProductPrices(OmnitronCommandInterface):
    endpoint = ChannelProductPriceEndpoint
    CHUNK_SIZE = 50
    content_type = ContentType.product_price.value

    def get_data(self) -> List[Product]:
        products = self.objects

        self.get_product_price(products)
        return products

    def normalize_response(self, data, response) -> List[object]:
        object_list = []
        failed_products = [failed_product[0] for failed_product in
                           self.failed_object_list]
        product_object_list = self.create_batch_objects(
            data=failed_products,
            content_type=ContentType.product.value)
        object_list.extend(product_object_list)

        self.create_integration_actions(data, object_list)
        self.update_batch_request(object_list)
        return data

    def create_integration_actions(self, data, object_list):
        commit_product_prices = [product.productprice for product in data
                                 if not getattr(product, "failed_reason_type",
                                                None)]
        product_price_object_list = self.create_batch_objects(
            data=commit_product_prices,
            content_type=ContentType.product_price.value)
        object_list.extend(product_price_object_list)

    def get_product_price(self, products: List[Product]) -> List[Product]:
        if not products:
            empty_list: List[Product] = []
            return empty_list

        endpoint = self.endpoint(channel_id=self.integration.channel_id)
        product_ids = [str(p.pk) for p in products]
        prices = []
        for chunk in split_list(product_ids, self.CHUNK_SIZE):
            price_batch = self.get_prices(chunk, endpoint)
            if not price_batch:
                break
            prices.extend(price_batch)

        product_prices = {s.product: s for s in prices}

        for index, product in enumerate(products):
            if getattr(product, "failed_reason_type", None):
                continue
            try:
                product.productprice = product_prices[product.pk]
            except KeyError:
                product.failed_reason_type = FailedReasonType.channel_app.value
                self.failed_object_list.append(
                    (product, ContentType.product.value, "PriceNotFound"))
                continue

        return products

    def get_prices(self, chunk, endpoint):
        price_batch = endpoint.list(params={"product__pk__in": ",".join(chunk),
                                            "price_list": self.integration.catalog.price_list})
        for item in endpoint.iterator:
            if not item:
                break
            price_batch.extend(item)
        return price_batch


class GetProductPricesWithOutCommit(GetProductPrices):
    def create_integration_actions(self, data, object_list):
        pass


class GetProductStocks(OmnitronCommandInterface):
    endpoint = ChannelProductStockEndpoint
    content_type = ContentType.product_stock.value
    CHUNK_SIZE = 50

    def get_data(self) -> List[Product]:
        products = self.objects
        self.get_product_stock(products)
        return products

    def normalize_response(self, data, response) -> List[object]:
        object_list = []
        failed_products = [failed_product[0] for failed_product in
                           self.failed_object_list]
        product_object_list = self.create_batch_objects(
            data=failed_products,
            content_type=ContentType.product.value)
        object_list.extend(product_object_list)

        self.create_integration_actions(data, object_list)
        self.update_batch_request(object_list)
        return data

    def create_integration_actions(self, data, object_list):
        commit_product_stocks = [product.productstock for product in data
                                 if not getattr(product, "failed_reason_type",
                                                None)]
        product_stock_object_list = self.create_batch_objects(
            data=commit_product_stocks,
            content_type=ContentType.product_stock.value)
        object_list.extend(product_stock_object_list)

    def get_product_stock(self, products: List[Product]) -> List[Product]:
        if not products:
            empty_list: List[Product] = []
            return empty_list

        product_ids = [str(p.pk) for p in products if
                       not getattr(p, "failed_reason_type", None)]

        endpoint = self.endpoint(channel_id=self.integration.channel_id)
        stocks = []
        for chunk in split_list(product_ids, self.CHUNK_SIZE):
            stock_batch = self.get_stocks(chunk, endpoint)
            if not stock_batch:
                break
            stocks.extend(stock_batch)

        product_stocks = {s.product: s for s in stocks}

        for index, product in enumerate(products):
            if getattr(product, "failed_reason_type", None):
                continue
            try:
                product.productstock = product_stocks[product.pk]
            except KeyError:
                product.failed_reason_type = FailedReasonType.channel_app.value
                self.failed_object_list.append(
                    (product, ContentType.product.value, "StockNotFound"))
                continue

        return products

    def get_stocks(self, chunk, endpoint):
        stock_batch = endpoint.list(params={"product__pk__in": ",".join(chunk),
                                            "stock_list": self.integration.catalog.stock_list})
        for item in endpoint.iterator:
            if not item:
                break
            stock_batch.extend(item)
        return stock_batch


class GetProductStocksWithOutCommit(GetProductStocks):
    def create_integration_actions(self, data, object_list):
        pass


class GetUpdatedProducts(GetInsertedProducts):
    path = "updates"

    def get_data(self) -> List[Product]:
        products = super(GetUpdatedProducts, self).get_data()
        self.get_integration_actions(products)
        return products

    def get_integration_actions(self, products: List[Product]):
        if not products:
            return []

        return_products_as_dict = {}
        for chunk in split_list(products, 20):
            endpoint = ChannelIntegrationActionEndpoint(
                channel_id=self.integration.channel_id)
            product_ids = [str(product.pk) for product in chunk]
            product_ias = endpoint.list(
                params={"object_id__in": ",".join(product_ids),
                        "content_type_name": ContentType.product.value,
                        "channel_id": self.integration.channel_id,
                        "sort": "id"
                        })

            for product_batch in endpoint.iterator:
                product_ias.extend(product_batch)

            product_integrations_by_id = {ia.object_id: ia for ia in
                                          product_ias}
            return_products_as_dict.update(product_integrations_by_id)

        for product in products:
            if product.pk in return_products_as_dict:
                product_ia = return_products_as_dict[product.pk]
                product.integration_action = product_ia

        return products


class GetInsertedOrUpdatedProducts(GetInsertedProducts):
    path = "inserts_or_updates"


class ProcessProductBatchRequests(OmnitronCommandInterface,
                                  ProcessBatchRequests):
    endpoint = ChannelBatchRequestEndpoint
    content_type = ContentType.product.value
    CHUNK_SIZE = 50
    BATCH_SIZE = 100

    def validated_data(self, data: List[ProductBatchRequestResponseDto]):
        for item in data:
            assert isinstance(item, ProductBatchRequestResponseDto)
        return data

    def send(self, validated_data):
        result = self.process_item(validated_data)
        return result

    def check_run(self, is_ok, formatted_data):
        if not is_ok and self.is_batch_request:
            self.integration.batch_request.objects = None
            self.batch_service(self.integration.channel_id).to_fail(
                self.integration.batch_request)
        return False

    @property
    def update_state(self, *args, **kwargs) -> BatchRequestStatus:
        return BatchRequestStatus.done

    def get_channel_items_by_reference_object_ids(self, channel_response,
                                                  model_items_by_content,
                                                  integration_actions):
        channel_items_by_product_id = {}
        for product_id, product in model_items_by_content["product"].items():
            sku = self.get_barcode(obj=product)
            for channel_item in channel_response:
                # TODO: comment
                if channel_item.sku != sku:
                    continue
                remote_item = channel_item
                channel_items_by_product_id[product_id] = remote_item
                break
        return channel_items_by_product_id


class GetDeletedProducts(OmnitronCommandInterface):
    endpoint = ChannelIntegrationActionEndpoint
    content_type = ContentType.integration_action.value
    path = 'deleted'
    BATCH_SIZE = 100

    def get_data(self) -> List[IntegrationAction]:
        products = self.get_deleted_products_ia()

        return products

    def get_deleted_products_ia(self) -> List[IntegrationAction]:
        products_integration_actions = self.endpoint(
            path=self.path,
            channel_id=self.integration.channel_id).list(
            params={"model": ContentType.product.value,
                    "channel_id": self.integration.channel_id,
                    "limit": self.BATCH_SIZE})

        products_integration_actions = products_integration_actions[
                                       :self.BATCH_SIZE]
        return products_integration_actions


class ProcessDeletedProductBatchRequests(ProcessProductBatchRequests):
    """ Manages product deletion process by taking into account the deletion task on channel """
    endpoint = ChannelBatchRequestEndpoint
    content_type = ContentType.batch_request.value
    CHUNK_SIZE = 50
    BATCH_SIZE = 100

    def get_data(self):
        return self.objects

    def validated_data(self, data: List[ProductBatchRequestResponseDto]):
        for item in data:
            assert isinstance(item, ProductBatchRequestResponseDto)
        return data

    def send(self, validated_data):
        result = self.process_item(validated_data)
        return result

    def process_item(self, channel_response):
        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)

        remote_ids = []
        fail_remote_ids = []
        integration_actions = []
        for remote_item in channel_response:
            if remote_item.status == ResponseStatus.success:
                remote_ids.append(remote_item.remote_id)
            else:
                fail_remote_ids.append(remote_item.remote_id)

        if remote_ids:
            integration_actions = self.get_integration_actions_for_remote_ids(
                remote_ids)

            # successful integration action objects are deleted
            for integration_action in integration_actions:
                if integration_action.content_type.get(
                        "model") in [ContentType.product.value,
                                     ContentType.product_price.value,
                                     ContentType.product_stock.value,
                                     ContentType.product_image.value]:
                    endpoint.delete(id=integration_action.pk)

        # faulty integration action objects are reported
        if fail_remote_ids:
            fail_integration_actions = self.get_integration_actions_for_remote_ids(
                fail_remote_ids)

            for integration_action_obj in fail_integration_actions:
                integration_action_obj.failed_reason_type = \
                    FailedReasonType.channel_app.value

            objects_data = self.create_batch_objects(
                data=fail_integration_actions,
                content_type=ContentType.integration_action.value)
            # done
            self.update_batch_request(objects_data=objects_data)
        return integration_actions

    def get_integration_actions_for_remote_ids(self, remote_ids):
        if not remote_ids:
            return []
        integration_actions_list = []
        for chunk in split_list(remote_ids, 10):
            endpoint = ChannelIntegrationActionEndpoint(
                channel_id=self.integration.channel_id)
            integration_actions = endpoint.list(params={
                "remote_id__in": ",".join(str(r) for r in chunk),
                "channel": self.integration.channel_id,
                "sort": "id"
            })
            for ia_batch in endpoint.iterator:
                if not ia_batch:
                    break
                integration_actions.extend(ia_batch)
            integration_actions_list.extend(integration_actions)
        return [ial for ial in integration_actions_list if ial.remote_id in remote_ids]


class GetProductObjects(OmnitronCommandInterface):
    endpoint = ChannelProductEndpoint
    content_type = ContentType.product.value
    CHUNK_SIZE = 100
    BATCH_SIZE = 100

    def get_data(self):
        """
        :param self.objects: Union[ProductStock, ProductPrice]

        {
            "pk": 8545,
            "product": 76,
            "stock": 10,
            "stock_list": 3,
            "unit_type": "qty",
            "extra_field": {},
            "sold_quantity_unreported": 0,
            "modified_date": "2021-02-16T10:15:18.856000Z"
        }
        """
        return self.objects

    def validated_data(self, data: Union[ProductStock, ProductPrice]):
        product_ids = []
        for obj in data:
            product_ids.append(str(obj.product))
        return product_ids

    def send(self, validated_data):
        result = self.process_item(validated_data)
        for obj in self.objects:
            obj.product = result.get(obj.product)

        return self.objects

    def process_item(self, validated_data):
        return_products_dict = {}
        for chunk in split_list(validated_data, 20):
            endpoint = ChannelProductEndpoint(
                channel_id=self.integration.channel_id,
            )
            products = endpoint.list(
                params={"pk__in": ",".join(c for c in chunk),
                        "sort": "id"})

            for product in endpoint.iterator:
                if not product:
                    break
                products.extend(product)

            products_dict = {product.pk: product for product in products}
            return_products_dict.update(products_dict)

        return return_products_dict


class GetProductsFromBatchrequest(OmnitronCommandInterface):
    """
    It is the command used to fetch products according to bathcrequest.
    """
    endpoint = ChannelProductEndpoint
    BATCH_SIZE = 100
    CHUNK_SIZE = 100
    content_type = ContentType.product.value

    def get_data(self):
        batch_request = self.objects
        product_integration_actions = self.get_integration_actions_from_batchrequest(
            batch_request)
        integration_action_with_product = self.integration.do_action(
            key="get_content_objects_from_integrations",
            objects=product_integration_actions)
        products = self.convert_integration_action_to_product(
            integration_actions=integration_action_with_product)
        return products

    def convert_integration_action_to_product(self, integration_actions):
        products = []
        for integration_action in integration_actions:
            product = getattr(integration_action, "product", None)
            if product:
                setattr(product, "integration_action", integration_action)
                products.append(product)
        return products

    def get_integration_actions_from_batchrequest(self, batch_request):
        """
        Retrieval of integration actions of product type from omnitron
         according to batch request
        :param batch_request:
        :return: ChannelIntegrationAction
        """
        integration_action_endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        batch_integration_action = integration_action_endpoint.list(
            params={
                "local_batch_id": batch_request.local_batch_id,
                "status": "processing",
                "content_type_name": self.content_type,
                "limit": self.CHUNK_SIZE,
                "sort": "id"})
        for batch in integration_action_endpoint.iterator:
            if not batch:
                break
            batch_integration_action.extend(batch)
        return batch_integration_action

    def validated_data(self, data: List[Product]) -> List[Product]:
        formatted_data = [product for product in data
                          if not getattr(product, "failed_reason_type", None)]
        return formatted_data
