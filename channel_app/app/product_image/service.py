from typing import List

from omnisdk.omnitron.models import BatchRequest, ProductImage

from channel_app.core import settings
from channel_app.core.data import BatchRequestResponseDto, ErrorReportDto
from channel_app.core.settings import OmnitronIntegration, ChannelIntegration
from channel_app.omnitron.batch_request import ClientBatchRequest
from channel_app.omnitron.constants import ContentType


class ImageService(object):
    batch_service = ClientBatchRequest

    def update_product_images(self, is_sync=True, is_success_log=True,
                              add_product_objects=False):
        with OmnitronIntegration(
                content_type=ContentType.product_image.value) as omnitron_integration:
            product_images = omnitron_integration.do_action(
                key='get_updated_images')
            first_product_image_count = len(product_images)
            if add_product_objects:
                product_images = product_images and omnitron_integration.do_action(
                    key='get_product_objects', objects=product_images)

            if not product_images:
                if first_product_image_count:
                    omnitron_integration.batch_request.objects = None
                    self.batch_service(omnitron_integration.channel_id).to_fail(
                        omnitron_integration.batch_request
                    )
                return

            product_images: List[ProductImage]

            response_data, reports, data = ChannelIntegration().do_action(
                key='send_updated_images',
                objects=product_images,
                batch_request=omnitron_integration.batch_request,
                is_sync=is_sync)

            # tips
            response_data: List[BatchRequestResponseDto]
            reports: List[ErrorReportDto]
            data: List[ProductImage]

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
                    key='process_image_batch_requests',
                    objects=response_data)

    def insert_product_images(self, is_sync=True, is_success_log=True,
                              add_product_objects=False):
        with OmnitronIntegration(
                content_type=ContentType.product_image.value) as omnitron_integration:
            product_images = omnitron_integration.do_action(
                key='get_inserted_images')
            first_product_image_count = len(product_images)

            if add_product_objects:
                product_images = product_images and omnitron_integration.do_action(
                    key='get_product_objects', objects=product_images)

            if not product_images:
                if first_product_image_count:
                    omnitron_integration.batch_request.objects = None
                    self.batch_service(omnitron_integration.channel_id).to_fail(
                        omnitron_integration.batch_request
                    )
                return

            product_images: List[ProductImage]

            response_data, reports, data = ChannelIntegration().do_action(
                key='send_inserted_images',
                objects=product_images,
                batch_request=omnitron_integration.batch_request,
                is_sync=is_sync)

            # tips
            response_data: List[BatchRequestResponseDto]
            reports: List[ErrorReportDto]
            data: List[ProductImage]

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
                    key='process_image_batch_requests',
                    objects=response_data)

    def get_image_batch_requests(self, is_success_log=True):
        with OmnitronIntegration(create_batch=False) as omnitron_integration:
            batch_request_data = omnitron_integration.do_action(
                'get_batch_requests',
                params={
                    "status": ["sent_to_remote", "ongoing"],
                    "content_type": ContentType.product_image.value})
            # tips
            batch_request_data: List[BatchRequest]

            for batch_request in batch_request_data:
                response_data, reports, data = ChannelIntegration().do_action(
                    key='check_images',
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
                        key='process_image_batch_requests',
                        objects=response_data)
