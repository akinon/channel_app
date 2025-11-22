from typing import List

from omnisdk.omnitron.models import ProductPrice, BatchRequest

from channel_app.core import settings
from channel_app.core.data import BatchRequestResponseDto, ErrorReportDto
from channel_app.core.settings import OmnitronIntegration, ChannelIntegration
from channel_app.logs.services import LogService
from channel_app.omnitron.batch_request import ClientBatchRequest
from channel_app.omnitron.constants import ContentType


class PriceService(object):
    batch_service = ClientBatchRequest

    def update_product_prices(
        self,
        is_sync=True,
        is_success_log=True,
        add_product_objects=False,
        add_stock=False,
    ):
        log_service = LogService()
        log_service.create_flow(name="Update Product Prices")

        try:
            with log_service.step("update_product_prices"):
                with OmnitronIntegration(
                    content_type=ContentType.product_price.value
                ) as omnitron_integration:
                    with log_service.step("get_updated_prices"):
                        product_prices = omnitron_integration.do_action(
                            key="get_updated_prices"
                        )

                    first_product_price_count = len(product_prices)

                    if add_product_objects:
                        with log_service.step("get_product_objects"):
                            product_prices = (
                                product_prices
                                and omnitron_integration.do_action(
                                    key="get_product_objects", objects=product_prices
                                )
                            )

                    if add_stock:
                        with log_service.step("get_stocks_from_product_prices"):
                            product_prices = (
                                product_prices
                                and omnitron_integration.do_action(
                                    key="get_stocks_from_product_prices",
                                    objects=product_prices,
                                    stock_list=omnitron_integration.catalog.stock_list,
                                )
                            )

                    if not product_prices:
                        if first_product_price_count:
                            omnitron_integration.batch_request.objects = None
                            with log_service.step("batch_to_fail"):
                                self.batch_service(
                                    omnitron_integration.channel_id
                                ).to_fail(omnitron_integration.batch_request)
                        return

                    product_prices: List[ProductPrice]

                    with log_service.step("send_updated_prices"):
                        response_data, reports, data = ChannelIntegration().do_action(
                            key="send_updated_prices",
                            objects=product_prices,
                            batch_request=omnitron_integration.batch_request,
                            is_sync=is_sync,
                        )

                    # tips
                    response_data: List[BatchRequestResponseDto]
                    reports: List[ErrorReportDto]
                    data: List[ProductPrice]

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
                        with log_service.step("process_price_batch_requests"):
                            omnitron_integration.do_action(
                                key="process_price_batch_requests",
                                objects=response_data,
                            )
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    def insert_product_prices(
        self,
        is_sync=True,
        is_success_log=True,
        add_product_objects=False,
        add_stock=False,
    ):
        log_service = LogService()
        log_service.create_flow(name="Insert Product Prices")

        try:
            with log_service.step("insert_product_prices"):
                with OmnitronIntegration(
                    content_type=ContentType.product_price.value
                ) as omnitron_integration:
                    with log_service.step("get_inserted_prices"):
                        product_prices = omnitron_integration.do_action(
                            key="get_inserted_prices"
                        )

                    first_product_price_count = len(product_prices)

                    if add_product_objects:
                        with log_service.step("get_product_objects"):
                            product_prices = (
                                product_prices
                                and omnitron_integration.do_action(
                                    key="get_product_objects", objects=product_prices
                                )
                            )

                    if add_stock:
                        with log_service.step("get_stocks_from_product_prices"):
                            product_prices = (
                                product_prices
                                and omnitron_integration.do_action(
                                    key="get_stocks_from_product_prices",
                                    objects=product_prices,
                                    stock_list=omnitron_integration.catalog.stock_list,
                                )
                            )

                    if not product_prices:
                        if first_product_price_count:
                            omnitron_integration.batch_request.objects = None
                            with log_service.step("batch_to_fail"):
                                self.batch_service(
                                    omnitron_integration.channel_id
                                ).to_fail(omnitron_integration.batch_request)
                        return

                    product_prices: List[ProductPrice]

                    with log_service.step("send_inserted_prices"):
                        response_data, reports, data = ChannelIntegration().do_action(
                            key="send_inserted_prices",
                            objects=product_prices,
                            batch_request=omnitron_integration.batch_request,
                            is_sync=is_sync,
                        )

                    # tips
                    response_data: List[BatchRequestResponseDto]
                    reports: List[ErrorReportDto]
                    data: List[ProductPrice]

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
                        with log_service.step("process_price_batch_requests"):
                            omnitron_integration.do_action(
                                key="process_price_batch_requests",
                                objects=response_data,
                            )
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    def insert_product_prices_from_extra_price_list(
        self,
        is_sync=True,
        is_success_log=True,
        add_stock=False,
        add_product_objects=False,
    ):
        log_service = LogService()
        log_service.create_flow(name="Insert Product Prices from Extra Price List")

        try:
            with log_service.step("insert_product_prices_from_extra_price_list"):
                with log_service.step("get_currency_mappings"):
                    currency_mappings = self.get_currency_mappings()
                
                for price_list_id, country_code in currency_mappings.items():
                    with OmnitronIntegration(
                        content_type=ContentType.product_price.value
                    ) as omnitron_integration:
                        with log_service.step("get_inserted_prices_from_extra_price_list"):
                            product_prices = omnitron_integration.do_action(
                                key="get_inserted_prices_from_extra_price_list",
                                objects=price_list_id,
                            )
                        first_product_price_count = len(product_prices)

                        if add_product_objects:
                            with log_service.step("get_product_objects"):
                                product_prices = product_prices and omnitron_integration.do_action(
                                    key="get_product_objects", objects=product_prices
                                )

                        if add_stock:
                            with log_service.step("get_stocks_from_product_prices"):
                                product_prices = product_prices and omnitron_integration.do_action(
                                    key="get_stocks_from_product_prices",
                                    objects=product_prices,
                                    stock_list=omnitron_integration.catalog.stock_list,
                                )

                        product_prices: List[ProductPrice]
                        if product_prices:
                            with log_service.step("send_inserted_prices"):
                                response_data, reports, data = ChannelIntegration().do_action(
                                    key="send_inserted_prices",
                                    objects=(product_prices, country_code),
                                    batch_request=omnitron_integration.batch_request,
                                    is_sync=is_sync,
                                )

                            # tips
                            response_data: List[BatchRequestResponseDto]
                            reports: List[ErrorReportDto]
                            data: List[ProductPrice]

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
                                with log_service.step("process_price_batch_requests"):
                                    omnitron_integration.do_action(
                                        key="process_price_batch_requests", objects=response_data
                                    )
                        else:
                            if first_product_price_count:
                                omnitron_integration.batch_request.objects = None
                                with log_service.step("batch_to_fail"):
                                    self.batch_service(omnitron_integration.channel_id).to_fail(
                                        omnitron_integration.batch_request
                                    )
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    def update_product_prices_from_extra_price_list(
        self,
        is_sync=True,
        is_success_log=True,
        add_stock=False,
        add_product_objects=False,
    ):
        log_service = LogService()
        log_service.create_flow(name="Update Product Prices from Extra Price List")

        try:
            with log_service.step("get_currency_mappings"):
                currency_mappings = self.get_currency_mappings()

            for price_list_id, country_code in currency_mappings.items():
                with OmnitronIntegration(
                    content_type=ContentType.product_price.value
                ) as omnitron_integration:
                    with log_service.step("get_updated_prices_from_extra_price_list"):
                        product_prices = omnitron_integration.do_action(
                            key="get_updated_prices_from_extra_price_list",
                            objects=price_list_id,
                        )
                    first_product_price_count = len(product_prices)
                    if add_product_objects:
                        with log_service.step("get_product_objects"):
                            product_prices = product_prices and omnitron_integration.do_action(
                                key="get_product_objects", objects=product_prices
                            )

                    if add_stock:
                        with log_service.step("get_stocks_from_product_prices"):
                            product_prices = product_prices and omnitron_integration.do_action(
                                key="get_stocks_from_product_prices",
                                objects=product_prices,
                                stock_list=omnitron_integration.catalog.stock_list,
                            )

                    product_prices: List[ProductPrice]
                    if product_prices:
                        with log_service.step("send_updated_prices"):
                            response_data, reports, data = ChannelIntegration().do_action(
                                key="send_updated_prices",
                                objects=(product_prices, country_code),
                                batch_request=omnitron_integration.batch_request,
                                is_sync=is_sync,
                            )

                        # tips
                        response_data: List[BatchRequestResponseDto]
                        reports: List[ErrorReportDto]
                        data: List[ProductPrice]

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
                            with log_service.step("process_price_batch_requests"):
                                omnitron_integration.do_action(
                                    key="process_price_batch_requests", objects=response_data
                                )
                    else:
                        if first_product_price_count:
                            omnitron_integration.batch_request.objects = None
                            with log_service.step("batch_to_fail"):
                                self.batch_service(omnitron_integration.channel_id).to_fail(
                                    omnitron_integration.batch_request
                                )
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    def get_price_batch_requests(self, is_success_log=True):
        log_service = LogService()
        log_service.create_flow(name="Get Price Batch Requests")

        try:
            with OmnitronIntegration(create_batch=False) as omnitron_integration:
                with log_service.step("get_batch_requests"):
                    batch_request_data = omnitron_integration.do_action(
                        "get_batch_requests",
                        params={
                            "status": ["sent_to_remote", "ongoing"],
                            "content_type": ContentType.product_price.value,
                        },
                    )
                # tips
                batch_request_data: List[BatchRequest]

                for batch_request in batch_request_data:
                    with log_service.step("check_prices"):
                        response_data, reports, data = ChannelIntegration().do_action(
                            key="check_prices",
                            objects=batch_request,
                            batch_request=batch_request,
                        )

                    # tips
                    response_data: List[BatchRequestResponseDto]
                    reports: List[ErrorReportDto]
                    data: BatchRequest

                    if reports and (is_success_log or not reports[0].is_ok):
                        for report in reports:
                            with log_service.step("create_error_report"):
                                omnitron_integration.do_action(
                                    key="create_error_report", objects=report
                                )

                    if response_data:
                        omnitron_integration.batch_request = batch_request
                        with log_service.step("process_price_batch_requests"):
                            omnitron_integration.do_action(
                                key="process_price_batch_requests", objects=response_data
                            )
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    def get_currency_mappings(self):
        """
        Process is like below:
         We get key value list of the currency mappings, filter Omnitron
         with key field
        {
            "1": "ae",
            "2": "us"
        }
        :return:
        """
        with OmnitronIntegration(create_batch=False) as integration:
            currency_mappings = integration.channel.conf.get("CURRENCY_MAPPINGS", {})
            price_lists = integration.catalog.extra_price_lists
            if integration.catalog.price_list:
                price_lists.append(integration.catalog.price_list)
            filtered_currency_mappings = {
                price_list: currency_mappings[price_list]
                for price_list in map(str, price_lists)
                if price_list in currency_mappings
            }
        return filtered_currency_mappings
