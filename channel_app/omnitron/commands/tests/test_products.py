from unittest.mock import MagicMock, patch
from omnisdk.base_client import BaseClient
from omnisdk.omnitron.endpoints import (
    ChannelIntegrationActionEndpoint,
    ChannelProductEndpoint, 
)
from channel_app.core.tests import BaseTestCaseMixin
from channel_app.omnitron.commands.products import (
    GetInsertedProducts, 
    GetUpdatedProducts, 
    Product,
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