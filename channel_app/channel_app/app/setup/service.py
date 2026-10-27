from typing import List

from channel_app.core import settings
from channel_app.core.data import (CategoryTreeDto, ErrorReportDto,
                                   OperationalEventDto, AttributeDto)
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
                    key='create_operational_event',
                    objects=OperationalEventDto.from_error_report(report))

            omnitron_integration.do_action(
                key='create_or_update_category_tree_and_nodes',
                objects=category_tree)

    def create_or_update_category_attributes(self, is_success_log=False,
                                              max_workers=8):
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with OmnitronIntegration(
                content_type=ContentType.attribute.value) as omnitron_integration:
            channel_integration = ChannelIntegration()
            _ = channel_integration.channel  # cache channel before threads
            category_integration_actions = omnitron_integration.do_action(
                key='get_category_ids')

            leaf_nodes = omnitron_integration.do_action(
                key='get_leaf_category_node_ids')
            leaf_ids = {n.pk for n in leaf_nodes} if leaf_nodes else set()

            leaf_ias = [
                ia for ia in category_integration_actions
                if ia.remote_id and ia.object_id in leaf_ids
            ]

            def fetch_attributes(category_ia):
                """Thread-safe attribute fetch."""
                category, report, data = channel_integration.do_action(
                    key='get_category_attributes',
                    objects=category_ia,
                    batch_request=omnitron_integration.batch_request)
                return category_ia, category, report

            results = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(fetch_attributes, ia): ia
                    for ia in leaf_ias
                }
                for future in as_completed(futures):
                    results.append(future.result())

            for category_ia, category, report in results:
                if report and (is_success_log or not report.is_ok):
                    omnitron_integration.do_action(
                        key='create_error_report',
                        objects=report)

                category = category if category and category.attributes else None
                omnitron_integration.do_action(
                    key='bulk_create_or_update_category_attributes',
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
                omnitron_integration.do_action(
                    key='create_operational_event',
                    objects=OperationalEventDto.from_error_report(report))

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

    def bulk_create_or_update_attributes(self, is_success_log=False):
        """Bulk endpoint kullanarak tüm attribute'ları tek seferde işler."""
        with OmnitronIntegration(
                content_type=ContentType.attribute.value) as omnitron_integration:
            channel_integration = ChannelIntegration()
            attributes, report, data = channel_integration.do_action(
                key='get_attributes',
                batch_request=omnitron_integration.batch_request
            )

            attributes: List[AttributeDto]

            if report and (is_success_log or not report.is_ok):
                omnitron_integration.do_action(
                    key='create_error_report',
                    objects=report)

            if attributes:
                omnitron_integration.do_action(
                    key='bulk_create_or_update_attributes',
                    objects=attributes)

    def update_channel_conf_schema(self):
        with OmnitronIntegration(
                content_type=ContentType.channel.value) as omnitron_integration:
            channel_integration = ChannelIntegration()
            schema, _, _ = channel_integration.do_action(
                key='get_channel_conf_schema',
                batch_request=omnitron_integration.batch_request)

            omnitron_integration.do_action(key="update_channel_conf_schema",
                                           objects=schema)
