from unittest.mock import MagicMock, patch
from omnisdk.base_client import BaseClient
from omnisdk.omnitron.endpoints import ChannelOrderEndpoint
from channel_app.core.data import OrderBatchRequestResponseDto
from channel_app.core.tests import BaseTestCaseMixin
from channel_app.omnitron.commands.orders.orders import ProcessOrderBatchRequests
from channel_app.omnitron.constants import BatchRequestStatus


class TestProcessOrderBatchRequests(BaseTestCaseMixin):
    """
    Test case for ProcessOrderBatchRequests
    
    run: python -m unittest channel_app.omnitron.commands.tests.test_orders.TestProcessOrderBatchRequests
    """

    def setUp(self) -> None:
        self.instance = ProcessOrderBatchRequests(
            integration=self.mock_integration,
        )
        self.instance.objects = [
            OrderBatchRequestResponseDto(
                status='fail',
                remote_id='',
                number='1',
                message='Error message'
            ),
            OrderBatchRequestResponseDto(
                status='success',
                remote_id='123',
                number='2',
                message=''
            )
        ]
        self.integration_actions = [
            MagicMock(
                id=1,
                channel=1,
                content_type={
                    'model': 'order'
                },
                remote_id='1',
                object_id=1,
            ),
            MagicMock(
                id=2,
                channel=1,
                content_type={
                    'model': 'order'
                },
                remote_id='2',
                object_id=2,
            )
        ]
        self.order_obj = MagicMock(
            pk=1,
        )

    def test_validated_data(self):
        data = self.instance.validated_data(self.instance.objects)
        self.assertEqual(len(data), 2)
        self.assertIsInstance(data[0], OrderBatchRequestResponseDto)
        self.assertIsInstance(data[1], OrderBatchRequestResponseDto)

    def test_update_state(self):
        result = self.instance.update_state
        self.assertEqual(result, BatchRequestStatus.commit)

    def test_get_remote_order_number(self):
        data = self.instance.get_remote_order_number(
            integration_actions=self.integration_actions,
            obj=self.order_obj,
        )
        self.assertEqual(data, self.integration_actions[0].remote_id)

    def test_get_remote_order_number_content_type_is_not_order(self):
        self.integration_actions[0].content_type = {
            'model': 'product'
        }
        data = self.instance.get_remote_order_number(
            integration_actions=self.integration_actions,
            obj=self.order_obj,
        )
        self.assertIsNone(data)

    def test_get_channel_items_by_reference_object_ids(self):
        channel_response = [
            MagicMock(number='1'),
            MagicMock(number='2'),
        ]
        model_items_by_content = {
            "order": {
                "1": MagicMock(pk=1),
                "2": MagicMock(pk=2),
            }
        }
        integration_actions = self.integration_actions
        result = self.instance.get_channel_items_by_reference_object_ids(
            channel_response,
            model_items_by_content,
            integration_actions
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result.get('1').number, "1")
        self.assertEqual(result.get('2').number, "2")

    def test_get_orders_with_empty_list(self):
        id_list = []
        result = self.instance.get_orders(id_list)
        self.assertEqual(len(result), 0)

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelOrderEndpoint, '_list')
    def test_get_orders(self, mock_endpoint, mock_get_instance):
        response_data = [
            MagicMock(pk=1),
            MagicMock(pk=2),
        ]
        response = MagicMock()
        response.list.return_value = response_data

        with patch.object(ChannelOrderEndpoint, '__new__', return_value=response):
            result = self.instance.get_orders(['1', '2'])
            self.assertEqual(len(result), 2)
            self.assertEqual(result.get(1).pk, response_data[0].pk)
            self.assertEqual(result.get(2).pk, response_data[1].pk)

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ProcessOrderBatchRequests, 'get_orders')
    def test_group_model_items_by_content_type(
        self,
        mock_get_orders, 
        mock_get_instance
    ):
        mock_get_orders.return_value = [
            MagicMock(pk=1),
            MagicMock(pk=2),
        ]
        items_by_content = {
            "order": {
                "1": MagicMock(pk=1),
                "2": MagicMock(pk=2),
            }
        }
        data = self.instance.group_model_items_by_content_type(items_by_content)
        self.assertEqual(len(data), 1)
        self.assertEqual(len(data.get('order')), 2)
        