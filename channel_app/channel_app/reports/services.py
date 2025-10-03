from decimal import Decimal
from typing import List
from channel_app.core.settings import OmnitronIntegration
from channel_app.logs.services import LogService
from channel_app.omnitron.integration import OmnitronIntegration as IOmnitronIntegration
from channel_app.omnitron.constants import ContentType
from omnisdk.omnitron.models import Product


class ReportService:
    @staticmethod
    def get_not_for_sale_products(limit: int = 10) -> List[Product]:
        """
        Get not for sale products from Omnitron API.
        """

        log_service = LogService()
        log_service.create_flow(name="Get Not For Sale Products")

        try:
            with OmnitronIntegration(
                content_type=ContentType.product.value,
            ) as omnitron_integration:
                omnitron_integration: IOmnitronIntegration

                with log_service.step("get_not_for_sale_products"):
                    products: List[Product] = omnitron_integration.do_action(
                        key="get_inserted_products",
                        params={
                            "catalogitem__isnull": True,
                        },
                        objects={
                            "limit": limit,
                        },
                    )

                return products
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    @staticmethod
    def get_price_differences_from_products(marketplace_products: List[Product]):
        """
        Get price differences from products.
        :param marketplace_products: List of products from marketplace
        :return: List of products with price differences

        marketplace_products: List[Product] = [
            Product(
                pk=1,
                price=100.0,
                sku="test-sku-1",
                ...
            ),
            Product(
                pk=3,
                price=200.0,
                sku="test-sku-2",
                ...
            ),
        ]
        """

        log_service = LogService()
        log_service.create_flow(name="Get Price Differences")

        try:
            with OmnitronIntegration(
                content_type=ContentType.product_price.value,
            ) as omnitron_integration:
                omnitron_integration: IOmnitronIntegration

                with log_service.step("get_product_prices"):
                    omnitron_products = omnitron_integration.do_action(
                        key="get_product_prices",
                        objects=marketplace_products,
                    )

                with log_service.step("get_price_differences"):
                    differences = []
                    for omnitron_product in omnitron_products:
                        if omnitron_product.productprice is None:
                            continue

                        if omnitron_product.productprice.price is None:
                            continue

                        for marketplace_product in marketplace_products:
                            if omnitron_product.sku == marketplace_product.sku:
                                if Decimal(
                                    omnitron_product.productprice.price
                                ) != Decimal(marketplace_product.price):
                                    differences.append(
                                        {
                                            "product_pk": omnitron_product.pk,
                                            "product_sku": omnitron_product.sku,
                                            "price_difference": abs(
                                                Decimal(
                                                    omnitron_product.productprice.price
                                                )
                                                - Decimal(marketplace_product.price)
                                            ),
                                            "updated_at": omnitron_product.productprice.modified_date,
                                        }
                                    )

                    return differences
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()

    @staticmethod
    def get_stock_differences_from_products(marketplace_products: List[Product]):
        """
        Get stock differences from products.
        :param marketplace_products: List of products from marketplace
        :return: List of products with stock differences

        marketplace_products: List[Product] = [
            Product(
                pk=1,
                stock=100,
                sku="test-sku-1",
                ...
            ),
            Product(
                pk=3,
                stock=200,
                sku="test-sku-2",
                ...
            ),
        ]
        """
        log_service = LogService()
        log_service.create_flow(name="Get Stock Differences")

        try:
            with OmnitronIntegration(
                content_type=ContentType.product_stock.value,
            ) as omnitron_integration:
                omnitron_integration: IOmnitronIntegration

                with log_service.step("get_product_stocks"):
                    omnitron_products = omnitron_integration.do_action(
                        key="get_product_stocks",
                        objects=marketplace_products,
                    )

                with log_service.step("get_stock_differences"):
                    differences = []
                    for omnitron_product in omnitron_products:
                        if omnitron_product.productstock is None:
                            continue

                        if omnitron_product.productstock.stock is None:
                            continue

                        for marketplace_product in marketplace_products:
                            if omnitron_product.sku == marketplace_product.sku:
                                if int(omnitron_product.productstock.stock) != int(
                                    marketplace_product.stock
                                ):
                                    differences.append(
                                        {
                                            "product_pk": omnitron_product.pk,
                                            "product_sku": omnitron_product.sku,
                                            "stock_difference": abs(
                                                int(omnitron_product.productstock.stock)
                                                - int(marketplace_product.stock)
                                            ),
                                            "updated_at": omnitron_product.productstock.modified_date,
                                        }
                                    )
                    return differences
        except Exception as fatal:
            log_service.add_exception(fatal)
            raise
        finally:
            log_service.save()
