from typing import List

from omnisdk.omnitron.endpoints import (
    ChannelProductImageEndpoint, ChannelIntegrationActionEndpoint, ChannelBatchRequestEndpoint
)
from omnisdk.omnitron.models import ProductImage

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.data import BatchRequestResponseDto
from channel_app.omnitron.commands.batch_requests import ProcessBatchRequests
from channel_app.omnitron.constants import ContentType, IntegrationActionStatus, FailedReasonType, BatchRequestStatus


class GetUpdatedProductImages(OmnitronCommandInterface):
    path = "updates"
    endpoint = ChannelProductImageEndpoint
    BATCH_SIZE = 100
    content_type = ContentType.product_image.value

    def get_data(self) -> List[ProductImage]:
        images = self.get_product_images()
        images = self.get_integration_actions(images)
        return images

    def get_product_images(self) -> List[ProductImage]:
        images = self.endpoint(
            path=self.path,
            channel_id=self.integration.channel_id
        ).list(
            params={
                "limit": self.BATCH_SIZE
            }
        )
        images = images[:self.BATCH_SIZE]
        objects_data = self.create_batch_objects(data=images,
                                                 content_type=self.content_type)
        self.update_batch_request(objects_data=objects_data)
        return images

    def get_integration_actions(self, images: List[ProductImage]):
        if not images:
            return []

        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id
        )
        image_integration_actions = endpoint.list(
            params={
                "local_batch_id": self.integration.batch_request.local_batch_id,
                "status": IntegrationActionStatus.processing,
                "channel_id": self.integration.channel_id,
                "sort": "id"
            }
        )
        for image_batch in endpoint.iterator:
            image_integration_actions.extend(image_batch)

        image_ia_dict = {ia.object_id: ia for ia in image_integration_actions}

        for image in images:
            image_ia = image_ia_dict[image.pk]
            image.remote_id = image_ia.remote_id

        return images


class GetInsertedProductImages(GetUpdatedProductImages):
    path = "inserts"

    def get_integration_actions(self, images: List[ProductImage]):
        if not images:
            return []
        endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        product_ids = [str(image.product) for image in images]
        product_ias = endpoint.list(
            params={"object_id__in": ",".join(product_ids),
                    "content_type_name": ContentType.product.value,
                    "status": IntegrationActionStatus.success,
                    "channel_id": self.integration.channel_id,
                    "sort": "id"
                    })
        for product_batch in endpoint.iterator:
            product_ias.extend(product_batch)
        product_integrations_by_id = {ia.object_id: ia for ia in product_ias}

        for image in images:
            if image.product in product_integrations_by_id:
                product_ia = product_integrations_by_id[image.product]
                image.remote_id = product_ia.remote_id
            else:
                image.failed_reason_type = FailedReasonType.channel_app.value
                self.failed_object_list.append(
                    (image, ContentType.product_image.value,
                     "Product has not been sent"))
        return images


class ProcessImageBatchRequests(OmnitronCommandInterface, ProcessBatchRequests):
    endpoint = ChannelBatchRequestEndpoint
    content_type = ContentType.product_image.value
    CHUNK_SIZE = 50
    BATCH_SIZE = 100

    def get_data(self):
        return self.objects

    def validated_data(self, data: List[BatchRequestResponseDto]):
        for item in data:
            assert isinstance(item, BatchRequestResponseDto)
        return data

    def send(self, validated_data):
        result = self.process_item(validated_data)
        return result

    @property
    def update_state(self, *args, **kwargs) -> BatchRequestStatus:
        return BatchRequestStatus.done

    def check_run(self, is_ok, formatted_data):
        if not is_ok and self.is_batch_request:
            self.integration.batch_request.objects = None
            self.batch_service(self.integration.channel_id).to_fail(
                self.integration.batch_request)
        return False

    def get_channel_items_by_reference_object_ids(self, channel_response,
                                                  model_items_by_content,
                                                  integration_actions):
        product_ids = [str(item) for item in
                       model_items_by_content["productimage"]]

        model_items_by_content_product = self.get_products(product_ids)

        channel_items_by_product_id = {}
        for product_id, product in model_items_by_content_product.items():
            sku = self.get_barcode(obj=product)
            for channel_item in channel_response:
                # TODO: comment
                if channel_item.sku != sku:
                    continue
                remote_item = channel_item
                channel_items_by_product_id[product_id] = remote_item
                break
        return channel_items_by_product_id
