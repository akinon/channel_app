from typing import List
from unittest.mock import patch, MagicMock
from omnisdk.base_client import BaseClient
from channel_app.core.data import BatchRequestResponseDto
from channel_app.core.tests import BaseTestCaseMixin
from channel_app.omnitron.batch_request import ClientBatchRequest
from channel_app.omnitron.commands.product_prices import ProcessPriceBatchRequests
from channel_app.omnitron.constants import BatchRequestStatus


class TestProcessPriceBatchRequests(BaseTestCaseMixin):
    """
    Test case for ProcessPriceBatchRequests
    
    run: python -m unittest channel_app.omnitron.commands.tests.test_product_stocks.TestProcessPriceBatchRequests
    """

    def setUp(self) -> None:
        self.instance = ProcessPriceBatchRequests(
            integration=self.mock_integration
        )
        self.instance.objects: List[BatchRequestResponseDto] = [
            BatchRequestResponseDto(
                status='fail',
                remote_id='',
                sku='1',
                message='Error message'
            ),
            BatchRequestResponseDto(
                status='success',
                remote_id='123',
                sku='2',
                message=''
            ),
        ]
        self.get_products_response = {
            "1": MagicMock(
                sku="1"
            ),
            "2": MagicMock(
                sku="3"
            ),
        }

    def test_get_data(self):
        data = self.instance.get_data()
        self.assertEqual(len(data), 2)
        self.assertIsInstance(data[0], BatchRequestResponseDto)
        self.assertIsInstance(data[1], BatchRequestResponseDto)

    def test_validated_data(self):
        data = self.instance.validated_data(self.instance.objects)
        self.assertEqual(len(data), 2)
        self.assertIsInstance(data[0], BatchRequestResponseDto)
        self.assertIsInstance(data[1], BatchRequestResponseDto)

    def test_validated_data_without_valid_data(self):
        self.instance.objects = [{'test': 'test'}]
        
        with self.assertRaises(AssertionError):
            self.instance.validated_data(self.instance.objects)

    def test_update_state(self):
        data = self.instance.update_state
        self.assertEqual(data, BatchRequestStatus.done)

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ClientBatchRequest, 'to_fail')
    def test_check_run(
        self,
        mock_client_batch_request, 
        mock_get_instance
    ):
        result = self.instance.check_run(False, self.instance.objects)
        self.assertFalse(result, False)

    def test_check_run_without_condition(self):
        result = self.instance.check_run(True, self.instance.objects)
        self.assertFalse(result, False)

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ProcessPriceBatchRequests, 'get_products')
    def test_get_channel_items_by_reference_object_ids(
        self,
        mock_get_products,
        mock_get_instance
    ):
        mock_get_products.return_value = self.get_products_response
        data = {
            "productprice": [
                "1"
            ]
        }
        self.instance.integration.channel.conf = {
            "remote_id_attribute": None
        }
        result = self.instance.get_channel_items_by_reference_object_ids(
            self.instance.objects,
            data,
            None
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result.get("1").sku, "1")
