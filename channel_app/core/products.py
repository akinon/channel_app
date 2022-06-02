import functools
from collections import defaultdict


class ProductCommonMixin(object):
    def group_by_product_id(self, products):
        """
       # products were grouped by color which was grouped by color
       :param products: [product1,product2]
       :return: Dict {"base_code-color":[product1,product2]}
       """
        group = defaultdict(list)
        for p in products:
            key = self.get_product_id(p)
            group[key].append(p)
        return group

    def get_product_id(self, obj):
        """
        # Your internal product id to reference for
        # this product.
        :param obj:
        :return: String (required)
        """
        product_id = getattr(obj, "mapped_attributes", {}).get(
            "mapped_attributes", {}).get("product_id", None)
        if product_id:
            return product_id
        return self.get_color(obj)

    @staticmethod
    def get_reduce_data(code, value):
        try:
            data = functools.reduce(
                lambda d, key: d.get(key, None) if isinstance(d,
                                                              dict) else None,
                code.split("__"), value)
            return data
        except TypeError:
            return None

    def get_color(self, obj):
        """
        # Valid color provided by namshi
        :param obj:
        :return:String (required,namshi_lookup)
        """
        color = getattr(obj, "mapped_attributes", {}).get(
            "mapped_attributes", {}).get("color", obj.listing_code)
        color = color and obj.attributes["renk"]
        return color

    def get_barcode(self, obj):
        """
        # The barcode uniquely identifying a
        # certain product line across
        remote_id_attribute = ["attributes","barcode"], ["sku"]
        :param obj:
        :return: String (required)
        """
        remote_id_attribute = self.integration.channel.conf.get("remote_id_attribute")
        if remote_id_attribute:
            return self.get_reduce_data(remote_id_attribute, obj.__dict__)
        return obj.sku
