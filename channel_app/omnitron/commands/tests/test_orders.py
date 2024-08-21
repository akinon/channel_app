from dataclasses import asdict
from unittest.mock import MagicMock, patch
from omnisdk.base_client import BaseClient
from omnisdk.omnitron.endpoints import (
    ChannelCargoEndpoint, 
    ChannelCustomerEndpoint,
    ChannelOrderEndpoint,
    ChannelOrderItemEndpoint,
    ChannelCancellationRequestEndpoint,
    ChannelBatchRequestEndpoint)
from omnisdk.omnitron.models import CancellationRequest

from channel_app.core.data import CancellationRequestDto, CustomerDto, OrderBatchRequestResponseDto
from channel_app.core.tests import BaseTestCaseMixin
from channel_app.omnitron.commands.orders.cargo_companies import GetCargoCompany
from channel_app.omnitron.commands.orders.customers import GetOrCreateCustomer
from channel_app.omnitron.commands.orders.orders import (
    CreateCancellationRequest,
    GetCancellationRequestUpdates, 
    GetOrderItems, 
    GetOrderItemsWithOrder, 
    ProcessOrderBatchRequests,
    ChannelIntegrationActionEndpoint)
from channel_app.omnitron.constants import (
    BatchRequestStatus,
    CancellationType, 
    CustomerIdentifierField)


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
        

class TestGetOrCreateCustomer(BaseTestCaseMixin):
    """
    Test case for GetOrCreateCustomer
    
    run: python -m unittest channel_app.omnitron.commands.tests.test_orders.TestGetOrCreateCustomer
    """

    def setUp(self) -> None:
        self.instance = GetOrCreateCustomer(
            integration=self.mock_integration,
        )
        self.instance.objects: CustomerDto = CustomerDto(
            email="john.doe@akinon.com",
            first_name="John",
            last_name="Doe",
            channel_code="1",
            extra_field={},
            phone_number="05556667788",
            is_active=True,
        )
        self.customer_endpoint_response_data = {
            'pk': 1, 
            'channel': 1, 
            'email': 'john.doe@akinon.com', 
            'first_name': 'John', 
            'last_name': 'Doe', 
            'phone_number': 
            '05556667788', 
            'is_active': True, 
            'channel_code': '1', 
            'erp_code': None, 
            'extra_field': {}, 
            'modified_date': '2024-01-29T08:27:18.399594Z', 
            'created_date': '2024-01-29T08:27:18.399484Z', 
            'date_joined': None, 
            'email_allowed': False, 
            'sms_allowed': False, 
            'call_allowed': False, 
            'gender': None, 
            'attributes': {}, 
            'user_type': None, 
            'date_of_birth': None, 
            'attributes_kwargs': {}, 
            'localized_attributes': {}, 
            'localized_attributes_kwargs': {}
        }
        self.customer_endpoint_response = [
            MagicMock(**self.customer_endpoint_response_data)
        ]

    @patch.object(GetOrCreateCustomer, 'get_customer')
    def test_get_data(self, mock_get_customer):
        mock_get_customer.return_value = [self.instance.objects]
        data = self.instance.get_data()
        
        self.assertEqual(len(data), 1)

        data = data[0]

        for key, value in asdict(self.instance.objects).items():
            self.assertEqual(getattr(data, key), value)

    def test_get_customer_identifier_is_email(self):
        self.instance.integration.channel.conf = {
            "CUSTOMER_IDENTIFIER_FIELD": CustomerIdentifierField.email
        }

        response = MagicMock()
        response.list.return_value = self.customer_endpoint_response

        with patch.object(
            ChannelCustomerEndpoint, 
            '__new__', 
            return_value=response
        ):
            customers = self.instance.get_customer(self.instance.objects)
            self.assertEqual(len(customers), 1)

            customer = customers[0]

            for key, value in self.customer_endpoint_response_data.items():
                self.assertEqual(getattr(customer, key), value)
            

    def test_get_customer_identifier_is_phone_number(self):
        self.instance.integration.channel.conf = {
            "CUSTOMER_IDENTIFIER_FIELD": CustomerIdentifierField.phone_number
        }

        response = MagicMock()
        response.list.return_value = self.customer_endpoint_response

        with patch.object(
            ChannelCustomerEndpoint,
            '__new__',
            return_value=response
        ):
            customers = self.instance.get_customer(self.instance.objects)
            self.assertEqual(len(customers), 1)

            customer = customers[0]

            for key, value in self.customer_endpoint_response_data.items():
                self.assertEqual(getattr(customer, key), value)
            
    def test_get_customer_email_filter_incorrect_exception(self):
        self.instance.integration.channel.conf = {
            "CUSTOMER_IDENTIFIER_FIELD": CustomerIdentifierField.email
        }

        response = MagicMock()
        response.list.return_value = [MagicMock()]

        with patch.object(
            ChannelCustomerEndpoint,
            '__new__',
            return_value=response
        ):
            with self.assertRaises(
                Exception, 
                msg="Customer email filter incorrect"
            ):
                self.instance.get_customer(self.instance.objects)

    def test_get_customer_phone_number_filter_incorrect_exception(self):
        self.instance.integration.channel.conf = {
            "CUSTOMER_IDENTIFIER_FIELD": CustomerIdentifierField.phone_number
        }

        response = MagicMock()
        response.list.return_value = [MagicMock()]

        with patch.object(
            ChannelCustomerEndpoint,
            '__new__',
            return_value=response
        ):
            with self.assertRaises(
                Exception, 
                msg="Customer phone_number filter incorrect"
            ):
                self.instance.get_customer(self.instance.objects)

    def test_get_customer_must_update_case(self):
        self.instance.integration.channel.conf = {
            "CUSTOMER_IDENTIFIER_FIELD": CustomerIdentifierField.email
        }

        self.instance.objects.first_name = "Jenny"
        self.instance.objects.last_name = "Doey"
        
        response = MagicMock()
        response.list.return_value = self.customer_endpoint_response
        response.update.return_value = MagicMock(
            **self.customer_endpoint_response_data
        )

        with patch.object(
            ChannelCustomerEndpoint,
            '__new__',
            return_value=response
        ):
            customers = self.instance.get_customer(self.instance.objects)
            self.assertEqual(len(customers), 1)

            customer = customers[0]

            for key, value in self.customer_endpoint_response_data.items():
                self.assertEqual(getattr(customer, key), value)


class TestGetCargoCompany(BaseTestCaseMixin):
    """
    Test case for GetCargoCompany

    run: python -m unittest channel_app.omnitron.commands.tests.test_orders.TestGetCargoCompany
    """

    def setUp(self) -> None:
        self.instance = GetCargoCompany(
            integration=self.mock_integration,
        )
        self.instance.objects = 'zyWpJvJdlqRaUfZMtdxgEnzslqXobZWxDGjtlQZtwQUnHtGkpJYzzJuoJhSVQIUW'
        self.channel_cargo_endpoint_response_data = {
            'pk': 1, 
            'name': 
            'ltLIdxIpZlyksSTPEGBytajaRazeShlCzrUZQBIteaHxQElXzQglgnZHZUyuzSqH', 
            'erp_code': 'zyWpJvJdlqRaUfZMtdxgEnzslqXobZWxDGjtlQZtwQUnHtGkpJYzzJuoJhSVQIUW', 
            'shipping_company': 'bringo_express', 
            'modified_date': '2024-01-29T10:04:56.791090Z', 
            'created_date': '2024-01-29T10:04:56.790945Z'
        }
        self.channel_cargo_endpoint_response = [
            MagicMock(**self.channel_cargo_endpoint_response_data)
        ]

    def test_get_cargo_company(self):
        cargo_company = self.instance.get_cargo_company(
            self.channel_cargo_endpoint_response
        )
        self.assertEqual(cargo_company.erp_code, self.instance.objects)

    def test_get_cargo_company_not_exists_exception(self):
        self.instance.objects = 'not_exists_erp_code'

        with self.assertRaises(
            Exception, 
            msg=f"CargoCompany does not exists: {self.instance.objects}"
        ):
            self.instance.get_cargo_company(
                self.channel_cargo_endpoint_response
            )

    @patch.object(GetCargoCompany, 'get_cargo_company')
    def test_get_data(self, mock_get_cargo_company):
        mock_get_cargo_company.return_value = self.channel_cargo_endpoint_response[0]

        response = MagicMock()
        response.list.return_value = self.channel_cargo_endpoint_response
        response.iterator = iter(self.channel_cargo_endpoint_response)

        with patch.object(
            ChannelCargoEndpoint,
            '__new__',
            return_value=response
        ):
            cargo_companies = self.instance.get_data()
            self.assertEqual(len(cargo_companies), 1)

            cargo_company = cargo_companies[0]

            self.assertEqual(
                cargo_company.erp_code, 
                self.channel_cargo_endpoint_response_data['erp_code']
            )
        

class TestGetOrderItems(BaseTestCaseMixin):
    """
    Test case for GetOrderItems
    run: python -m unittest channel_app.omnitron.commands.tests.test_orders.TestGetOrderItems
    """
    def setUp(self) -> None:
        self.instance = GetOrderItems(
            integration=self.mock_integration,
        )
        self.order = MagicMock(
            pk=1,
        )
        self.order_items = [
            MagicMock(
                pk=7,
                order=1,
                content_type='orderitem'
            ),
            MagicMock(
                pk=8,
                order=1,
                content_type='orderitem'
            )
        ]
        self.instance.objects = self.order

    @patch.object(GetOrderItems, 'get_order_items')
    def test_get_data(self, mock_get_order_items):
        mock_get_order_items.return_value = self.order_items
        order_items = self.instance.get_data()
        
        self.assertEqual(len(order_items), 2)

        for order_item in order_items:
            self.assertEqual(order_item.order, self.order.pk)
            self.assertEqual(order_item.content_type, 'orderitem')

    def test_get_order_items(self):
        response = MagicMock()
        response.list.return_value = self.order_items

        with patch.object(
            ChannelOrderItemEndpoint,
            '__new__',
            return_value=response
        ):
            order_items = self.instance.get_order_items(self.order)
            self.assertEqual(len(order_items), 2)

            for order_item in order_items:
                self.assertEqual(order_item.order, self.order.pk)
                self.assertEqual(order_item.content_type, 'orderitem')


class TestGetOrderItemsWithOrder(BaseTestCaseMixin):
    """
    Test case for GetOrderItems
    run: python -m unittest channel_app.omnitron.commands.tests.test_orders.TestGetOrderItemsWithOrder
    """
    def setUp(self) -> None:
        self.instance = GetOrderItemsWithOrder(
            integration=self.mock_integration,
        )
        self.orders = [
            MagicMock(
                pk=1,
                orderitem_set=[],
            ),
        ]
        self.order_items = [
            MagicMock(
                pk=7,
                order=1,
                content_type='orderitem'
            ),
            MagicMock(
                pk=8,
                order=1,
                content_type='orderitem'
            ),
        ]
        self.instance.objects = self.orders

    @patch.object(GetOrderItemsWithOrder, 'get_order_items')
    def test_get_data(self, mock_get_order_items):
        mock_get_order_items.return_value = self.order_items
        orders = self.instance.get_data()

        self.assertEqual(len(orders), 1)
        self.assertEqual(len(orders[0].orderitem_set), 2)

class TestGetCancellationRequestUpdates(BaseTestCaseMixin):
    """
    Test case for GetCancellationRequestUpdates
    run: python -m unittest channel_app.omnitron.commands.tests.test_orders.GetCancellationRequestUpdates
    """

    def setUp(self) -> None:
        self.instance = GetCancellationRequestUpdates(
            integration=self.mock_integration,
        )
       
        self.instance.objects = {
            'status': 'completed',
            'cancellation_type': 'refund'
        }
        self.endpoint = ChannelCancellationRequestEndpoint
        self.cancellation_request = MagicMock(
                pk=1,
                status='completed',
                cancellation_type='refund',
                easy_return=None,
                order_item=1,
            )
        return super().setUp()

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelCancellationRequestEndpoint, '_list')
    @patch.object(ChannelBatchRequestEndpoint, 'update')    
    def test_get_data(self, mock_endpoint, mock_get_instance, mock_batch_request):
        response_data = [
                MagicMock(
                pk=1,
                status='completed',
                cancellation_type=CancellationType.refund.value,
                easy_return=None,
                order_item=1,
            ),
                MagicMock(
                pk=2,
                status='completed',
                cancellation_type=CancellationType.refund.value,
                easy_return=None,
                order_item=2,
            )
        ]
        response = MagicMock()
        response.list.return_value = response_data
        with patch.object(self.endpoint, '__new__', return_value=response):
            data = self.instance.get_data()
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0].status, self.instance.objects['status'])

    @patch.object(GetCancellationRequestUpdates, 'get_cancellation_requests')
    def test_update_cancellation_request(self, mock_get_cancellation_requests):
        mock_get_cancellation_requests.return_value = self.cancellation_request
        self.instance.get_cancellation_requests(self.cancellation_request)
        self.assertEqual(self.cancellation_request.status, self.instance.objects['status'])
        self.assertEqual(self.cancellation_request.cancellation_type, self.instance.objects['cancellation_type'])


class TestCreateCancellationRequest(BaseTestCaseMixin):
    """
    Test case for CreateCancellationRequest
    run: python -m unittest channel_app.omnitron.commands.tests.test_orders.TestCreateCancellationRequest
    """

    def setUp(self) -> None:
        self.instance = CreateCancellationRequest(
            integration=self.mock_integration)

        self.endpoint = ChannelCancellationRequestEndpoint
        self.instance.objects = CancellationRequestDto(
            order_item='1',
            reason='reason_code',
            remote_id='2',
            cancellation_type=CancellationType.refund.value)
        return super().setUp()

    @patch.object(BaseClient, 'get_instance')
    @patch.object(CreateCancellationRequest, 'get_omnitron_order_item')
    def test_get_data(self, mock_get_instance, mock_get_omnitron_order_item):
        mock_get_omnitron_order_item.return_value = 1
        response_data = CancellationRequest(
                pk=1,
                status='waiting',
                cancellation_type='refund',
                easy_return=None,
                order_item=1,
            )
        response = MagicMock()
        response.create.return_value = response_data

        with patch.object(self.endpoint, '__new__', return_value=response):
            data = self.instance.get_data()
            self.assertIsInstance(data, CancellationRequest)
