from typing import List

from omnisdk.omnitron.models import (
    Product,
    IntegrationAction,
    BatchRequest,
)

from channel_app.core import settings
from channel_app.core.data import ProductBatchRequestResponseDto, ErrorReportDto
from channel_app.core.settings import OmnitronIntegration, ChannelIntegration
from channel_app.logs.services import LogService
from channel_app.omnitron.batch_request import ClientBatchRequest
from channel_app.omnitron.constants import ContentType


class ProductService(object):
    batch_service = ClientBatchRequest

    def insert_products(
        self,
        add_mapped=True,
        add_stock=True,
        add_price=True,
        add_categories=True,
        is_sync=True,
        is_success_log=True,
    ):
        log_service = LogService()
        log_service.create_flow(name="Insert Products")

        try:
            with log_service.step("insert_products"):
                with OmnitronIntegration(
                    content_type=ContentType.product.value
                ) as omnitron_integration:
                    with log_service.step("get_inserted_products"):
                        products = omnitron_integration.do_action(
                            key="get_inserted_products"
                        )

                    first_product_count = len(products)

                    if add_mapped:
                        with log_service.step("get_mapped_products"):
                            products = products and omnitron_integration.do_action(
                                key="get_mapped_products", objects=products
                            )

                    if add_stock:
                        with log_service.step("get_product_stocks"):
                            products = products and omnitron_integration.do_action(
                                key="get_product_stocks", objects=products
                            )

                    if add_price:
                        with log_service.step("get_product_prices"):
                            products = products and omnitron_integration.do_action(
                                key="get_product_prices", objects=products
                            )

                    if add_categories:
                        with log_service.step("get_product_categories"):
                            products = products and omnitron_integration.do_action(
                                key="get_product_categories", objects=products
                            )

                    if not products:
                        if first_product_count:
                            omnitron_integration.batch_request.objects = None

                            with log_service.step("batch_to_fail"):
                                self.batch_service(
                                    omnitron_integration.channel_id
                                ).to_fail(omnitron_integration.batch_request)

                        return

                    products: List[Product]

                    with log_service.step("send_inserted_products"):
                        response_data, reports, data = ChannelIntegration().do_action(
                            key="send_inserted_products",
                            objects=products,
                            batch_request=omnitron_integration.batch_request,
                            is_sync=is_sync,
                        )

                    # tips
                    response_data: List[ProductBatchRequestResponseDto]
                    reports: List[ErrorReportDto]
                    data: List[Product]

                    if not is_sync:
                        if reports[0].is_ok:

                            with log_service.step("batch_send_to_remote"):
                                self.batch_service(
                                    settings.OMNITRON_CHANNEL_ID
                                ).to_sent_to_remote(
                                    batch_request=omnitron_integration.batch_request
                                )
                        else:
                            is_sync = True

                    if reports and (is_success_log or not reports[0].is_ok):
                        for report in reports:
                            with log_service.step("create_error_report"):
                                omnitron_integration.do_action(
                                    key="create_error_report", objects=report
                                )

                    if is_sync:
                        with log_service.step("process_product_batch_requests"):
                            omnitron_integration.do_action(
                                key="process_product_batch_requests",
                                objects=response_data,
                            )
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    def update_products(
        self,
        add_mapped=True,
        add_stock=True,
        add_price=True,
        add_categories=True,
        is_sync=True,
        is_success_log=True,
    ):
        log_service = LogService()
        log_service.create_flow(name="Update Products")

        try:
            with log_service.step("update_products"):
                with OmnitronIntegration(
                    content_type=ContentType.product.value
                ) as omnitron_integration:
                    with log_service.step("get_updated_products"):
                        products = omnitron_integration.do_action(
                            key="get_updated_products"
                        )

                    first_product_count = len(products)

                    if add_mapped:
                        with log_service.step("get_mapped_products"):
                            products = products and omnitron_integration.do_action(
                                key="get_mapped_products", objects=products
                            )

                    if add_stock:
                        with log_service.step("get_product_stocks"):
                            products = products and omnitron_integration.do_action(
                                key="get_product_stocks", objects=products
                            )

                    if add_price:
                        with log_service.step("get_product_prices"):
                            products = products and omnitron_integration.do_action(
                                key="get_product_prices", objects=products
                            )

                    if add_categories:
                        with log_service.step("get_product_categories"):
                            products = products and omnitron_integration.do_action(
                                key="get_product_categories", objects=products
                            )

                    if not products:
                        if first_product_count:
                            omnitron_integration.batch_request.objects = None
                            with log_service.step("batch_to_fail"):
                                self.batch_service(
                                    omnitron_integration.channel_id
                                ).to_fail(omnitron_integration.batch_request)

                        return

                    products: List[Product]

                    with log_service.step("send_updated_products"):
                        response_data, reports, data = ChannelIntegration().do_action(
                            key="send_updated_products",
                            objects=products,
                            batch_request=omnitron_integration.batch_request,
                            is_sync=is_sync,
                        )

                    # tips
                    response_data: List[ProductBatchRequestResponseDto]
                    reports: List[ErrorReportDto]
                    data: List[Product]

                    if not is_sync:
                        if reports[0].is_ok:
                            with log_service.step("batch_send_to_remote"):
                                self.batch_service(
                                    settings.OMNITRON_CHANNEL_ID
                                ).to_sent_to_remote(
                                    batch_request=omnitron_integration.batch_request
                                )
                        else:
                            is_sync = True

                    if reports and (is_success_log or not reports[0].is_ok):
                        for report in reports:
                            with log_service.step("create_error_report"):
                                omnitron_integration.do_action(
                                    key="create_error_report", objects=report
                                )

                    if is_sync:
                        with log_service.step("process_product_batch_requests"):
                            omnitron_integration.do_action(
                                key="process_product_batch_requests",
                                objects=response_data,
                            )
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    def delete_products(
        self, is_sync=True, is_content_object=True, is_success_log=True
    ):
        log_service = LogService()
        log_service.create_flow("Delete Products")

        try:
            with log_service.step("delete_products"):
                with OmnitronIntegration(
                    content_type=ContentType.integration_action.value
                ) as omnitron_integration:
                    with log_service.step("get_deleted_products"):
                        products_integration_action = omnitron_integration.do_action(
                            key="get_deleted_products"
                        )
                    if not products_integration_action:
                        return

                    with log_service.step("get_content_objects_from_integrations"):
                        products_integration_action = omnitron_integration.do_action(
                            key="get_content_objects_from_integrations",
                            objects=products_integration_action,
                        )
                    products_integration_action: List[IntegrationAction]

                    with log_service.step("send_deleted_products"):
                        response_data, reports, data = ChannelIntegration().do_action(
                            key="send_deleted_products",
                            objects=products_integration_action,
                            batch_request=omnitron_integration.batch_request,
                            is_sync=is_sync,
                        )

                    # tips
                    response_data: List[ProductBatchRequestResponseDto]
                    reports: List[ErrorReportDto]
                    data: List[IntegrationAction]

                    if not is_sync:
                        if reports[0].is_ok:
                            with log_service.step("batch_to_commit"):
                                self.batch_service(
                                    settings.OMNITRON_CHANNEL_ID
                                ).to_commit(
                                    batch_request=omnitron_integration.batch_request
                                )
                            with log_service.step("batch_send_to_remote"):
                                self.batch_service(
                                    settings.OMNITRON_CHANNEL_ID
                                ).to_sent_to_remote(
                                    batch_request=omnitron_integration.batch_request
                                )
                        else:
                            is_sync = True

                    if reports and (is_success_log or not reports[0].is_ok):
                        for report in reports:
                            with log_service.step("create_error_report"):
                                omnitron_integration.do_action(
                                    key="create_error_report", objects=report
                                )

                    if is_sync:
                        with log_service.step("process_delete_product_batch_requests"):
                            omnitron_integration.do_action(
                                key="process_delete_product_batch_requests",
                                objects=response_data,
                            )
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    def get_delete_product_batch_requests(self, is_success_log=True):
        log_service = LogService()
        log_service.create_flow(name="Get Delete Product Batch Requests")

        try:
            with log_service.step("get_delete_product_batch_requests"):
                with OmnitronIntegration(create_batch=False) as omnitron_integration:
                    with log_service.step("get_batch_requests"):
                        batch_request_data = omnitron_integration.do_action(
                            "get_batch_requests",
                            params={
                                "status": ["sent_to_remote", "ongoing"],
                                "content_type": ContentType.integration_action.value,
                            },
                        )
                    # tips
                    batch_request_data: List[BatchRequest]

                    for batch_request in batch_request_data:
                        with log_service.step("check_deleted_products"):
                            (
                                response_data,
                                report,
                                data,
                            ) = ChannelIntegration().do_action(
                                key="check_deleted_products",
                                objects=batch_request,
                                batch_request=batch_request,
                            )

                        # tips
                        response_data: List[ProductBatchRequestResponseDto]
                        report: ErrorReportDto
                        data: BatchRequest

                        if report and (is_success_log or not report.is_ok):
                            with log_service.step("create_error_report"):
                                omnitron_integration.do_action(
                                    key="create_error_report", objects=report
                                )
                        if response_data:
                            omnitron_integration.batch_request = batch_request
                            with log_service.step(
                                "process_delete_product_batch_requests"
                            ):
                                omnitron_integration.do_action(
                                    key="process_delete_product_batch_requests",
                                    objects=response_data,
                                )
        except Exception as fatal:
            log_service.add_exception(fatal)
        finally:
            log_service.save()

    def get_product_batch_requests(self, is_success_log=True):
        log_service = LogService()
        log_service.create_flow(name="Get Product Batch Requests")

        try:
            with log_service.step("get_product_batch_requests"):
                with OmnitronIntegration(create_batch=False) as omnitron_integration:
                    with log_service.step("get_batch_requests"):
                        batch_request_data = omnitron_integration.do_action(
                            "get_batch_requests",
                            params={
                                "status": ["sent_to_remote", "ongoing"],
                                "content_type": ContentType.product.value,
                            },
                        )
                    # tips
                    batch_request_data: List[BatchRequest]

                    for batch_request in batch_request_data:
                        with log_service.step("check_products"):
                            (
                                response_data,
                                report,
                                data,
                            ) = ChannelIntegration().do_action(
                                key="check_products",
                                objects=batch_request,
                                batch_request=batch_request,
                            )

                        # tips
                        response_data: List[ProductBatchRequestResponseDto]
                        report: ErrorReportDto
                        data: BatchRequest

                        if report and (is_success_log or not report.is_ok):
                            with log_service.step("create_error_report"):
                                omnitron_integration.do_action(
                                    key="create_error_report", objects=report
                                )

                        if response_data:
                            omnitron_integration.batch_request = batch_request
                            with log_service.step("process_product_batch_requests"):
                                omnitron_integration.do_action(
                                    key="process_product_batch_requests",
                                    objects=response_data,
                                )
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()
