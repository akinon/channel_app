from typing import List

from omnisdk.omnitron.models import ProductStock, BatchRequest

from channel_app.core import settings
from channel_app.core.data import BatchRequestResponseDto, ErrorReportDto
from channel_app.core.settings import OmnitronIntegration, ChannelIntegration
from channel_app.omnitron.batch_request import ClientBatchRequest
from channel_app.omnitron.constants import ContentType


class StockService(object):
    batch_service = ClientBatchRequest

    def update_product_stocks(self, is_sync=True, is_success_log=True,
                              add_product_objects=False, add_price=False):
        with OmnitronIntegration(
                content_type=ContentType.product_stock.value) as omnitron_integration:
            product_stocks = omnitron_integration.do_action(
                key='get_updated_stocks')
            first_product_stock_count = len(product_stocks)
            if add_product_objects:
                product_stocks = product_stocks and omnitron_integration.do_action(
                    key='get_product_objects', objects=product_stocks)

            if add_price:
                product_stocks = product_stocks and omnitron_integration.do_action(
                    key='get_prices_from_product_stocks',
                    objects=product_stocks,
                    stock_list=omnitron_integration.catalog.price_list)

            if not product_stocks:
                # TODO: Move this part under batch service
                if first_product_stock_count:
                    omnitron_integration.batch_request.objects = None
                    self.batch_service(omnitron_integration.channel_id).to_fail(
                        omnitron_integration.batch_request
                    )
                return

            product_stocks: List[ProductStock]
            response_data, reports, data = ChannelIntegration().do_action(
                key='send_updated_stocks',
                objects=product_stocks,
                batch_request=omnitron_integration.batch_request,
                is_sync=is_sync)

            # tips
            response_data: List[BatchRequestResponseDto]
            reports: List[ErrorReportDto]
            data: List[ProductStock]

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
                    key='process_stock_batch_requests',
                    objects=response_data)

    def update_product_stocks_from_extra_stock_list(self, is_sync=True,
                                                    is_success_log=True,
                                                    add_price=False,
                                                    add_product_objects=False):
        warehouse_mappings = self.get_warehouse_mappings()
        for stock_list_id, country_code in warehouse_mappings.items():
            with OmnitronIntegration(
                    content_type=ContentType.product_stock.value) as omnitron_integration:
                product_stocks = omnitron_integration.do_action(
                    key='get_updated_stocks_from_extra_stock_list',
                    objects=stock_list_id)
                first_product_stock_count = len(product_stocks)
                if add_product_objects:
                    product_stocks = product_stocks and omnitron_integration.do_action(
                        key='get_product_objects', objects=product_stocks)

                if add_price:
                    product_stocks = product_stocks and omnitron_integration.do_action(
                        key='get_prices_from_product_stocks',
                        objects=product_stocks,
                        stock_list=omnitron_integration.catalog.price_list)

                if not product_stocks:
                    if first_product_stock_count:
                        omnitron_integration.batch_request.objects = None
                        self.batch_service(omnitron_integration.channel_id).to_fail(
                            omnitron_integration.batch_request
                        )
                    return

                product_stocks: List[ProductStock]
                response_data, reports, data = ChannelIntegration().do_action(
                    key='send_updated_stocks',
                    objects=(product_stocks, country_code),
                    batch_request=omnitron_integration.batch_request,
                    is_sync=is_sync)

                # tips
                response_data: List[BatchRequestResponseDto]
                reports: List[ErrorReportDto]
                data: List[ProductStock]

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
                        key='process_stock_batch_requests',
                        objects=response_data)

    def insert_product_stocks_from_extra_stock_list(self, is_sync=True,
                                                    is_success_log=True,
                                                    add_price=False,
                                                    add_product_objects=False):
        warehouse_mappings = self.get_warehouse_mappings()
        for stock_list_id, country_code in warehouse_mappings.items():
            with OmnitronIntegration(
                    content_type=ContentType.product_stock.value) as omnitron_integration:
                product_stocks = omnitron_integration.do_action(
                    key='get_inserted_stocks_from_extra_stock_list',
                    objects=stock_list_id)
                first_product_stock_count = len(product_stocks)
                if add_product_objects:
                    product_stocks = product_stocks and omnitron_integration.do_action(
                        key='get_product_objects', objects=product_stocks)

                if add_price:
                    product_stocks = product_stocks and omnitron_integration.do_action(
                        key='get_prices_from_product_stocks',
                        objects=product_stocks,
                        stock_list=omnitron_integration.catalog.price_list)

                if not product_stocks:
                    if first_product_stock_count:
                        omnitron_integration.batch_request.objects = None
                        self.batch_service(omnitron_integration.channel_id).to_fail(
                            omnitron_integration.batch_request
                        )
                    return

                product_stocks: List[ProductStock]
                response_data, reports, data = ChannelIntegration().do_action(
                    key='send_inserted_stocks',
                    objects=(product_stocks, country_code),
                    batch_request=omnitron_integration.batch_request,
                    is_sync=is_sync)

                # tips
                response_data: List[BatchRequestResponseDto]
                reports: List[ErrorReportDto]
                data: List[ProductStock]

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
                        key='process_stock_batch_requests',
                        objects=response_data)

    def insert_product_stocks(self, is_sync=True, is_success_log=True,
                              add_product_objects=False, add_price=False):
        with OmnitronIntegration(
                content_type=ContentType.product_stock.value) as omnitron_integration:
            product_stocks = omnitron_integration.do_action(
                key='get_inserted_stocks')
            first_product_stock_count = len(product_stocks)

            if add_product_objects:
                product_stocks = product_stocks and omnitron_integration.do_action(
                    key='get_product_objects', objects=product_stocks)

            if add_price:
                product_stocks = product_stocks and omnitron_integration.do_action(
                    key='get_prices_from_product_stocks',
                    objects=product_stocks,
                    stock_list=omnitron_integration.catalog.price_list)

            if not product_stocks:
                if first_product_stock_count:
                    omnitron_integration.batch_request.objects = None
                    self.batch_service(omnitron_integration.channel_id).to_fail(
                        omnitron_integration.batch_request
                    )
                return

            product_stocks: List[ProductStock]
            response_data, reports, data = ChannelIntegration().do_action(
                key='send_inserted_stocks',
                objects=product_stocks,
                batch_request=omnitron_integration.batch_request,
                is_sync=is_sync)
            # tips
            response_data: List[BatchRequestResponseDto]
            reports: List[ErrorReportDto]
            data: List[ProductStock]

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
                    key='process_stock_batch_requests',
                    objects=response_data)

    def get_stock_batch_requests(self, is_success_log=True):
        with OmnitronIntegration(create_batch=False) as omnitron_integration:
            batch_request_data = omnitron_integration.do_action(
                'get_batch_requests',
                params={
                    "status": ["sent_to_remote", "ongoing"],
                    "content_type": ContentType.product_stock.value})
            # tips
            batch_request_data: List[BatchRequest]

            for batch_request in batch_request_data:
                response_data, reports, data = ChannelIntegration().do_action(
                    key='check_stocks',
                    objects=batch_request,
                    batch_request=batch_request
                )

                # tips
                response_data: List[BatchRequestResponseDto]
                reports: List[ErrorReportDto]
                data: BatchRequest

                if reports and (is_success_log or not reports[0].is_ok):
                    for report in reports:
                        omnitron_integration.do_action(
                            key='create_error_report',
                            objects=report)

                if response_data:
                    omnitron_integration.batch_request = batch_request
                    omnitron_integration.do_action(
                        key='process_stock_batch_requests',
                        objects=response_data)

    def get_warehouse_mappings(self):
        """
        Process is like below:
         We get key value list of the warehouse mapping, filter Omnitron
         with key field
        {
            "1": "ae",
            "2": "us"
        }
        :return:
        """
        with OmnitronIntegration(create_batch=False) as integration:
            warehouse_mapping = integration.channel.conf.get(
                "WAREHOUSE_CODES", {})
            stock_lists = integration.catalog.extra_stock_lists
            if integration.catalog.stock_list:
                stock_lists.append(integration.catalog.stock_list)
            filtered_warehouse_mapping = {
                stock_list: warehouse_mapping[stock_list]
                for stock_list in map(str, stock_lists)
                if stock_list in warehouse_mapping}
        return filtered_warehouse_mapping
