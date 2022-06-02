from dataclasses import asdict
from typing import List, Generator, Union

from omnisdk.omnitron.models import (Customer, Address, CargoCompany, Order,
                                     BatchRequest)

from channel_app.core import settings
from channel_app.core.data import (OmnitronCreateOrderDto, OmnitronOrderDto,
                                   ChannelCreateOrderDto,
                                   ErrorReportDto,
                                   OrderBatchRequestResponseDto, CancelOrderDto)
from channel_app.core.settings import OmnitronIntegration, ChannelIntegration
from channel_app.omnitron.batch_request import ClientBatchRequest
from channel_app.omnitron.constants import ContentType
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
            while True:
                try:
                    channel_create_order, report, _ = next(get_orders)
                except StopIteration:
                    break

                # tips
                channel_create_order: ChannelCreateOrderDto
                report: ErrorReportDto

                if report and (is_success_log or not report.is_ok):
                    omnitron_integration.do_action(
                        key='create_error_report',
                        objects=report)

                self.create_order(omnitron_integration=omnitron_integration,
                                  channel_order=channel_create_order)

    def create_order(self, omnitron_integration: OmnitronIntegration,
                     channel_order: ChannelCreateOrderDto
                     ) -> Union[Order, None]:
        order = channel_order.order

        try:
            customer = omnitron_integration.do_action(
                key='get_or_create_customer',
                objects=order.customer)
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

        shipping_address: Address
        billing_address: Address
        try:
            cargo_company = omnitron_integration.do_action(
                key='get_cargo_company',
                objects=order.cargo_company
            )[0]
        except CargoCompanyException:  # TODO: exception
            # log
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
            order = orders[0]  # formatted_data
        except OrderException:
            return

        omnitron_integration.do_action(
            key='create_order_shipping_info',
            objects=order
        )
        return order

    def update_orders(self, is_sync=True, is_success_log=True):
        with OmnitronIntegration(
                content_type=ContentType.order.value) as omnitron_integration:
            orders = omnitron_integration.do_action(key='get_orders')
            orders: List[Order]

            if not orders:
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
                key='get_cancelled_orders')
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
