import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from channel_app.omnitron.constants import CancellationType, ResponseStatus, \
    ChannelConfSchemaDataTypes


@dataclass
class CategoryNodeDto:
    name: str
    children: List['CategoryNodeDto']
    remote_id: Optional[str] = ''
    parent: Optional['CategoryNodeDto'] = None


@dataclass
class CategoryTreeDto:
    root: CategoryNodeDto


@dataclass
class CategoryAttributeValueDto:
    remote_id: str
    name: str


@dataclass
class CategoryAttributeDto:
    remote_id: str
    name: str
    required: bool
    variant: bool
    allow_custom_value: bool
    values: List[CategoryAttributeValueDto]


@dataclass
class AttributeValueDto:
    remote_id: str
    name: str


@dataclass
class AttributeDto:
    remote_id: str
    name: str
    values: List[AttributeValueDto]


@dataclass
class CategoryDto:
    remote_id: str
    name: str
    attributes: List[CategoryAttributeDto]


@dataclass
class ChannelConfSchemaField:
    required: bool
    data_type: ChannelConfSchemaDataTypes
    key: str
    label: str
    schema: Optional[dict] = None


@dataclass
class ErrorReportDto:
    action_content_type: str
    action_object_id: int
    modified_date: str
    raw_request: str = ""
    raw_response: str = ""
    error_code: str = "custom"
    error_description: str = "custom"
    is_ok: bool = False
    target_content_type: Optional[str] = ''
    target_object_id: Optional[str] = ''


@dataclass
class BatchRequestObjectsDto:
    pk: int
    version_date: str
    content_type: str
    failed_reason_type: Optional[str] = ''
    remote_id: Optional[int] = 0


class BatchRequestDto:
    channel: int
    local_batch_id: str
    content_type: str
    pk: Optional[int] = 0
    remote_batch_id: Optional[str] = ''
    status: Optional[str] = ''
    objects: Optional[List[BatchRequestObjectsDto]] = []


@dataclass
class ProductBatchRequestResponseDto:
    status: ResponseStatus
    sku: str
    remote_id: Optional[str] = ''
    message: Optional[str] = ''


@dataclass
class BatchRequestResponseDto:
    status: ResponseStatus
    remote_id: Optional[str] = ''
    sku: Optional[str] = ''
    message: Optional[str] = ''


@dataclass
class OrderBatchRequestResponseDto:
    status: ResponseStatus
    remote_id: str
    number: str
    message: Optional[str] = ''


@dataclass
class OmnitronOrderDto:
    remote_id: str
    number: str
    channel: int
    customer: int
    shipping_address: int
    billing_address: int
    currency: str
    amount: Decimal
    shipping_amount: Decimal
    shipping_tax_rate: Decimal
    extra_field: dict
    cargo_company: int
    created_at: datetime.datetime
    delivery_type: Optional[str] = None
    discount_amount: Optional[Decimal] = "0.0"
    net_shipping_amount: Optional[Decimal] = "0.0"
    tracking_number: Optional[str] = None
    carrier_shipping_code: Optional[str] = ""
    remote_addr: Optional[str] = None
    has_gift_box: Optional[bool] = False
    gift_box_note: Optional[str] = ""
    client_type: Optional[str] = ""
    language_code: Optional[str] = ""
    notes: Optional[str] = ""
    delivery_range: Optional[str] = None
    shipping_option_slug: Optional[str] = ""
    status: Optional[str] = ""


@dataclass
class OrderItemDto:
    remote_id: str
    product: str
    price_currency: str
    price: Decimal
    tax_rate: Decimal
    extra_field: dict
    status: Optional[str] = None
    price_list: Optional[int] = None
    stock_list: Optional[int] = None
    tracking_number: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    carrier_shipping_code: Optional[str] = ""
    discount_amount: Optional[Decimal] = 0.0
    retail_price: Optional[Decimal] = 0.0
    attributes: Optional[dict] = None
    attributes_kwargs: Optional[dict] = None
    parent: Optional[str] = None
    delivered_date: Optional[str] = None
    estimated_delivery_date: Optional[str] = None


# dataclass used for omnitron.commands.orders.orders.CreateOrders
@dataclass
class OmnitronCreateOrderDto:
    order: OmnitronOrderDto
    order_item: List[OrderItemDto]


@dataclass
class CancelOrderDto:
    order: str  # remote order number
    cancel_items: List[str]  # order_item_remote_id list
    reasons: dict  # order_item_remote_id : reason code
    is_cargo_refund: Optional[bool] = False  # default False
    forced_refund_amount: Optional[bool] = None  # default False
    refund_invoice_number: Optional[str] = None


@dataclass
class CancellationRequestDto:
    order_item: str  # remote item number
    reason: str      # reason code
    remote_id: str
    description: str
    cancellation_type: Optional[str] = "cancel"


@dataclass
class CustomerDto:
    email: str  # "john.doe@akinon.com"
    first_name: str  # "John"
    last_name: str  # "Doe"
    channel_code: str  # will be unique
    extra_field: Optional[dict] = None
    phone_number: Optional[str] = None  # "05556667788"
    is_active: Optional[bool] = True


@dataclass
class AddressDto:
    email: str  # "john.doe@akinon.com"
    phone_number: str  # "05556667788"
    first_name: str  # "John"
    last_name: str  # "Doe"
    country: str  # 1
    city: str  # 80
    line: str  # "Hemen sahil kenarı"
    title: Optional[str] = None  # "COMM-876"
    township: Optional[str] = None  # 933
    district: Optional[str] = None  # 71387
    postcode: Optional[str] = None  # ""
    notes: Optional[str] = None  # null
    company_name: Optional[str] = None  # ""
    tax_office: Optional[str] = None  # ""
    tax_no: Optional[str] = None  # ""
    e_bill_taxpayer: Optional[bool] = False
    remote_id: Optional[str] = None  # null
    identity_number: Optional[str] = None  # null
    extra_field: Optional[dict] = None  # {}
    is_active: Optional[bool] = True  # true
    retail_store: Optional[str] = None


@dataclass
class ChannelOrderDto(OmnitronOrderDto):
    customer = CustomerDto
    shipping_address = AddressDto
    billing_address = AddressDto
    cargo_company = str


@dataclass
class ChannelCreateOrderDto:
    order: ChannelOrderDto
    order_item: List[OrderItemDto]


@dataclass
class ChannelUpdateOrderItemDto:
    remote_id: str
    order_remote_id: Optional[str] = None
    order_number: Optional[str] = None
    status: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    tracking_number: Optional[str] = None
    extra_field: Optional[dict] = None


@dataclass
class ChannelCancellationRequestDto:
    cancellation_type: CancellationType  # cancel, refund
    status: str  # confirmed, waiting_approval, approved, rejected, completed
    order_item: str  # omnitron order item remote id
    reason: str  # omnitron reason code
    description: Optional[str]  # description for refund
    remote_id: Optional[str]  # remote id for cancellation request
