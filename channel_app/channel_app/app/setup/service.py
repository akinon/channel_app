from typing import List

from channel_app.core import settings
from channel_app.core.data import CategoryTreeDto, ErrorReportDto, AttributeDto
from channel_app.core.settings import OmnitronIntegration, ChannelIntegration
from channel_app.logs.services import LogService
from channel_app.omnitron.constants import ContentType


class SetupService(object):
    def create_or_update_category_tree_and_nodes(self, is_success_log=False):
        log_service = LogService()
        log_service.create_flow(name="(Setup) Create or Update Category Tree and Nodes")

        try:
            with OmnitronIntegration(
                content_type=ContentType.category_tree.value) as omnitron_integration:
                channel_integration = ChannelIntegration()
                with log_service.step("get_category_tree_and_nodes"):
                    category_tree, report, _ = channel_integration.do_action(
                        key='get_category_tree_and_nodes',
                        batch_request=omnitron_integration.batch_request)

                category_tree: CategoryTreeDto
                report: ErrorReportDto

                if report and (is_success_log or not report.is_ok):
                    with log_service.step("create_error_report"):
                        omnitron_integration.do_action(
                            key='create_error_report',
                            objects=report)

                with log_service.step("create_or_update_category_tree_and_nodes"):
                    omnitron_integration.do_action(
                        key='create_or_update_category_tree_and_nodes',
                        objects=category_tree)
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    def create_or_update_category_attributes(self, is_success_log=False):
        log_service = LogService()
        log_service.create_flow(name="Create or Update Category Attributes")

        try:
            with OmnitronIntegration(
                content_type=ContentType.attribute.value) as omnitron_integration:
                channel_integration = ChannelIntegration()
                with log_service.step("get_category_ids"):
                    category_integration_actions = omnitron_integration.do_action(
                        key='get_category_ids')

                for category_ia in category_integration_actions:
                    if not category_ia.remote_id:
                        continue
                    
                    with log_service.step("get_category_attributes"):
                        category, report, data = channel_integration.do_action(
                            key='get_category_attributes',
                            objects=category_ia,
                            batch_request=omnitron_integration.batch_request
                        )
                    if report and (is_success_log or not report.is_ok):
                        with log_service.step("create_error_report"):
                            omnitron_integration.do_action(
                                key='create_error_report',
                                objects=report)

                    category = category if category.attributes else None
                    with log_service.step("create_or_update_category_attributes"):
                        omnitron_integration.do_action(
                            key='create_or_update_category_attributes',
                            objects=(category_ia, category))
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    def create_or_update_attributes(self, is_success_log=False):
        log_service = LogService()
        log_service.create_flow(name="Create or Update Attributes")

        try:
            with OmnitronIntegration(
                content_type=ContentType.attribute.value) as omnitron_integration:
                channel_integration = ChannelIntegration()
                with log_service.step("get_attributes"):
                    attributes, report, data = channel_integration.do_action(
                        key='get_attributes',
                        batch_request=omnitron_integration.batch_request
                    )

                attributes: List[AttributeDto]
                reports: ErrorReportDto

                if report and (is_success_log or not report.is_ok):
                    with log_service.step("create_error_report"):
                        omnitron_integration.do_action(
                            key='create_error_report',
                            objects=report)

                for attribute in attributes:
                    with log_service.step("create_or_update_channel_attribute"):
                        attr = omnitron_integration.do_action(
                            key="create_or_update_channel_attribute",
                            objects={"name": attribute.name,
                                    "remote_id": attribute.remote_id},
                        )[0]
                        
                    with log_service.step("get_or_create_channel_attribute_schema"):
                        omnitron_integration.do_action(
                            key="get_or_create_channel_attribute_schema",
                            objects={"name": f"{settings.OMNITRON_CHANNEL_ID} {attribute.name} Schema"},
                        )
                    for attr_value in attribute.values:
                        with log_service.step("create_or_update_channel_attribute_value", metadata={
                            "attribute_name": attr_value.name,
                            "remote_id": attr_value.remote_id
                        }):
                            omnitron_integration.do_action(
                                key="create_or_update_channel_attribute_value",
                                objects={
                                    "attribute": attr.pk,
                                    "label": attr_value.name,
                                    "value": attr_value.remote_id,
                                    "remote_id": attr_value.remote_id})
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    def update_channel_conf_schema(self):
        log_service = LogService()
        log_service.create_flow(name="Update Channel Conf Schema")

        try:
            with OmnitronIntegration(
                content_type=ContentType.channel.value) as omnitron_integration:
                channel_integration = ChannelIntegration()
                with log_service.step("get_channel_conf_schema"):
                    schema, _, _ = channel_integration.do_action(
                        key='get_channel_conf_schema',
                        batch_request=omnitron_integration.batch_request)

                with log_service.step("update_channel_conf_schema"):
                    omnitron_integration.do_action(key="update_channel_conf_schema",
                                                objects=schema)
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()
