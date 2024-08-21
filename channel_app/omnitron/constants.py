from enum import Enum

CHANNEL_TYPE = "sales_channel"
INTEGRATION_TYPE = "sales_channel"
CHUNK_SIZE = 50
CONTENT_TYPE_IDS = {}


class BatchRequestStatus(Enum):
    """
    Batch requests work as a state machine. These are states defined for them.
    """
    # Initial state
    initialized = "initialized"
    # Channel app reports that it received data and objects in the batch are marked so that they
    # are not reprocessed on further requests
    commit = "commit"
    # Objects are sent to the Channel and being processed on Channel side
    sent_to_remote = "sent_to_remote"
    # Objects are still being processed on the Channel
    ongoing = "ongoing"
    # Channel finished processing the batch and returned the result. Some items may be in
    # fail state
    done = "done"
    # Channel failed processing the batch and halted the process.
    fail = "fail"


class ErrorType(Enum):
    country = "country"
    city = "city"
    township = "township"
    district = "district"


class ContentType(Enum):
    """
    Omnitron model content types. Batch requests can be used for all Omnitron models. We need to
    specify content type of the model in question. Both for the batch request itself and inside the
    objects block of the batch.
    """
    # TODO check all contenttype usages and add them here
    batch_request = "batchrequest"
    product = "product"
    order = "order"
    order_item = "orderitem"
    product_price = "productprice"
    product_stock = "productstock"
    integration_action = "integrationaction"
    product_image = "productimage"
    category_tree = "categorytree"
    category_node = "categorynode"
    channel = "channel"
    product_category = "productcategory"
    attribute_set = "marketplaceattributeset"
    attribute_set_config = "marketplaceattributesetconfig"
    attribute = "marketplaceattribute"
    attribute_schema = "marketplaceattributeschema"
    attribute_value = "marketplaceattributevalue"
    attribute_value_config = "marketplaceattributevalueconfig"
    cancellation_request = "cancellationrequest"


class FailedReasonType(Enum):
    mapping = "mapping"
    remote = "remote"
    channel_app = "channel_app"


class CustomerIdentifierField(Enum):
    """
    Customer uniqueness identifier field
    """
    email = "email"
    phone_number = "phone_number"


class ResponseStatus:
    fail = "FAIL"
    success = "SUCCESS"


class IntegrationActionStatus:
    processing = "processing"
    success = "success"
    error = "error"


class ChannelConfSchemaDataTypes:
    text = 'text'
    URL = 'URL'
    email = 'email'
    date = 'date'
    datetime = 'datetime'
    bool = 'bool'
    json = 'json'
    list = 'list'
    integer = 'integer'


class CancellationType(Enum):
    cancel = "cancel"
    refund = "refund"