from dataclasses import asdict
from typing import List, Generator, Union

from requests import exceptions as requests_exceptions

from omnisdk.omnitron.models import (Customer, Address, CargoCompany, Order,
                                     BatchRequest, CancellationRequest)
from omnisdk.omnitron.endpoints import ChannelIntegrationActionEndpoint

from channel_app.core import settings
from channel_app.core.data import (BatchRequestResponseDto, 
                                   CancellationRequestDto, 
                                   ChannelCancellationRequestDto, 
                                   OmnitronCreateOrderDto, 
                                   OmnitronOrderDto,
                                   ChannelCreateOrderDto,
                                   ErrorReportDto,
                                   OrderBatchRequestResponseDto, 
                                   CancelOrderDto,
                                   ChannelUpdateOrderItemDto)
from channel_app.core.settings import OmnitronIntegration, ChannelIntegration
from channel_app.omnitron.batch_request import ClientBatchRequest
from channel_app.omnitron.constants import (BatchRequestStatus, ContentType, 
                                            FailedReasonType)
from channel_app.omnitron.exceptions import (CityException,
                                             TownshipException,
                                             DistrictException,
                                             CargoCompanyException,
                                             OrderException)


class OrderService(object):
    batch_service = ClientBatchRequest

    def fetch_and_create_order(self, is_success_log=True):
        with OmnitronIntegration(
                content_type=ContentType.order.value) as omnitron_integration:
            get_orders = ChannelIntegration().do_action(
                key='get_orders',
                batch_request=omnitron_integration.batch_request
            )

            get_orders: Generator
            order_batch_objects = []
            while True:
                try:
                    channel_create_order, report_list, _ = next(get_orders)
                except StopIteration:
                    break

                # tips
                channel_create_order: ChannelCreateOrderDto
                report_list: List[ErrorReportDto]
                for report in report_list:
                    if is_success_log or not report.is_ok:
                        report.error_code = \
                            f"{omnitron_integration.batch_request.local_batch_id}" \
                            f"-Channel-GetOrders_{channel_create_order.order.number}"
                        omnitron_integration.do_action(
                            key='create_error_report',
                            objects=report)

                order = self.create_order(omnitron_integration=omnitron_integration,
                                          channel_order=channel_create_order)
                if order and omnitron_integration.batch_request.objects:
                    order_batch_objects.extend(omnitron_integration.batch_request.objects)

            omnitron_integration.batch_request.objects = order_batch_objects
            try:
                self.batch_service(settings.OMNITRON_CHANNEL_ID).to_done(
                    batch_request=omnitron_integration.batch_request
                )
            except requests_exceptions.HTTPError as exc:
                if exc.response.status_code == 406 and "batch_request_status_100_1" in exc.response.text:
                    pass
                else:
                    raise exc

    def create_order(self, omnitron_integration: OmnitronIntegration,
                     channel_order: ChannelCreateOrderDto
                     ) -> Union[Order, None]:
        order = channel_order.order

        try:
            customer = omnitron_integration.do_action(
                key='get_or_create_customer',
                objects=order.customer)[0]
        except Exception:
            return

        customer: Customer
        try:
            shipping_address_data = {
                "customer": customer,
                "address": order.shipping_address
            }
            shipping_address = omnitron_integration.do_action(
                key='get_or_create_address',
                objects=shipping_address_data
            )[0]

            billing_address_data = {
                "customer": customer,
                "address": order.billing_address
            }
            billing_address = omnitron_integration.do_action(
                key='get_or_create_address',
                objects=billing_address_data
            )[0]
        except (CityException, TownshipException, DistrictException) as exc:
            omnitron_integration.do_action(
                key='create_address_error_report',
                object=exc)
            return

        except IndexError:
            return

        shipping_address: Address
        billing_address: Address
        try:
            cargo_company = omnitron_integration.do_action(
                key='get_cargo_company',
                objects=order.cargo_company
            )[0]
        except (CargoCompanyException, IndexError):
            return
        cargo_company: CargoCompany

        order_data = asdict(order)
        order_data["customer"] = customer.pk
        order_data["shipping_address"] = shipping_address.pk
        order_data["billing_address"] = billing_address.pk
        order_data["cargo_company"] = cargo_company.pk
        omnitron_order = OmnitronOrderDto(**order_data)
        create_order_dto = OmnitronCreateOrderDto(
            order=omnitron_order,
            order_item=channel_order.order_item)
        try:
            orders: List[Order] = omnitron_integration.do_action(
                key='create_order',
                objects=create_order_dto
            )
            order = orders[0]
        except (OrderException, IndexError):
            return

        return order

    def fetch_and_update_order_items(self, is_success_log=True):
        with OmnitronIntegration(
                content_type=ContentType.order.value) as omnitron_integration:
            get_updated_orders = ChannelIntegration().do_action(
                key='get_updated_order_items',
                batch_request=omnitron_integration.batch_request
            )
            get_updated_orders: Generator
            order_batch_objects = []
            while True:
                try:
                    channel_update_order, report_list, _ = next(get_updated_orders)
                except StopIteration:
                    break

                # tips
                channel_update_order: ChannelUpdateOrderItemDto
                report_list: List[ErrorReportDto]
                for report in report_list:
                    if report and (is_success_log or not report.is_ok):
                        report.error_code = \
                            f"{omnitron_integration.batch_request.local_batch_id}" \
                            f"_GetUpdatedOrders_{channel_update_order.remote_id}"
                        omnitron_integration.do_action(
                            key='create_error_report',
                            objects=report)

                omnitron_integration.do_action(
                    key='update_order_items', objects=channel_update_order)

            omnitron_integration.batch_request.objects = order_batch_objects

            self.batch_service(settings.OMNITRON_CHANNEL_ID).to_done(
                batch_request=omnitron_integration.batch_request
            )


    def update_orders(self, is_sync=True, is_success_log=True,
                      add_order_items=False):
        with OmnitronIntegration(
                content_type=ContentType.order.value) as omnitron_integration:
            orders = omnitron_integration.do_action(key='get_orders')
            orders: List[Order]
            first_order_count = len(orders)
            if add_order_items:
                orders = orders and omnitron_integration.do_action(
                    key='get_order_items_with_order', objects=orders)

            if not orders:
                if first_order_count:
                    omnitron_integration.batch_request.objects = None
                    self.batch_service(omnitron_integration.channel_id).to_fail(
                        omnitron_integration.batch_request
                    )
                return

            response_data, reports, data = ChannelIntegration().do_action(
                key='send_updated_orders',
                objects=orders,
                batch_request=omnitron_integration.batch_request,
                is_sync=True)

            # tips
            response_data: List[OrderBatchRequestResponseDto]
            reports: List[ErrorReportDto]
            data: List[Order]

            if not is_sync:
                if reports[0].is_ok:
                    self.batch_service(
                        settings.OMNITRON_CHANNEL_ID).to_sent_to_remote(
                        batch_request=omnitron_integration.batch_request)
                else:
                    is_sync = True

            if reports and (is_success_log or not reports[0].is_ok):
                for report in reports:
                    omnitron_integration.do_action(
                        key='create_error_report',
                        objects=report)

            if is_sync:
                omnitron_integration.do_action(
                    key='process_order_batch_requests',
                    objects=response_data)

    def get_order_batch_requests(self, is_success_log=False):
        with OmnitronIntegration(create_batch=False) as omnitron_integration:
            batch_request_data = omnitron_integration.do_action(
                'get_batch_requests',
                params={
                    "status": ["sent_to_remote", "ongoing"],
                    "content_type": ContentType.order.value})

            # tips
            batch_request_data: List[BatchRequest]

            for batch_request in batch_request_data:
                response_data, report, data = ChannelIntegration().do_action(
                    key='check_orders',
                    objects=batch_request)

                # tips
                response_data: List[OrderBatchRequestResponseDto]
                report: ErrorReportDto
                data: BatchRequest

                if report and (is_success_log or not report.is_ok):
                    omnitron_integration.do_action(
                        key='create_error_report',
                        objects=report)

                if response_data:
                    omnitron_integration.batch_request = batch_request_data
                    omnitron_integration.do_action(
                        key='process_order_batch_requests',
                        objects=response_data)

    def fetch_and_create_cancel(self, is_success_log=True):
        with OmnitronIntegration(
                content_type=ContentType.order.value) as omnitron_integration:
            get_cancelled_order = ChannelIntegration().do_action(
                key='get_cancelled_orders',
                batch_request=omnitron_integration.batch_request
            )
            get_cancelled_order: Generator

            while True:
                try:
                    cancel_order_dto, report, _ = next(get_cancelled_order)
                except StopIteration:
                    break

                # tips
                cancel_order_dto: CancelOrderDto
                report: ErrorReportDto

                if report and (is_success_log or not report.is_ok):
                    omnitron_integration.do_action(
                        key='create_error_report',
                        objects=report)

                self.create_cancel(omnitron_integration=omnitron_integration,
                                   cancel_order_dto=cancel_order_dto)

    def create_cancel(self, omnitron_integration: OmnitronIntegration,
                      cancel_order_dto: CancelOrderDto):
        success_datas: List[Order] = omnitron_integration.do_action(
            key="create_order_cancel",
            objects=cancel_order_dto)
        try:
            success_data = success_datas[0]
            return success_data
        except IndexError:
            return

    def fetch_and_create_cancellation_requests(self, is_success_log=True):
        with OmnitronIntegration(
                content_type=ContentType.cancellation_request.value) as omnitron_integration:
            get_cancellation_requests = ChannelIntegration().do_action(
                key='get_cancellation_requests',
                batch_request=omnitron_integration.batch_request)
            get_cancellation_requests: Generator
            while True:
                try:
                    cancellation_request, report_list, _ = next(get_cancellation_requests)
                except StopIteration:
                    break

                # tips
                cancellation_request: CancellationRequestDto
                report_list: List[ErrorReportDto]
                for report in report_list:
                    if report and (is_success_log or not report.is_ok):
                        report.error_code = \
                            f"{omnitron_integration.batch_request.local_batch_id}" \
                            f"-Channel-GetCancellationRequests_{cancellation_request.order_item}"                        
                        omnitron_integration.do_action(
                            key='create_error_report',
                            objects=report)
                
                # omnitron integration do action create_cancellation_request
                cancellation_request_response = omnitron_integration.do_action(
                    key='create_cancellation_requests',
                    objects=cancellation_request)
            try:
                self.batch_service(settings.OMNITRON_CHANNEL_ID).to_done(
                    batch_request=omnitron_integration.batch_request
                )
            except requests_exceptions.HTTPError as exc:
                if exc.response.status_code == 406 and "batch_request_status_100_1" in exc.response.text:
                    pass
                else:
                    raise exc                
                
                            
    

    def update_cancellation_requests(self, is_success_log=True):
        with OmnitronIntegration(
                content_type=ContentType.cancellation_request.value) as omnitron_integration:
            cancellation_requests = omnitron_integration.do_action(
                key='get_cancellation_requests_update', objects={})
            cancellation_requests: List[CancellationRequest]

            if not cancellation_requests:
                omnitron_integration.batch_request.objects = None
                self.batch_service(omnitron_integration.channel_id).to_fail(
                    omnitron_integration.batch_request)
                return
            
            batch_request_object_list = []
            
            for cancellation_request in cancellation_requests:
                remote_order_item = self.get_channel_order_item(
                    omnitron_integration, cancellation_request.order_item)
                remote_reason = self.get_channel_reason(
                    omnitron_integration, cancellation_request.reason)
                remote_cancellation_request = self.get_channel_cancellation_request(
                    omnitron_integration, cancellation_request.id)
                
                channel_cancellation_request = ChannelCancellationRequestDto(
                    cancellation_type=cancellation_request.cancellation_type,
                    status=cancellation_request.status,
                    order_item=remote_order_item,
                    reason=remote_reason,
                    description=cancellation_request.description,
                    remote_id=remote_cancellation_request,
                )
                response_data, reports, data = ChannelIntegration().do_action(
                    key='update_cancellation_request',
                    objects=channel_cancellation_request,
                    batch_request=omnitron_integration.batch_request,
                    is_sync=True)

                # tips
                response_data: List[BatchRequestResponseDto]
                reports: List[ErrorReportDto]
                data: List[ChannelCancellationRequestDto]

                if reports and (is_success_log or not reports[0].is_ok):
                    for report in reports:
                        omnitron_integration.do_action(
                            key='create_error_report',
                            objects=report)

                if response_data:
                    failed_reason_type = None
                else:
                    failed_reason_type = FailedReasonType.remote.value
                
                batch_request_object_dto = dict(
                    pk=cancellation_request.id,
                    version_date=cancellation_request.modified_date,
                    content_type=ContentType.cancellation_request.value,
                    failed_reason_type=failed_reason_type,
                    remote_id=remote_cancellation_request)
                
                batch_request_object_list.append(batch_request_object_dto)
                   
            status = BatchRequestStatus.fail.value
            if any([br["failed_reason_type"] is None for br in batch_request_object_list]):
                status = BatchRequestStatus.done.value

            omnitron_integration.batch_request.objects = batch_request_object_list
            service = self.batch_service(omnitron_integration.channel_id)
            
            if status == BatchRequestStatus.done.value:
                service.to_done(batch_request=omnitron_integration.batch_request)
            else:
                service.to_fail(batch_request=omnitron_integration.batch_request)

    def get_channel_order_item(self, omnitron_integration, order_item):
        channel_id = omnitron_integration.channel_id
        end_point = ChannelIntegrationActionEndpoint(
            channel_id=channel_id)
        params = {
            "channel": channel_id,
            "content_type_name": ContentType.order_item.value,
            "object_id": order_item
        }
        integration_action = end_point.list(params=params)
        if not integration_action:
            return Exception("Order item remote id not found: {}".format(order_item))
        if len(integration_action) > 1:
            return Exception("Multiple order item remote id found: {}".format(order_item))
        return integration_action[0].remote_id
    
    def get_channel_reason(self, omnitron_integration, omnitron_reason):
        configuration = omnitron_integration.channel.conf
        # configuration icinde yer alan reason_mapping anahtari bir json objesi,
        # key channel_reason value omnitron_reason olan bir dict objesinden
        # channel_reason'u döndürür
        for channel_reason, omnitron_reason in configuration.get("reason_mapping", {}):
            if omnitron_reason == omnitron_reason:
                return channel_reason
        
        return "10"
    
    def get_channel_cancellation_request(self, omnitron_integration, 
                                   omnitron_cancel_request_pk):
        channel_id = omnitron_integration.channel_id
        end_point = ChannelIntegrationActionEndpoint(
            channel_id=channel_id)
        params = {
            "channel": channel_id,
            "content_type_name": ContentType.cancellation_request.value,
            "object_id": omnitron_cancel_request_pk
        }
        integration_action = end_point.list(params=params)
        if not integration_action:
            return Exception("Cancellation request remote id not found: {}".format(
                omnitron_cancel_request_pk))
        if len(integration_action) > 1:
            return Exception("Multiple cancellation request remote id found: {}".format(
                omnitron_cancel_request_pk))
        return integration_action[0].remote_id

