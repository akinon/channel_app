from typing import List

from channel_app.core import settings
from channel_app.core.data import CategoryTreeDto, ErrorReportDto, AttributeDto
from channel_app.core.settings import OmnitronIntegration, ChannelIntegration
from channel_app.omnitron.constants import ContentType


class SetupService(object):
    def create_or_update_category_tree_and_nodes(self, is_success_log=False):
        with OmnitronIntegration(
                content_type=ContentType.category_tree.value) as omnitron_integration:
            channel_integration = ChannelIntegration()
            category_tree, report, _ = channel_integration.do_action(
                key='get_category_tree_and_nodes',
                batch_request=omnitron_integration.batch_request)

            category_tree: CategoryTreeDto
            report: ErrorReportDto

            if report and (is_success_log or not report.is_ok):
                omnitron_integration.do_action(
                    key='create_error_report',
                    objects=report)

            omnitron_integration.do_action(
                key='create_or_update_category_tree_and_nodes',
                objects=category_tree)

    def create_or_update_category_attributes(self, is_success_log=False):
        with OmnitronIntegration(
                content_type=ContentType.attribute.value) as omnitron_integration:
            channel_integration = ChannelIntegration()
            category_integration_actions = omnitron_integration.do_action(
                key='get_category_ids')

            for category_ia in category_integration_actions:
                if not category_ia.remote_id:
                    continue

                category, report, data = channel_integration.do_action(
                    key='get_category_attributes',
                    objects=category_ia,
                    batch_request=omnitron_integration.batch_request
                )
                if report and (is_success_log or not report.is_ok):
                    omnitron_integration.do_action(
                        key='create_error_report',
                        objects=report)

                category = category if category.attributes else None
                omnitron_integration.do_action(
                    key='create_or_update_category_attributes',
                    objects=(category_ia, category))

    def create_or_update_attributes(self, is_success_log=False):
        with OmnitronIntegration(
                content_type=ContentType.attribute.value) as omnitron_integration:
            channel_integration = ChannelIntegration()
            attributes, report, data = channel_integration.do_action(
                key='get_attributes',
                batch_request=omnitron_integration.batch_request
            )

            attributes: List[AttributeDto]
            reports: ErrorReportDto

            if report and (is_success_log or not report.is_ok):
                omnitron_integration.do_action(
                    key='create_error_report',
                    objects=report)

            for attribute in attributes:
                attr = omnitron_integration.do_action(
                    key="create_or_update_channel_attribute",
                    objects={"name": attribute.name,
                             "remote_id": attribute.remote_id},
                )[0]

                omnitron_integration.do_action(
                    key="get_or_create_channel_attribute_schema",
                    objects={"name": f"{settings.OMNITRON_CHANNEL_ID} {attribute.name} Schema"},
                )
                for attr_value in attribute.values:
                    omnitron_integration.do_action(
                        key="create_or_update_channel_attribute_value",
                        objects={
                            "attribute": attr.pk,
                            "label": attr_value.name,
                            "value": attr_value.remote_id,
                            "remote_id": attr_value.remote_id})

    def update_channel_conf_schema(self):
        with OmnitronIntegration(
                content_type=ContentType.channel.value) as omnitron_integration:
            channel_integration = ChannelIntegration()
            schema, _, _ = channel_integration.do_action(
                key='get_channel_conf_schema',
                batch_request=omnitron_integration.batch_request)

            omnitron_integration.do_action(key="update_channel_conf_schema",
                                           objects=schema)
