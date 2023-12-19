from unittest.mock import MagicMock, patch
from omnisdk.base_client import BaseClient
from omnisdk.omnitron.endpoints import (
    ChannelIntegrationActionEndpoint,
    ChannelProductEndpoint, 
)
from omnisdk.omnitron.models import ChannelAttributeConfig

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.tests import BaseTestCaseMixin
from channel_app.omnitron.commands.products import (
    GetDeletedProducts,
    GetInsertedProducts,
    GetUpdatedProducts,
    Product, GetMappedProducts, GetProductPrices,
)
from channel_app.omnitron.constants import BatchRequestStatus


class TestGetInsertedProducts(BaseTestCaseMixin):
    """
    Test case for GetInsertedProducts
    
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetInsertedProducts
    """
    def setUp(self) -> None:
        self.get_inserted_products = GetInsertedProducts(
            integration=self.mock_integration
        )
        self.sample_products = [
            Product(name='test', failed_reason_type=None), 
            Product(name='test2', failed_reason_type='error')
        ]
        self.limit = 1
    
    @patch.object(GetInsertedProducts, 'get_products')
    def test_get_data(self, mock_get_products):
        mock_get_products.return_value = [self.sample_products[0]]
        self.get_inserted_products.BATCH_SIZE = self.limit
        
        products = self.get_inserted_products.get_data()
        
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'test')
        mock_get_products.assert_called_once_with(limit=self.limit)

    @patch.object(GetInsertedProducts, 'get_products')
    def test_get_data_with_limit_in_objects_dict(self, mock_get_products):
        mock_get_products.return_value = [self.sample_products[0]]
        self.get_inserted_products.objects = {'limit': self.limit}
        
        products = self.get_inserted_products.get_data()
        
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'test')
        mock_get_products.assert_called_once_with(limit=self.limit)
        
    def test_update_state_property(self):
        self.assertEqual(
            self.get_inserted_products.update_state,
            BatchRequestStatus.commit
        )
        
    def test_validated_data(self):
        validated_products = self.get_inserted_products.validated_data(
            self.sample_products
        )
        
        self.assertIn(self.sample_products[0], validated_products)
        self.assertNotIn(self.sample_products[1], validated_products)
    
    @patch('channel_app.core.clients.OmnitronApiClient')
    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetInsertedProducts, 'update_batch_request')
    @patch.object(GetInsertedProducts, 'create_batch_objects')
    @patch.object(ChannelProductEndpoint, 'list')
    def test_get_products(
        self,
        mock_list,
        mock_create_batch_objects,
        mock_update_batch_request,
        mock_get_instance,
        mock_omnitron_api_client,
    ):
        mock_list.return_value = self.sample_products
        
        products = self.get_inserted_products.get_products(
            limit=self.limit + 1
        )
        
        self.assertEqual(len(products), 2)        
        self.assertEqual(products[0].name, 'test')
        self.assertEqual(products[1].name, 'test2')
        

class TestGetUpdatedProducts(BaseTestCaseMixin):
    """
    Test case for GetUpdatedProducts
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetUpdatedProducts
    """
    def setUp(self):
        self.get_inserted_products = GetInsertedProducts(
            integration=self.mock_integration
        )
        self.get_updated_products = GetUpdatedProducts(
            integration=self.mock_integration
        )
        self.sample_products = [
            Product(
                pk=1, 
                name='test', 
                failed_reason_type=None, 
                modified_date='2021-01-01T00:00:00Z'
            ), 
            Product(
                pk=2, 
                name='test2', 
                failed_reason_type='error', 
                modified_date='2021-01-01T00:00:00Z'
            )
        ]
    
    @patch.object(GetInsertedProducts, 'get_products')
    @patch.object(GetUpdatedProducts, 'get_integration_actions')
    def test_get_data(self, mock_get_integration_actions, mock_get_products):
        mock_get_integration_actions.return_value = self.sample_products
        mock_get_products.return_value = [self.sample_products[0]]
        products = self.get_updated_products.get_data()
        
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'test')

    @patch('channel_app.core.clients.OmnitronApiClient')
    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelIntegrationActionEndpoint, '_list')
    def test_get_integration_actions(
        self,
        mock_list,
        mock_get_instance,
        mock_omnitron_api_client
    ):
        example_response = MagicMock()
        example_response.json.return_value = [
            {
                'id': 1,
                'channel': 1,
                'content_type': 'product',
                'remote_id': 1,
                'object_id': 1,
            },
            {
                'id': 2,
                'channel': 1,
                'content_type': 'product',
                'remote_id': 2,
                'object_id': 2,
            }
        ]
        mock_list.return_value = example_response

        products = self.get_updated_products.get_integration_actions(
            self.sample_products
        )

        for product in products:
            for key, value \
                in example_response.json.return_value[product.pk - 1].items():
                self.assertEqual(
                    getattr(product.integration_action, key), 
                    value
                )

    
    def test_get_integration_actions_without_product(self):
        products = self.get_updated_products.get_integration_actions([])
        self.assertEqual(products, [])


class TestGetInsertedOrUpdatedProducts(
    TestGetInsertedProducts, 
    BaseTestCaseMixin
):
    """
    Test case for GetInsertedOrUpdatedProducts
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetInsertedOrUpdatedProducts
    """
    def setUp(self) -> None:
        self.get_inserted_products = GetInsertedProducts(
            integration=self.mock_integration
        )
        self.get_inserted_products.path = "inserts_or_updates"
        return super().setUp()
    

class TestGetDeletedProducts(BaseTestCaseMixin):
    """
    Test case for GetDeletedProducts
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetDeletedProducts
    """

    def setUp(self) -> None:
        self.get_deleted_products = GetDeletedProducts(
            integration=self.mock_integration
        )
        self.products = [
            {
                "pk": 23,
                "channel": 3,
                "content_type": {
                    "id": 1,
                    "app_label": "products",
                    "model": "product"
                },
                "object_id": 1,
                "remote_id": None,
                "version_date": "2023-11-07T08:58:16.079727Z",
                "state": {},
                "modified_date": "2023-11-08T09:11:56.919937Z",
                "local_batch_id": "7c43e5fb-32be-4a18-a6fa-539c9d2485ee",
                "status": "processing",
                "created_date": "2023-11-08T09:11:56.919929Z"
            }
        ]
    
    @patch.object(GetDeletedProducts, 'get_deleted_products_ia')
    def test_get_data(self, mock_get_deleted_products_ia):
        mock_get_deleted_products_ia.return_value = self.products
        products = self.get_deleted_products.get_data()
        self.assertEqual(len(products), 1)
        
        product = products[0]
        self.assertEqual(product.get('pk'), 23)

    @patch('channel_app.core.clients.OmnitronApiClient')
    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelIntegrationActionEndpoint, '_list')
    def test_get_deleted_products_ia(
        self,
        mock_list,
        mock_get_instance, 
        mock_omnitron_api_client
    ):
        example_response = MagicMock()
        example_response.json.return_value = self.products
        mock_list.return_value = example_response
        products_ia = self.get_deleted_products.get_deleted_products_ia()
        self.assertEqual(len(products_ia), 1)
        
        product = products_ia[0].get_parameters()
        self.assertEqual(product.get('pk'), 23)


class TestGetMappedProducts(BaseTestCaseMixin):
    """
    Test case for GetMappedProducts
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetMappedProducts
    """

    def setUp(self) -> None:
        self.get_mapped_products = GetMappedProducts(
            integration=self.mock_integration
        )
        self.sample_products = [
            Product(
                pk=1,
                name='test',
                failed_reason_type=None,
                modified_date='2021-01-01T00:00:00Z'
            ),
            Product(
                pk=2,
                name='test2',
                failed_reason_type='error',
                modified_date='2021-01-01T00:00:00Z'
            )
        ]

    @patch.object(GetMappedProducts, 'get_mapping')
    def test_get_data(self, mock_get_mapping):
        mock_get_mapping.return_value = self.sample_products
        result = self.get_mapped_products.get_data()
        self.assertEqual(len(result), 2)

    @patch.object(GetMappedProducts, 'check_product')
    def test_validated_data(self, mock_check_product):
        data = self.sample_products
        self.get_mapped_products.validated_data(data)
        self.assertEqual(mock_check_product.call_count, 2)

    @patch.object(GetMappedProducts, 'get_attribute_config_list')
    @patch.object(GetMappedProducts, 'update_and_check_product')
    def test_check_product_gets_attribute_config_list(
        self,
        mock_update_and_check_product,
        mock_get_attribute_config_list
    ):
        product = Product()
        product.mapped_attributes = MagicMock()
        product.mapped_attributes.attribute_set_id = 1
        product.mapped_attributes.mapped_attribute_values = {
            "1": {
                "value": "test"
            }
        }
        mock_get_attribute_config_list.return_value = [
            ChannelAttributeConfig()
        ]
        self.get_mapped_products.check_product(
            product,
            {}
        )
        mock_get_attribute_config_list.assert_called_once()

    @patch.object(GetMappedProducts, 'check_attribute_value_defined')
    @patch.object(GetMappedProducts, 'check_required')
    def test_update_and_check_product_checks_attribute_value_and_required(
        self,
        mock_check_required,
        mock_check_attribute_value_defined
    ):
        product = Product()
        product.mapped_attributes = MagicMock()
        product.mapped_attributes.mapped_attribute_values = {}
        config = ChannelAttributeConfig()
        config.attribute_remote_id = 1
        config.is_required = True
        config.is_variant = True
        config.is_custom = True
        config.is_meta = True
        config.attribute = {
            "pk": 1,
            "name": "test",
        }
        result = self.get_mapped_products.update_and_check_product(
            config,
            product
        )
        self.assertFalse(result)

    @patch.object(GetMappedProducts, 'check_attribute_value_defined')
    @patch.object(GetMappedProducts, 'check_required')
    def test_update_and_check_product(
            self,
            mock_check_required,
            mock_check_attribute_value_defined
    ):
        product = Product()
        product.mapped_attributes = MagicMock()
        product.mapped_attributes.mapped_attribute_values = {
            "1": {
                "value": "test"
            }
        }
        config = ChannelAttributeConfig()
        config.attribute_remote_id = 1
        config.is_required = True
        config.is_variant = True
        config.is_custom = True
        config.is_meta = True
        config.attribute = {
            "pk": 1,
            "name": "test",
        }
        result = self.get_mapped_products.update_and_check_product(
            config,
            product
        )
        self.assertTrue(result)

    @patch.object(GetMappedProducts, 'get_attribute_config_list')
    def test_get_attribute_config_list_returns_configs_data(
        self,
        mock_get_attribute_config_list
    ):
        config = ChannelAttributeConfig()
        mock_get_attribute_config_list.return_value = [
            config
        ]
        result = self.get_mapped_products.get_attribute_config_list(
            {"attribute_set": 1, "limit": 10}
        )
        self.assertEqual(result, [config])

    def test_check_attribute_value_defined_raises_exception_when_mapped_value_not_defined(self):
        mapped_attributes_obj = MagicMock()
        mapped_attributes_obj.mapped_attributes = {"name": "value"}
        mapped_attributes_obj.mapped_attribute_values = {}
        config = ChannelAttributeConfig()
        config.attribute = {"pk": 1, "name": "name"}
        config.attribute_set = {"pk": 1, "name": "name"}
        config.is_custom = False
        with self.assertRaises(Exception):
            self.get_mapped_products.check_attribute_value_defined(
                config,
                mapped_attributes_obj
            )

    def test_check_required_raises_exception_when_required_attribute_missing(self):
        product = Product()
        product.sku = "sku"
        self.get_mapped_products.integration = MagicMock()
        self.get_mapped_products.integration.channel_id = 1
        mapped_attributes = {}
        config = ChannelAttributeConfig()
        config.attribute = {"name": "name"}
        config.is_required = True
        with self.assertRaises(Exception):
            self.get_mapped_products.check_required(
                product,
                config,
                mapped_attributes
            )

    @patch.object(GetMappedProducts, 'get_mapping')
    def test_get_mapping_returns_mapped_products(self, mock_get_mapping):
        product = Product()
        mock_get_mapping.return_value = [product]
        result = self.get_mapped_products.get_mapping([product])
        self.assertEqual(result, [product])

    @patch.object(GetMappedProducts, 'get_mapping')
    def test_get_mapping_returns_empty_list_when_no_products(self, mock_get_mapping):
        mock_get_mapping.return_value = []
        result = self.get_mapped_products.get_mapping([])
        self.assertEqual(result, [])


class TestGetMappedProductsWithOutCommit(TestGetMappedProducts):
    pass


class TestGetProductPrices(BaseTestCaseMixin):
    """
    Test case for GetProductPrices
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetProductPrices
    """

    def setUp(self) -> None:
        self.get_product_prices = GetProductPrices(
            integration=self.mock_integration
        )

    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetProductPrices, 'get_prices')
    def test_successful_product_price_retrieval(
        self,
        mock_get_instance,
        mock_get_prices
    ):
        products = [Product(pk=i, productprice=10) for i in range(1, 6)]
        self.get_product_prices.objects = products

        result = self.get_product_prices.get_data()
        self.assertEqual(result, products)

    @patch.object(GetProductPrices, 'get_prices')
    @patch.object(BaseClient, 'get_instance')
    def test_product_price_retrieval_with_successful_get_product_price(
        self,
        mock_get_instance,
        mock_get_prices
    ):
        products = [Product(pk=i) for i in range(1, 6)]

        price_list = []
        for product in products:
            price = MagicMock()
            price.product = product.pk
            price_list.append(price)

        mock_get_prices.return_value = price_list
        result = self.get_product_prices.get_product_price(products)
        self.assertEqual(result, products)

    @patch.object(GetProductPrices, 'get_prices')
    @patch.object(BaseClient, 'get_instance')
    def test_product_price_retrieval_with_failed_get_product_price(
            self,
            mock_get_instance,
            mock_get_prices
    ):
        products = [Product(pk=i, product_price=0) for i in range(1, 6)]

        price_list = []
        for product in products:
            price = MagicMock()
            price.product = product.pk

            if len(price_list) < len(products) - 1:
                price_list.append(price)

        mock_get_prices.return_value = price_list
        result = self.get_product_prices.get_product_price(products)
        self.assertFalse(hasattr(result[-1], 'productprice'))
