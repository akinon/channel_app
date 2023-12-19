from collections import defaultdict
from typing import List

from omnisdk.omnitron.endpoints import ChannelIntegrationActionEndpoint, \
    ChannelProductEndpoint, ChannelProductPriceEndpoint, \
    ChannelProductStockEndpoint
from omnisdk.omnitron.models import IntegrationAction

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.utilities import split_list


class CreateIntegrationActions(OmnitronCommandInterface):
    endpoint = ChannelIntegrationActionEndpoint

    def get_data(self) -> list:
        obj_list = self.objects
        items = []
        for obj in obj_list:
            data = {
                "content_type": obj.content_type,
                "channel_id": self.integration.channel_id,
                "object_id": obj.pk,
                "remote_id": obj.remote_id,
                "version_date": obj.modified_date,
                "state": {}
            }
            items.append(data)
        return items

    def send(self, validated_data) -> object:
        integration_actions = []
        for item in validated_data:
            integration_action = self.endpoint(
                channel_id=self.integration.channel_id).create(item=item)

            integration_actions.append(integration_action)
        return integration_actions


class UpdateIntegrationActions(CreateIntegrationActions):
    endpoint = ChannelIntegrationActionEndpoint

    def get_data(self) -> list:
        return self.objects

    def send(self, validated_data) -> object:
        integration_actions = []
        for item in validated_data:
            item.content_type_id = item.content_type['id']
            delattr(item, "content_type")

            integration_action = self.endpoint(
                channel_id=self.integration.channel_id
            ).update(id=item.pk, item=item)

            integration_actions.append(integration_action)
        return integration_actions


class GetIntegrationActionsWithObjectId(OmnitronCommandInterface):
    endpoint = ChannelIntegrationActionEndpoint
    id_type = "object_id__in"
    CHUNK_SIZE = 50

    def get_ia_dict(self, integration_action):
        return {i.object_id: i for i in integration_action}

    def get_data(self) -> List:
        integration_action_list = []
        group_by_content_type = self.get_grup_by_content_type_pk_list()

        for ct, pk_list in group_by_content_type.items():
            for chunk_pk_list in split_list(pk_list, self.CHUNK_SIZE):
                chunk_ia = self.endpoint(
                    channel_id=self.integration.channel_id
                ).list(params={
                    "limit": len(chunk_pk_list),
                    "channel_id": self.integration.channel_id,
                    "content_type_name": ct,
                    self.id_type: ",".join([str(pk) for pk in chunk_pk_list])
                })
                integration_action_list.extend(chunk_ia)

        ia_dict = self.get_ia_dict(integration_action_list)
        self.update_objects(ia_dict)
        return self.objects

    def update_objects(self, ia_dict):
        for obj in self.objects:
            obj.integration_action = ia_dict[obj.pk]

    def get_grup_by_content_type_pk_list(self):
        group_by_content_type = defaultdict(list)
        for obj in self.objects:
            group_by_content_type[obj.content_type].append(obj.pk)
        return group_by_content_type


class GetIntegrationActionsWithRemoteId(GetIntegrationActionsWithObjectId):
    endpoint = ChannelIntegrationActionEndpoint
    id_type = "remote_id__in"

    def get_grup_by_content_type_pk_list(self):
        group_by_content_type = defaultdict(list)
        for obj in self.objects:
            group_by_content_type[obj.content_type].append(obj.remote_id)
        return group_by_content_type

    def get_ia_dict(self, ia):
        return {i.remote_id: i for i in ia}

    def update_objects(self, ia_dict):
        for obj in self.objects:
            obj.integration_action = ia_dict[obj.remote_id]


class GetIntegrationActions(OmnitronCommandInterface):
    endpoint = ChannelIntegrationActionEndpoint
    CHUNK_SIZE = 10

    def get_data(self) -> dict:
        if "limit" not in self.objects:
            self.objects.update({"limit": self.CHUNK_SIZE})
        return self.objects

    def run(self) -> List[IntegrationAction]:
        integration_action_endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        self.objects.update({
            "channel_id": self.integration.channel_id,
            "sort": "id"
        })
        integration_action_list = integration_action_endpoint.list(
            params=self.objects)
        for batch in integration_action_endpoint.iterator:
            if not batch:
                break
            integration_action_list.extend(batch)
        return integration_action_list


class GetObjectsFromIntegrationAction(OmnitronCommandInterface):
    endpoint = {
        "product": ChannelProductEndpoint,
        "productprice": ChannelProductPriceEndpoint,
        "productstock": ChannelProductStockEndpoint
    }
    CHUNK_SIZE = 100

    def get_data(self) -> List[IntegrationAction]:
        """

        :return: Added content type object in integration action objects
            Example: if content type product, -> integration_action.product
                     if content type productprice, -> integration_action.productprice
        """
        integration_actions = self.objects
        group = self.group_by_content_type(integration_actions)
        grouped_integration_actions = self.get_content_objects(group)
        return self.extract_group(grouped_integration_actions)

    def group_by_content_type(self, integration_actions):
        """

        :param integration_actions:
        :return:
        {
        "product":[integration1,integration2,...],
        "productprice":[integration3,integration4,...]
        }
        """
        group = defaultdict(list)
        for integration_action in integration_actions:
            model = integration_action.content_type.get("model")
            group[model].append(integration_action)
        return group

    def get_content_objects(self, grouped_integration_actions: dict):
        for content_type, integration_actions in grouped_integration_actions.items():
            endpoint = self.endpoint.get(content_type)
            if endpoint:
                id_list = [str(ia.object_id) for ia in integration_actions]
                end_point = endpoint(channel_id=self.integration.channel_id)
                objects_list = []
                for chunk_id_list in split_list(id_list, self.CHUNK_SIZE):
                    objects = end_point.list(
                        params={"pk__in": ",".join(chunk_id_list),
                                "limit": len(chunk_id_list)})
                    objects_list.extend(objects)
                objects_dict = {s.pk: s for s in objects_list}
                for integration_action in integration_actions:
                    setattr(integration_action, content_type,
                            objects_dict.get(integration_action.object_id))

        return grouped_integration_actions

    def extract_group(self, group: dict):
        object_list = []
        for key, value_list in group.items():
            object_list.extend(value_list)
        return object_list
