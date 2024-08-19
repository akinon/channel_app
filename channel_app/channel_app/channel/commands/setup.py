from typing import Tuple, Any, List

from omnisdk.omnitron.models import IntegrationAction

from channel_app.core.commands import ChannelCommandInterface
from channel_app.core.data import (CategoryTreeDto, CategoryNodeDto,
                                   CategoryDto,
                                   CategoryAttributeDto,
                                   CategoryAttributeValueDto, ErrorReportDto,
                                   ChannelConfSchemaField, AttributeDto,
                                   AttributeValueDto)
from channel_app.core.utilities import mock_response_decorator
from channel_app.omnitron.constants import ChannelConfSchemaDataTypes


class GetCategoryTreeAndNodes(ChannelCommandInterface):
    """
    Category trees and categories represent an easy way to find, list, filter
    products. Tree representation of the sales channel must be fetched and
    all products we want to sell must be assigned to a category.

    This command fetches all categories belonging to a sales channels and their
    tree structure.

    input olarak do_action'da
        objects -> None tipinde kayıt alır. Yani veri almaz
        batch_request -> BatchRequest tipinde kayıt alır. Ana işleme ait
            BatchRequest kaydı. Rapor üretmek için kullanılır.

    CategoryTreeDto -> Kategori ağacı ve buna bağlı dalları barındıran veri tipi.

    ErrorReportDto -> Rapor için üretilmiş  veri tipi. Hata olmasada uretilebilir.

    """

    def get_data(self):

        data = self.objects
        return data

    def validated_data(self, data) -> object:
        return data

    def transform_data(self, data) -> object:
        return data

    def send_request(self, transformed_data) -> object:
        response = self.__mocked_request(data=transformed_data)
        return response

    def normalize_response(self, data, validated_data, transformed_data,
                           response) -> Tuple[
        CategoryTreeDto, List[ErrorReportDto], Any]:
        """
        Convert channel category tree to the format OmnitronIntegration
        requires
        """
        report = self.create_report(response)
        node_dict = {}

        stack = []
        current = {
            "id": None,
            "name": "root",
            "parentId": None,
            "subCategories": response.json()["categories"]
        }
        # TODO document parent of top level nodes should be None
        # TODO document id and parent_id of root node must be None
        while True:
            if current:
                category_node = CategoryNodeDto(
                    parent=node_dict[current["parentId"]] if current[
                        "parentId"] else None,
                    remote_id=current["id"],
                    children=[],
                    name=current["name"]
                )
                node_dict[current["id"]] = category_node
                for child in current["subCategories"]:
                    stack.append(child)
                current = None
            elif stack:
                current = stack.pop()
            else:
                break
        category_tree = CategoryTreeDto(root=node_dict[None])
        node_dict.pop(None)
        for node_remote_id, node in node_dict.items():
            if node.parent is not None:
                node_dict[node.parent.remote_id].children.append(node)
            else:
                category_tree.root.children.append(node)

        return category_tree, report, data

    @mock_response_decorator
    def __mocked_request(self, data):
        """
        Mock a request and response for the send operation to mimic actual channel data

        """
        return {
            "categories": [
                {
                    "id": 403,
                    "name": "Ayakkabı",
                    "parentId": None,
                    "subCategories": [
                        {
                            "id": 420,
                            "name": "Spor Ayakkabı",
                            "parentId": 403,
                            "subCategories": [
                                {
                                    "id": 421,
                                    "name": "Basketbol Ayakkabısı",
                                    "parentId": 420,
                                    "subCategories": []
                                },
                                {
                                    "id": 422,
                                    "name": "Fitness Ayakkabısı",
                                    "parentId": 420,
                                    "subCategories": []
                                },
                                {
                                    "id": 426,
                                    "name": "Halı Saha Ayakkabısı&Krampon",
                                    "parentId": 420,
                                    "subCategories": []
                                },
                                {
                                    "id": 425,
                                    "name": "Koşu & Antrenman Ayakkabısı",
                                    "parentId": 420,
                                    "subCategories": [
                                        {
                                            "id": 999,
                                            "name": "Test Sub Category",
                                            "parentId": 425,
                                            "subCategories": []
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }


class GetCategoryAttributes(ChannelCommandInterface):
    """
    Along with classification, categories define a set of common attributes which makes
    sense only for that category and not others. To manage this process the attributes
    are fetched from the channel and certain validations are done to ensure product is
    ready to be sold before sending to the channel.

    This command fetches category attributes of a given category id.
    """

    def get_data(self):
        if self.objects:
            assert isinstance(self.objects, IntegrationAction)
        data = self.objects
        return data

    def validated_data(self, data) -> object:
        return data

    def transform_data(self, data) -> object:
        return data

    def send_request(self, transformed_data) -> object:
        response = self.__mocked_request(data=transformed_data)
        return response

    def normalize_response(self, data, validated_data, transformed_data,
                           response) -> Tuple[CategoryDto, ErrorReportDto, Any]:
        """
        Convert channel category tree to the format OmnitronIntegration
        requires
        """
        report = self.create_report(response)
        response = response.json()
        category = CategoryDto(remote_id=response["id"],
                               name=response["name"],
                               attributes=[])

        for channel_attribute in response["categoryAttributes"]:
            attribute = CategoryAttributeDto(
                remote_id=channel_attribute["attribute"]["id"],
                name=channel_attribute["attribute"]["name"],
                allow_custom_value=channel_attribute["allowCustom"],
                required=channel_attribute["required"],
                variant=channel_attribute["varianter"],
                values=[]
            )
            for channel_attribute_value in channel_attribute["attributeValues"]:
                attribute_value = CategoryAttributeValueDto(
                    remote_id=channel_attribute_value["id"],
                    name=channel_attribute_value["name"])
                attribute.values.append(attribute_value)
            category.attributes.append(attribute)
        return category, report, data

    @mock_response_decorator
    def __mocked_request(self, data):
        """
        Mock a request and response for the send operation to mimic actual channel data
        """
        return {
            "id": 123123124214,
            "name": "Sweatshirt",
            "displayName": "Sweatshirt",
            "categoryAttributes": [
                {
                    "allowCustom": False,
                    "attribute": {
                        "id": 2,
                        "name": "Boy / Ölçü"
                    },
                    "attributeValues": [
                        {
                            "id": 10,
                            "name": "Kısa"
                        },
                        {
                            "id": 16,
                            "name": "Uzun"
                        },
                        {
                            "id": 572,
                            "name": "Orta"
                        },
                        {
                            "id": 575,
                            "name": "Battal Boy"
                        }
                    ],
                    "categoryId": 601,
                    "required": False,
                    "varianter": False,
                    "slicer": False
                },
                {
                    "allowCustom": False,
                    "attribute": {
                        "id": 12,
                        "name": "Kol Tipi"
                    },
                    "attributeValues": [
                        {
                            "id": 62,
                            "name": "Askılı"
                        },
                        {
                            "id": 64,
                            "name": "Kısa Kol"
                        },
                        {
                            "id": 65,
                            "name": "Kolsuz"
                        },
                        {
                            "id": 67,
                            "name": "Tek Kol"
                        },
                        {
                            "id": 68,
                            "name": "Uzun"
                        },
                        {
                            "id": 69,
                            "name": "Uzun Kol"
                        },
                        {
                            "id": 622,
                            "name": "Geniş / Yarasa"
                        },
                        {
                            "id": 2841,
                            "name": "Volanlı"
                        },
                        {
                            "id": 2842,
                            "name": "Omzu açık"
                        },
                        {
                            "id": 2857,
                            "name": "Balon"
                        },
                        {
                            "id": 4020,
                            "name": "Ay"
                        },
                        {
                            "id": 7118,
                            "name": "Karpuz Kol"
                        },
                        {
                            "id": 23532,
                            "name": "Reglan Kol"
                        },
                        {
                            "id": 193959,
                            "name": "Mendil"
                        },
                        {
                            "id": 256024,
                            "name": "Yarasa Kol"
                        },
                        {
                            "id": 666277,
                            "name": "Takma Kol"
                        },
                        {
                            "id": 902440,
                            "name": "Ay Kol"
                        },
                        {
                            "id": 902442,
                            "name": "Standart Kol"
                        },
                        {
                            "id": 902443,
                            "name": "Düşük Kol"
                        },
                        {
                            "id": 902444,
                            "name": "Mendil Kol"
                        },
                        {
                            "id": 902445,
                            "name": "Balon Kol"
                        },
                        {
                            "id": 997508,
                            "name": "Büzgülü/Fırfırlı Kol"
                        },
                        {
                            "id": 997516,
                            "name": "İspanyol Kol"
                        }
                    ],
                    "categoryId": 601,
                    "required": False,
                    "varianter": False,
                    "slicer": False
                },
                {
                    "allowCustom": False,
                    "attribute": {
                        "id": 14,
                        "name": "Materyal"
                    },
                    "attributeValues": [
                        {
                            "id": 77,
                            "name": "Akrilik"
                        },
                        {
                            "id": 79,
                            "name": "Bambu"
                        },
                        {
                            "id": 91,
                            "name": "Kumaş"
                        },
                        {
                            "id": 99,
                            "name": "Polyester"
                        },
                        {
                            "id": 105,
                            "name": "Suni Deri"
                        },
                        {
                            "id": 195,
                            "name": "Kadife"
                        },
                        {
                            "id": 627,
                            "name": "Polar"
                        },
                        {
                            "id": 645,
                            "name": "Dalgıç Kumaş"
                        },
                        {
                            "id": 646,
                            "name": "Şerpa"
                        },
                        {
                            "id": 654,
                            "name": "Poliamid"
                        },
                        {
                            "id": 661,
                            "name": "PVC"
                        },
                        {
                            "id": 674,
                            "name": "Modal"
                        },
                        {
                            "id": 675,
                            "name": "Saten"
                        },
                        {
                            "id": 678,
                            "name": "Likra"
                        },
                        {
                            "id": 679,
                            "name": "Zincir"
                        },
                        {
                            "id": 681,
                            "name": "Pamuklu"
                        },
                        {
                            "id": 690,
                            "name": "Viskon"
                        },
                        {
                            "id": 710,
                            "name": "Keten"
                        },
                        {
                            "id": 713,
                            "name": "Elyaf"
                        },
                        {
                            "id": 727,
                            "name": "Pamuk-Polyester"
                        },
                        {
                            "id": 7119,
                            "name": "Lyocell"
                        },
                        {
                            "id": 9328,
                            "name": "Naylon"
                        },
                        {
                            "id": 9329,
                            "name": "Liyosel"
                        },
                        {
                            "id": 9330,
                            "name": "Poliüretan"
                        },
                        {
                            "id": 9331,
                            "name": "Asetat"
                        },
                        {
                            "id": 12277,
                            "name": "Elastan"
                        },
                        {
                            "id": 12278,
                            "name": "Fibre"
                        },
                        {
                            "id": 12279,
                            "name": "Linen"
                        },
                        {
                            "id": 12280,
                            "name": "Lureks"
                        },
                        {
                            "id": 12281,
                            "name": "Metalik İplik"
                        },
                        {
                            "id": 12282,
                            "name": "Mikro Polyester"
                        },
                        {
                            "id": 12283,
                            "name": "Poliakrilik"
                        },
                        {
                            "id": 12284,
                            "name": "Spandeks"
                        },
                        {
                            "id": 12285,
                            "name": "Viskoz"
                        },
                        {
                            "id": 12286,
                            "name": "Yün"
                        },
                        {
                            "id": 16668,
                            "name": "%100 Viskon"
                        },
                        {
                            "id": 16826,
                            "name": "%100 Polyester"
                        },
                        {
                            "id": 19513,
                            "name": "Pamuk-Elastan"
                        },
                        {
                            "id": 22135,
                            "name": "Pamuk-Polyester-Elastan"
                        },
                        {
                            "id": 23674,
                            "name": "Elastan-Viskon-Polyester"
                        },
                        {
                            "id": 137105,
                            "name": "Yün - Akrilik - Polyester"
                        },
                        {
                            "id": 144229,
                            "name": "%100 Organik Pamuk"
                        },
                        {
                            "id": 144666,
                            "name": "Pamuk-Viskon-Polyester"
                        },
                        {
                            "id": 165153,
                            "name": "Polietilen"
                        },
                        {
                            "id": 176093,
                            "name": "Pamuk - Polyamid"
                        },
                        {
                            "id": 194604,
                            "name": "Pamuk - Polietilen"
                        },
                        {
                            "id": 212262,
                            "name": "%100 Pamuk"
                        },
                        {
                            "id": 997542,
                            "name": "Polyamid"
                        },
                        {
                            "id": 997984,
                            "name": "Viskon Karışımlı"
                        },
                        {
                            "id": 997987,
                            "name": "Polyester Karışımlı"
                        },
                        {
                            "id": 997994,
                            "name": "Polyamid Karışımlı"
                        },
                        {
                            "id": 998003,
                            "name": "Yün Karışımlı"
                        },
                        {
                            "id": 998008,
                            "name": "Pamuk Karışımlı"
                        },
                        {
                            "id": 998013,
                            "name": "Pamuk Polyester"
                        },
                        {
                            "id": 998020,
                            "name": "Keten Karışımlı"
                        },
                        {
                            "id": 1005632,
                            "name": "Lyocell Karışımlı"
                        },
                        {
                            "id": 1005633,
                            "name": "Keten Görünümlü"
                        },
                        {
                            "id": 1178581,
                            "name": "Pamuk Elastan"
                        },
                        {
                            "id": 1178593,
                            "name": "Polyester Elastan"
                        }
                    ],
                    "categoryId": 601,
                    "required": False,
                    "varianter": False,
                    "slicer": False
                },
                {
                    "allowCustom": False,
                    "attribute": {
                        "id": 18,
                        "name": "Parça Sayısı"
                    },
                    "attributeValues": [
                        {
                            "id": 314394,
                            "name": "3"
                        },
                        {
                            "id": 314396,
                            "name": "1"
                        },
                        {
                            "id": 314398,
                            "name": "2"
                        },
                        {
                            "id": 314400,
                            "name": "5"
                        },
                        {
                            "id": 314401,
                            "name": "4"
                        },
                        {
                            "id": 417420,
                            "name": "6"
                        }
                    ],
                    "categoryId": 601,
                    "required": False,
                    "varianter": False,
                    "slicer": False
                },
                {
                    "allowCustom": False,
                    "attribute": {
                        "id": 22,
                        "name": "Yaka Tipi"
                    },
                    "attributeValues": [
                        {
                            "id": 175,
                            "name": "Balıkçı Yaka"
                        },
                        {
                            "id": 176,
                            "name": "Bebe Yaka"
                        },
                        {
                            "id": 177,
                            "name": "Bisiklet Yaka"
                        },
                        {
                            "id": 178,
                            "name": "Degaje Yaka"
                        },
                        {
                            "id": 179,
                            "name": "Dik Yaka"
                        },
                        {
                            "id": 180,
                            "name": "Hakim Yaka"
                        },
                        {
                            "id": 181,
                            "name": "Kare Yaka"
                        },
                        {
                            "id": 182,
                            "name": "Kayık Yaka"
                        },
                        {
                            "id": 184,
                            "name": "Kruvaze Yaka"
                        },
                        {
                            "id": 186,
                            "name": "Kalp Yaka"
                        },
                        {
                            "id": 188,
                            "name": "Straplez"
                        },
                        {
                            "id": 189,
                            "name": "Şal Yaka"
                        },
                        {
                            "id": 190,
                            "name": "U Yaka"
                        },
                        {
                            "id": 191,
                            "name": "V-Yaka"
                        },
                        {
                            "id": 192,
                            "name": "Yuvarlak Yaka"
                        },
                        {
                            "id": 779,
                            "name": "Marine"
                        },
                        {
                            "id": 780,
                            "name": "Asimetrik Yaka"
                        },
                        {
                            "id": 781,
                            "name": "Boyundan Bağlamalı"
                        },
                        {
                            "id": 782,
                            "name": "Carmen Yaka"
                        },
                        {
                            "id": 783,
                            "name": "Halter Yaka"
                        },
                        {
                            "id": 784,
                            "name": "V Yaka"
                        },
                        {
                            "id": 785,
                            "name": "Choker Yaka"
                        },
                        {
                            "id": 786,
                            "name": "Boğazlı"
                        },
                        {
                            "id": 788,
                            "name": "Klasik"
                        },
                        {
                            "id": 789,
                            "name": "Kolej Yaka"
                        },
                        {
                            "id": 792,
                            "name": "Yarım Balıkçı Yaka"
                        },
                        {
                            "id": 793,
                            "name": "Ata Yaka"
                        },
                        {
                            "id": 795,
                            "name": "Gizli Düğmeli Yaka"
                        },
                        {
                            "id": 796,
                            "name": "İtalyan Yaka"
                        },
                        {
                            "id": 797,
                            "name": "Yarım İtalyan Yaka"
                        },
                        {
                            "id": 798,
                            "name": "Smokin"
                        },
                        {
                            "id": 799,
                            "name": "Beyzbol Yaka"
                        },
                        {
                            "id": 800,
                            "name": "Resort Yaka"
                        },
                        {
                            "id": 801,
                            "name": "Çentik Yaka"
                        },
                        {
                            "id": 802,
                            "name": "Sivri Yaka"
                        },
                        {
                            "id": 803,
                            "name": "Oyuk Yaka"
                        },
                        {
                            "id": 804,
                            "name": "Düğmeli"
                        },
                        {
                            "id": 805,
                            "name": "Fermuarlı"
                        },
                        {
                            "id": 806,
                            "name": "Kapamasız"
                        },
                        {
                            "id": 807,
                            "name": "Gömlek Yaka"
                        },
                        {
                            "id": 808,
                            "name": "Kapüşonlu"
                        },
                        {
                            "id": 2838,
                            "name": "Devrik Yaka"
                        },
                        {
                            "id": 2839,
                            "name": "İspanyol Yaka"
                        },
                        {
                            "id": 2840,
                            "name": "Dantel Yaka"
                        },
                        {
                            "id": 2845,
                            "name": "Madonna Yaka"
                        },
                        {
                            "id": 2846,
                            "name": "Havuz Yaka"
                        },
                        {
                            "id": 2847,
                            "name": "İspanyol"
                        },
                        {
                            "id": 2852,
                            "name": "Polo Yaka"
                        },
                        {
                            "id": 2854,
                            "name": "O Yaka"
                        },
                        {
                            "id": 2864,
                            "name": "Sıfır Yaka"
                        },
                        {
                            "id": 2870,
                            "name": "Geniş Yaka"
                        },
                        {
                            "id": 22140,
                            "name": "Balerin Yaka"
                        },
                        {
                            "id": 22141,
                            "name": "Alttan Biritli Yaka"
                        },
                        {
                            "id": 22142,
                            "name": "Mono Yaka"
                        },
                        {
                            "id": 22143,
                            "name": "Kırlangıç Yaka"
                        },
                        {
                            "id": 22144,
                            "name": "Tulum Yaka"
                        },
                        {
                            "id": 23359,
                            "name": "Pis Yaka"
                        },
                        {
                            "id": 175940,
                            "name": "Ceket Yaka"
                        },
                        {
                            "id": 175941,
                            "name": "Erkek Yaka"
                        },
                        {
                            "id": 175942,
                            "name": "Fular Yaka"
                        },
                        {
                            "id": 194557,
                            "name": "Bomber Yaka"
                        },
                        {
                            "id": 256019,
                            "name": "Kruvaze"
                        },
                        {
                            "id": 260637,
                            "name": "Apaş Yaka"
                        },
                        {
                            "id": 902493,
                            "name": "Düğmeli Yaka"
                        },
                        {
                            "id": 1178240,
                            "name": "Choker"
                        },
                        {
                            "id": 1178764,
                            "name": "Yakasız"
                        }
                    ],
                    "categoryId": 601,
                    "required": False,
                    "varianter": False,
                    "slicer": False
                }]
        }


class GetAttributes(ChannelCommandInterface):
    """
    It is the class that enables the creation of attribute and attribute values
    without depending on category.
    """

    def get_data(self):
        data = self.objects
        return data

    def validated_data(self, data) -> object:
        return data

    def transform_data(self, data) -> object:
        return data

    def send_request(self, transformed_data) -> object:
        response = self.__mocked_request(data=transformed_data)
        return response

    def normalize_response(self, data, validated_data, transformed_data,
                           response) -> Tuple[
        List[AttributeDto], ErrorReportDto, Any]:
        """
        It is the method where the response
        from the Channel is processed and
        AttributeDto and AttributeValueDto are created.
        """
        report = self.create_report(response)

        response = response.json()
        attributes = []
        for attribute in response:
            attr = AttributeDto(remote_id=attribute["id"],
                                name=attribute["name"],
                                values=[])
            for attribute_value in attribute["attr_values"]:
                attr.values.append(
                    AttributeValueDto(remote_id=attribute_value["id"],
                                      name=attribute_value["name"]))
            attributes.append(attr)

        return attributes, report, data

    @mock_response_decorator
    def __mocked_request(self, data):
        """
        Mock a request and response for the send operation to mimic actual channel data
        """

        return [{
            "id": 123213,
            "name": "Color",
            "attr_values": [{"id": 213124,
                             "name": "Green"},
                            {"id": 21442,
                             "name": "Red"}]
        }]


class GetChannelConfSchema(ChannelCommandInterface):
    """
    Prepare channel conf schema
    """

    def get_data(self):
        return

    def validated_data(self, data) -> object:
        return data

    def transform_data(self, data) -> object:
        return data

    def send_request(self, transformed_data) -> object:
        return transformed_data

    def normalize_response(self, data, validated_data, transformed_data,
                           response) -> Tuple[dict, Any, Any]:
        schema = {
            "setting_name": ChannelConfSchemaField(
                required=True,
                data_type=ChannelConfSchemaDataTypes.bool,
                key="setting_name",
                label="setting_name"),
            "setting_name_2": ChannelConfSchemaField(
                required=True,
                data_type=ChannelConfSchemaDataTypes.text,
                key="setting_name_2",
                label="setting_name_2"),
            "reason_mapping": ChannelConfSchemaField(
                required=True,
                data_type=ChannelConfSchemaDataTypes.json,
                key="reason_mapping",
                label="reason_mapping"),
        }

        return schema, None, None
