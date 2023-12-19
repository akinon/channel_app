import asyncio
import uuid
from functools import lru_cache

import requests
from omnisdk.omnitron.endpoints import ChannelAttributeSetEndpoint, \
    ChannelAttributeEndpoint, \
    ChannelAttributeConfigEndpoint, ChannelAttributeValueEndpoint, \
    ChannelAttributeSetConfigEndpoint, ChannelAttributeValueConfigEndpoint, \
    ChannelAttributeSchemaEndpoint
from omnisdk.omnitron.endpoints import ChannelCategoryTreeEndpoint, \
    ChannelCategoryNodeEndpoint, \
    ContentTypeEndpoint, ChannelIntegrationActionEndpoint, ChannelEndpoint
from omnisdk.omnitron.models import CategoryNode, IntegrationAction, \
    CategoryTree, Channel, \
    ChannelAttributeSetConfig, ChannelAttributeValueConfig, \
    ChannelAttributeSchema
from omnisdk.omnitron.models import ChannelAttributeSet, ChannelAttribute, \
    ChannelAttributeConfig, \
    ChannelAttributeValue
from requests import HTTPError

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.data import CategoryTreeDto
from channel_app.core.utilities import is_updated, split_list
from channel_app.omnitron.constants import ContentType


class CreateOrUpdateCategoryTreeAndNodes(OmnitronCommandInterface):
    """
    Using the channel category tree data (including all nodes)
    Create/Update category tree and nodes on the Omnitron side.
    """
    endpoint = ChannelCategoryTreeEndpoint

    def get_data(self) -> CategoryTreeDto:
        return self.objects

    def send(self, validated_data):
        """
        Iterative tree traversal implementation with stack by processing parents first
        children later.
        :return:
        """
        # TODO what should we do once a leaf node becomes a parent node?
        #  How do we update this node? What happens to the products that are
        #  assigned to this category?

        tree = validated_data
        channel_endpoint = ChannelEndpoint()

        if not self.integration.channel.category_tree:
            ct = CategoryTree()
            ct.name = "Sales Channel Tree {}".format(str(uuid.uuid4()))
            node = self.endpoint(channel_id=self.integration.channel_id).create(
                item=ct)
            channel = Channel(category_tree=node.pk)
            channel_endpoint.update(id=self.integration.channel_id,
                                    item=channel)
            self.integration.channel_object = None
        stack = []
        current = tree.root
        node_endpoint = ChannelCategoryNodeEndpoint(
            channel_id=self.integration.channel_id)
        content_type = \
            ContentTypeEndpoint().list(params={"model": "categorynode"})[0]
        integration_action_endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)
        while True:
            if current:
                integration_action = self.get_integration_action(
                    content_type_model=content_type.model,
                    remote_id=current.remote_id)
                if integration_action:  # update node
                    node_object = CategoryNode()
                    node_object.name = current.name
                    node_endpoint.update(id=integration_action.object_id,
                                         item=node_object)
                    current.omnitron_id = integration_action.object_id
                elif not current.remote_id:
                    # if block to skip node creation for root node
                    pass

                else:  # create node
                    self.create_node(content_type, current,
                                     integration_action_endpoint,
                                     node_endpoint)
                stack.extend(current.children)
                current = None
            elif stack:
                current = stack.pop()
            else:
                break
        return []

    def create_node(self, content_type, current, integration_action_endpoint,
                    node_endpoint) -> (
            CategoryNode, IntegrationAction):

        parent_remote_id = current.parent and current.parent.remote_id

        if parent_remote_id:
            node_object_parent = self.get_integration_action(
                content_type_model=content_type.model,
                remote_id=parent_remote_id)
            node_object_parent_id = node_object_parent.object_id
        else:
            root_node = self.root_node()
            node_object_parent_id = root_node["pk"]

        node_object_name = current.name

        node_object = CategoryNode()
        node_object.node = node_object_parent_id
        node_object.name = node_object_name
        node = None
        try:
            node = node_endpoint.create(item=node_object)
        except requests.HTTPError as e:
            if e.response.status_code // 100 != 4:
                raise e

            parent_node_detailed = self.get_node(node_id=node_object_parent_id,
                                                 is_detailed=True)
            for child_node in parent_node_detailed.children:
                if child_node["name"] == node_object_name:
                    node = self.get_node(node_id=child_node["pk"])
                    break

            if not node:
                raise e

        integration_action = IntegrationAction(
            channel_id=self.integration.channel_id,
            content_type_id=content_type.id,
            version_date=node.modified_date,
            object_id=node.pk,
            remote_id=current.remote_id)

        integration_action = integration_action_endpoint.create(
            item=integration_action)
        current.omnitron_id = node.pk
        return node, integration_action

    def get_integration_action(self, content_type_model, remote_id):
        if not remote_id:
            return None
        integration_action_endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)

        integration_action = integration_action_endpoint.list(params={
            "channel_id": self.integration.channel_id,
            "content_type_name": content_type_model,
            "remote_id__exact": remote_id
        })
        if integration_action:
            return integration_action[0]
        else:
            return None

    def get_node(self, node_id, is_detailed=False) -> CategoryNode:
        path = None
        if is_detailed:
            path = "detailed"
        node_endpoint = ChannelCategoryNodeEndpoint(
            channel_id=self.integration.channel_id,
            path=path)
        detailed_node = node_endpoint.retrieve(id=node_id)
        return detailed_node

    def root_node(self):
        category_tree_endpoint = ChannelCategoryTreeEndpoint(
            channel_id=self.integration.channel_id)
        return category_tree_endpoint.retrieve(
            id=self.integration.channel.category_tree).category_root

    def check_run(self, is_ok, formatted_data):
        return True


class CreateOrUpdateCategoryAttributes(OmnitronCommandInterface):
    """
    Create Attribute related entries on the Omnitron using the
    attribute data created from a CategoryDto object.
    """
    integration_action_endpoint = ChannelIntegrationActionEndpoint

    def get_data(self):
        return self.objects

    def send(self, validated_data):
        integration_action, channel_category = validated_data
        if not channel_category:
            self.update_category_node_version_date(integration_action)
            return [integration_action]
        attribute_set_name = self.get_attribute_set_name(channel_category)
        attribute_set = self.integration.do_action(
            key="create_or_update_channel_attribute_set",
            objects={"name": attribute_set_name,
                     "remote_id": integration_action.remote_id})[0]
        self.integration.do_action(
            key="get_or_create_channel_attribute_set_config",
            objects={"attribute_set": attribute_set.id,
                     "object_id": integration_action.object_id,
                     "content_type": ContentType.category_node.value})

        for channel_attribute in channel_category.attributes:
            attribute = self.integration.do_action(
                key="create_or_update_channel_attribute",
                objects={"name": channel_attribute.name,
                         "remote_id": channel_attribute.remote_id})[0]
            schema = self.integration.do_action(
                key="get_or_create_channel_attribute_schema",
                objects={"name": f"{attribute.name} Schema"}
            )
            self.integration.do_action(
                key="create_or_update_channel_attribute_config",
                objects={"attribute": attribute.pk,
                         "attribute_set": attribute_set.id,
                         "attribute_remote_id": channel_attribute.remote_id,
                         "is_required": channel_attribute.required,
                         "is_custom": channel_attribute.allow_custom_value,
                         "is_variant": channel_attribute.variant,
                         })
            for channel_attribute_value in channel_attribute.values:
                self.create_attribute_value_and_config(
                    attribute=attribute, attribute_set=attribute_set,
                    channel_attribute_value=channel_attribute_value)

        self.update_category_node_version_date(integration_action)
        return [attribute]

    def update_category_node_version_date(self, integration_action):
        category_node_endpoint = ChannelCategoryNodeEndpoint(
            channel_id=self.integration.channel_id)
        category_node = category_node_endpoint.update(
            id=integration_action.object_id,
            item=CategoryNode())
        self.integration_action_endpoint(
            channel_id=self.integration.channel_id).update(
            id=integration_action.pk,
            item=IntegrationAction(version_date=category_node.modified_date))

    def create_attribute_value_and_config(self, attribute, attribute_set,
                                          channel_attribute_value):
        attribute_value = self.integration.do_action(
            key="create_or_update_channel_attribute_value",
            objects={
                "attribute": attribute.pk,
                "label": channel_attribute_value.name,
                "value": channel_attribute_value.remote_id,
                "remote_id": channel_attribute_value.remote_id})[0]
        attribute_value_config = self.integration.do_action(
            key="get_or_create_channel_attribute_value_config",
            objects={
                "attribute_value": attribute_value.pk,
                "attribute_set": attribute_set.id})[0]

    def get_attribute_set_name(self, channel_category):
        # TODO create attribute set name as a breadcrumb
        return channel_category.name


class AsyncCreateOrUpdateCategoryAttributes(CreateOrUpdateCategoryAttributes):
    """
    Async process
    Create Attribute related entries on the Omnitron using the
    attribute data created from a CategoryDto object.
    """

    async def run_async(self):
        integration_action, channel_category = self.get_data()
        attribute_set_name = self.get_attribute_set_name(channel_category)
        attribute_set = self.integration.do_action(
            key="create_or_update_channel_attribute_set",
            objects={"name": attribute_set_name,
                     "remote_id": integration_action.remote_id})
        self.integration.do_action(
            key="get_or_create_channel_attribute_set_config",
            objects={"attribute_set": attribute_set.remote_id,
                     "object_id": integration_action.object_id,
                     "content_type": ContentType.category_node.value})

        for channel_attribute in channel_category.attributes:
            attribute = self.integration.do_action(
                key="create_or_update_channel_attribute",
                objects={"name": channel_attribute.name,
                         "remote_id": channel_attribute.remote_id})
            self.integration.do_action(
                key="create_or_update_channel_attribute_config",
                objects={"attribute": attribute.pk,
                         "attribute_set": attribute_set.remote_id,
                         "attribute_remote_id": channel_attribute.remote_id,
                         "is_required": channel_attribute.required,
                         "is_custom": channel_attribute.allow_custom_value,
                         "is_variant": channel_attribute.variant,
                         })

            await asyncio.gather(
                *[self.get_or_create_attribute_value_and_config(attribute,
                                                                attribute_set,
                                                                channel_attribute_value)
                  for
                  channel_attribute_value in channel_attribute.values])

        category_node_endpoint = ChannelCategoryNodeEndpoint(
            channel_id=self.integration.channel_id)
        category_node = category_node_endpoint.update(
            id=integration_action.object_id,
            item=CategoryNode())
        self.integration_action_endpoint(
            channel_id=self.integration.channel_id).update(
            id=integration_action.pk,
            item=IntegrationAction(version_date=category_node.modified_date))

    async def get_or_create_attribute_value_and_config(self, attribute,
                                                       attribute_set,
                                                       channel_attribute_value):
        attribute_value = self.integration.do_action(
            key="create_or_update_channel_attribute_value",
            objects={
                "attribute": attribute.pk,
                "label": channel_attribute_value.name,
                "value": channel_attribute_value.remote_id,
                "remote_id": channel_attribute_value.remote_id})
        attribute_value_config = self.integration.do_action(
            key="get_or_create_channel_attribute_value_config",
            objects={
                "attribute_value": attribute_value.pk,
                "attribute_set": attribute_set.remote_id})
        await asyncio.sleep(0)


class GetCategoryIds(OmnitronCommandInterface):
    """
    Get Category ids from Omnitron sorted by least recently updated category first
    """
    endpoint = ChannelCategoryNodeEndpoint
    CHUNK_SIZE = 50

    def get_data(self):
        return

    def send(self, validated_data) -> list:
        if not self.integration.channel.category_tree:
            raise Exception("No category tree, no attributes :/")
        integration_endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)

        integration_actions = integration_endpoint.list(params={
            "channel_id": self.integration.channel_id,
            "content_type_name": ContentType.category_node.value,
            "sort": "version_date",
            "limit": 200  # if we want to process oldest five nodes at a time
        })
        return integration_actions


class CreateOrUpdateChannelAttributeSet(OmnitronCommandInterface):
    """
    Create AttributeSet object on Omnitron to store the attributes
    """
    endpoint = ChannelAttributeSetEndpoint

    def get_data(self) -> ChannelAttributeSet:
        name = self.objects["name"]
        remote_id = self.objects["remote_id"]
        channel = self.integration.channel_id
        return ChannelAttributeSet(name=name, remote_id=remote_id,
                                   channel=channel)

    def send(self, validated_data) -> list:
        data = validated_data
        endpoint = self.endpoint(channel_id=self.integration.channel_id)

        attribute_sets = endpoint.list(
            params={"remote_id__exact": data.remote_id,
                    "channel": self.integration.channel_id})
        # TODO add channel filter too on the next version

        if len(attribute_sets) > 0:
            attribute_set = attribute_sets[0]
            if self.is_updated(attribute_set, data):
                self.endpoint(channel_id=self.integration.channel_id).update(
                    id=attribute_set.id, item=data)
            return [attribute_sets[0]]

        attribute_set = self.endpoint(
            channel_id=self.integration.channel_id).create(item=data)
        return [attribute_set]

    def is_updated(self, attribute_set, data):
        if data.channel != attribute_set.channel:
            return True
        if data.name != attribute_set.name:
            return True
        return False


class GetOrCreateChannelAttributeSetConfig(OmnitronCommandInterface):
    """
    Create an AttributeSetConfig entry for AttributeSet denoting which object this set belongs to.
    For example an attribute set usually defines the attributes a category needs. So
    we create an AttributeSetConfig entry with category Omnitron id, CategoryNode content type and
    AttributeSet id.
    """

    endpoint = ChannelAttributeSetConfigEndpoint

    def get_data(self) -> ChannelAttributeSetConfig:
        attribute_set = self.objects["attribute_set"]
        object_id = self.objects["object_id"]
        content_type = self.objects["content_type"]
        if not isinstance(attribute_set, int):
            raise AssertionError
        if not isinstance(object_id, (int, type(None))):
            raise AssertionError
        if not isinstance(content_type, str):
            raise AssertionError
        return ChannelAttributeSetConfig(attribute_set=attribute_set,
                                         object_id=object_id,
                                         content_type=content_type)

    def send(self, validated_data) -> list:
        data = validated_data
        endpoint = self.endpoint(channel_id=self.integration.channel_id)
        attribute_set_configs = endpoint.list(
            params={"attribute_set": data.attribute_set,
                    "object_id": data.object_id,
                    "content_type__model__exact": data.content_type})
        if len(attribute_set_configs) > 0:
            return attribute_set_configs

        attribute_set_config = endpoint.create(item=data)
        return [attribute_set_config]


class CreateOrUpdateChannelAttribute(OmnitronCommandInterface):
    endpoint = ChannelAttributeEndpoint

    # TODO Omnitron does not support 2 different attributes with same name on same channel,
    #  If a marketplace uses more than one same-name attributes for different purposes,
    #  in Omnitron they map to a single attribute. Only one of those attributes will be recognized
    #  and an IntegrationAction entry will be created.

    def get_data(self):
        name = self.objects["name"]
        remote_id = self.objects["remote_id"]
        if not isinstance(name, str):
            raise AssertionError
        if not isinstance(remote_id, (str, int, type(None))):
            raise AssertionError

        return name, remote_id

    def send(self, validated_data) -> list:
        name, remote_id = validated_data

        integration_endpoint = ChannelIntegrationActionEndpoint(
            channel_id=self.integration.channel_id)

        attribute = self.create_or_update_channel_attribute(
            integration_endpoint, name, remote_id)
        return [attribute]

    def create_or_update_channel_attribute(self, integration_endpoint, name,
                                           remote_id):

        integration_action = integration_endpoint.list(params={
            "content_type_name": "marketplaceattribute",
            "channel_id": self.integration.channel_id,
            "remote_id__exact": remote_id
        })
        if integration_action:
            integration_action = integration_action[0]
            attribute = self.endpoint(
                channel_id=self.integration.channel_id).retrieve(
                id=integration_action.object_id)
            if attribute.name != name:
                attribute = self.endpoint(
                    channel_id=self.integration.channel_id).update(
                    id=integration_action.object_id, item=ChannelAttribute(
                        channel=self.integration.channel_id,
                        name=name
                    ))
            return attribute
        else:
            try:
                attribute = self.endpoint(
                    channel_id=self.integration.channel_id).create(
                    item=ChannelAttribute(channel=self.integration.channel_id,
                                          name=name))
            except HTTPError as e:
                if e.response.status_code // 100 != 4:
                    raise e
                params = {
                    "name__exact": name, "channel": self.integration.channel_id
                }
                attributes = self.endpoint(
                    channel_id=self.integration.channel_id).list(params=params)
                if len(attributes) == 0:
                    raise Exception(
                        "Creation returned bad request but nothing exists!")
                return attributes[0]
            content_type = ContentTypeEndpoint().list(
                params={"model": "marketplaceattribute"})[0]
            integration_endpoint.create(item=IntegrationAction(
                channel_id=self.integration.channel_id,
                content_type_id=content_type.id,
                remote_id=remote_id,
                object_id=attribute.pk,
                version_date=attribute.modified_date,
            ))
        return attribute


class GetChannelAttributeSets(OmnitronCommandInterface):
    """
      Get all attribute set  in omnitron
      """

    def get_data(self):
        return

    def send(self, validated_data) -> object:
        endpoint = ChannelAttributeSetEndpoint(
            channel_id=self.integration.channel_id)
        attribute_sets = endpoint.list(
            params={"channel": self.integration.channel_id,
                    "sort": "id"})
        for attribute_set_batch in endpoint.iterator:
            attribute_sets.extend(attribute_set_batch)
        return attribute_sets


class GetChannelAttributeSetConfigs(OmnitronCommandInterface):
    """
    Get all attribute set config in omnitron
    """
    CHUNK_SIZE = 500

    def get_data(self):
        return

    def send(self, validated_data) -> object:
        endpoint = ChannelAttributeSetConfigEndpoint(
            channel_id=self.integration.channel_id)
        attribute_set_configs = endpoint.list(params={
            "content_type__model": ContentType.category_node.value,
            "limit": self.CHUNK_SIZE,
            "sort": "object_id"})
        for attribute_set_config_batch in endpoint.iterator:
            attribute_set_configs.extend(attribute_set_config_batch)
        attribute_set_configs_by_category_node_pk = {}
        for attribute_set_config in attribute_set_configs:
            attribute_set_configs_by_category_node_pk[
                attribute_set_config.object_id] = attribute_set_config
        return [attribute_set_configs_by_category_node_pk]


class CreateOrUpdateChannelAttributeConfig(OmnitronCommandInterface):
    """
    Attach an attribute with an attribute set
    """

    endpoint = ChannelAttributeConfigEndpoint

    def get_data(self) -> dict:
        attribute_set = self.objects["attribute_set"]
        attribute = self.objects["attribute"]
        attribute_remote_id = self.objects.get("attribute_remote_id", None)
        is_required = self.objects.get("is_required", False)
        is_variant = self.objects.get("is_variant", False)
        is_custom = self.objects.get("is_custom", False)
        is_image_attribute = self.objects.get("is_image_attribute", False)
        is_meta = self.objects.get("is_meta", False)

        if not isinstance(attribute_set, int):
            raise AssertionError
        if not isinstance(attribute, int):
            raise AssertionError
        if not isinstance(attribute_remote_id, (str, type(None))):
            raise AssertionError
        if not isinstance(is_required, bool):
            raise AssertionError
        if not isinstance(is_variant, bool):
            raise AssertionError
        if not isinstance(is_custom, bool):
            raise AssertionError
        if not isinstance(is_image_attribute, bool):
            raise AssertionError
        if not isinstance(is_meta, bool):
            raise AssertionError
        return {
            "attribute_set": attribute_set,
            "attribute": attribute,
            "attribute_remote_id": attribute_remote_id,
            "is_required": is_required,
            "is_variant": is_variant,
            "is_custom": is_custom,
            "is_image_attribute": is_image_attribute,
            "is_meta": is_meta,
        }

    def send(self, validated_data) -> ChannelAttributeConfig:
        data = validated_data
        attribute_set = data["attribute_set"]
        attribute = data["attribute"]
        attribute_remote_id = data["attribute_remote_id"]
        is_required = data["is_required"]
        is_variant = data["is_variant"]
        is_custom = data["is_custom"]
        is_image_attribute = data["is_image_attribute"]
        is_meta = data["is_meta"]

        endpoint = self.endpoint(channel_id=self.integration.channel_id)
        try:
            attributeconfig = endpoint.create(
                item=ChannelAttributeConfig(
                    attribute_set=attribute_set,
                    attribute=attribute,
                    attribute_remote_id=attribute_remote_id,
                    is_required=is_required,
                    is_variant=is_variant,
                    is_custom=is_custom,
                    is_image_attribute=is_image_attribute,
                    is_meta=is_meta))
        except HTTPError as e:
            if e.response.status_code // 100 != 4:
                raise e
            attributeconfigs = endpoint.list(
                params={"attribute_set": attribute_set,
                        "attribute": attribute})
            attributeconfig = attributeconfigs[0]
            if is_updated(attributeconfig, data):
                attributeconfig = endpoint.update(
                    id=attributeconfig.pk,
                    item=ChannelAttributeConfig(
                        attribute_set=attribute_set,
                        attribute=attribute,
                        attribute_remote_id=attribute_remote_id,
                        is_required=is_required,
                        is_variant=is_variant,
                        is_custom=is_custom,
                        is_image_attribute=is_image_attribute,
                        is_meta=is_meta))
            return [attributeconfig]
        return [attributeconfig]


class CreateOrUpdateChannelAttributeValue(OmnitronCommandInterface):
    endpoint = ChannelAttributeValueEndpoint

    def get_data(self) -> dict:
        remote_id = self.objects["remote_id"]
        attribute = self.objects["attribute"]
        label = self.objects["label"]
        value = self.objects["value"]
        if not isinstance(remote_id, (str, int)):
            raise AssertionError
        if not isinstance(attribute, int):
            raise AssertionError
        if not isinstance(label, str):
            raise AssertionError
        if not isinstance(value, (str, int)):
            raise AssertionError
        return self.objects

    def send(self, validated_data) -> list:
        # TODO all service calls here can be summarized to a single call to omnitron
        #  which checks IntegrationAction by remote id, if it finds the item, updates the item and
        #  IntegrationAction returns it and halts. If it cannot find the item, it creates the
        #  item, creates its IntegrationAction, returns them and halts.
        data = validated_data
        remote_id = data["remote_id"]
        attribute = data["attribute"]
        label = data["label"]
        value = data["value"]
        channel_id = self.integration.channel_id
        # search in cached attribute values and ia
        attribute_value = self.get_or_create_attribute_value(attribute, label,
                                                             remote_id,
                                                             value, channel_id)
        return [attribute_value]

    @staticmethod
    @lru_cache(maxsize=None)
    def get_or_create_attribute_value(attribute, label, remote_id, value,
                                      channel_id):
        data = {
            "remote_id": remote_id,
            "attribute": attribute,
            "label": label,
            "value": value
        }
        endpoint = ChannelAttributeValueEndpoint(channel_id=channel_id)
        integration_endpoint = ChannelIntegrationActionEndpoint(
            channel_id=channel_id)
        integration_action = integration_endpoint.list(params={
            "content_type_name": "marketplaceattributevalue",
            "channel_id": channel_id,
            "remote_id__exact": remote_id
        })
        attribute_value_item = ChannelAttributeValue(channel=channel_id,
                                                     attribute=attribute,
                                                     label=label,
                                                     value=value, )
        if integration_action:
            integration_action = integration_action[0]
            attribute_value = endpoint.retrieve(
                id=integration_action.object_id)
            if is_updated(attribute_value, data):
                if attribute_value.attribute == data["attribute"]:
                    endpoint.update(id=integration_action.object_id,
                                    item=attribute_value_item)
                else:
                    attribute_value = CreateOrUpdateChannelAttributeValue.create_attribute_value(
                        attribute, attribute_value_item, endpoint, label, value)
        else:
            attribute_value = CreateOrUpdateChannelAttributeValue.create_attribute_value(
                attribute, attribute_value_item, endpoint, label, value)

            content_type = ContentTypeEndpoint().list(params={
                "model": "marketplaceattributevalue"})[0]
            integration_endpoint.create(item=IntegrationAction(
                channel_id=channel_id,
                content_type_id=content_type.id,
                remote_id=remote_id,
                object_id=attribute_value.pk,
                version_date=attribute_value.modified_date,
            ))
        return attribute_value

    @staticmethod
    def create_attribute_value(attribute, attribute_value_item, endpoint, label,
                               value):
        try:
            attribute_value = endpoint.create(item=attribute_value_item)
        except HTTPError:
            attribute_value = endpoint.list(params={"attribute": attribute,
                                                    "label__exact": label,
                                                    "value__exact": value, })[
                0]
        return attribute_value


class GetOrCreateChannelAttributeValueConfig(OmnitronCommandInterface):
    """
    If a subset of attribute values are defined for an attribute set, you need to create
    AttributeValueConfig objects to achieve that setup
    """
    # TODO what happens it a value is no more needed in an attribute set
    #  there is nothing that handles deletes right now

    endpoint = ChannelAttributeValueConfigEndpoint

    def get_data(self) -> dict:
        attribute_set = self.objects["attribute_set"]
        attribute_value = self.objects["attribute_value"]
        if not isinstance(attribute_set, int):
            raise AssertionError
        if not isinstance(attribute_value, int):
            raise AssertionError
        return self.objects

    def send(self, validated_data) -> list:
        data = validated_data
        attribute_set = data["attribute_set"]
        attribute_value = data["attribute_value"]
        channel_id = self.integration.channel_id
        attribute_value_config = self.get_or_create_attribute_value_config(
            attribute_set, attribute_value, channel_id)
        return [attribute_value_config]

    @staticmethod
    @lru_cache(maxsize=None)
    def get_or_create_attribute_value_config(attribute_set, attribute_value,
                                             channel_id):
        endpoint = ChannelAttributeValueConfigEndpoint(channel_id=channel_id)
        attributevalueconfigs = endpoint.list(
            params={"attribute_set": attribute_set,
                    "attribute_value": attribute_value})
        if len(attributevalueconfigs) > 0:
            return attributevalueconfigs[0]
        attribute_value_config = endpoint.create(
            item=ChannelAttributeValueConfig(
                attribute_set=attribute_set,
                attribute_value=attribute_value))
        return attribute_value_config


class GetOrCreateChannelAttributeSchema(OmnitronCommandInterface):
    """
    Schema(Ruleset) objects define how an attribute of a product will be populated. It is
    not feasible to automatically fill the rules. We need to create empty schema objects so that
    Omnitron users can fill the rules
    """

    endpoint = ChannelAttributeSchemaEndpoint

    def get_data(self) -> object:
        return self.objects

    def send(self, validated_data) -> object:
        data = validated_data
        schema = data.get("schema", {})
        channel_id = self.integration.channel_id
        name = f"{str(channel_id)} {data['name']}"
        endpoint = self.endpoint(channel_id=channel_id)
        try:
            attribute_schema = endpoint.create(item=ChannelAttributeSchema(
                name=name, schema=schema, channel=channel_id))
        except HTTPError as e:
            if e.response.status_code // 100 != 4:
                raise e
            attribute_schemas = endpoint.list(params={"name__exact": name,
                                                      "channel": channel_id})
            attribute_schema = attribute_schemas[0]
        return [attribute_schema]


class UpdateChannelConfSchema(OmnitronCommandInterface):
    endpoint = ChannelEndpoint

    def get_data(self) -> dict:
        schema_dict = self.objects
        return schema_dict

    def send(self, validated_data) -> list:
        channel = self.integration.channel
        schema = validated_data
        if isinstance(channel.schema, dict):
            channel.schema.update(schema)
        else:
            channel.schema = schema
        new_channel = Channel(schema=channel.schema)
        channel_response = self.endpoint(
            channel_id=self.integration.channel_id).update(
            id=channel.pk,
            item=new_channel)
        return [channel_response]
