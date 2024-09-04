from dataclasses import asdict
from omnisdk.omnitron.endpoints import ChannelCustomerEndpoint
from omnisdk.omnitron.models import Customer

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.data import CustomerDto
from channel_app.omnitron.constants import CustomerIdentifierField


class GetOrCreateCustomer(OmnitronCommandInterface):
    endpoint = ChannelCustomerEndpoint

    def get_data(self) -> Customer:
        data = self.objects
        data: CustomerDto
        return self.get_customer(data)

    def get_customer(self, data: CustomerDto) -> Customer:
        customer_identifier_field = self.integration.channel.conf.get(
            "CUSTOMER_IDENTIFIER_FIELD", CustomerIdentifierField.email)
        customers = None
        if customer_identifier_field == CustomerIdentifierField.email:
            customers = self.endpoint(channel_id=self.integration.channel_id).list(params={
                "email": data.email,
                "channel": self.integration.channel_id
            })
            for c in customers:
                if c.email != data.email:
                    raise Exception("Customer email filter incorrect")
        elif customer_identifier_field == CustomerIdentifierField.phone_number:
            customers = self.endpoint(channel_id=self.integration.channel_id).list(params={
                "phone_number": data.phone_number,
                "channel": self.integration.channel_id
            })
            for c in customers:
                if c.phone_number != data.phone_number:
                    raise Exception("Customer phone_number filter incorrect")

        if customers:
            customer = customers[0]
            must_update = False
            new_customer = Customer()
            new_customer.channel = customer.channel
            new_customer.channel_code = customer.channel_code
            if "email" in asdict(data) and data.email != customer.email:
                must_update = True
                new_customer.email = data.email
            if "phone_number" in asdict(data) and data.phone_number != customer.phone_number:
                must_update = True
                new_customer.phone_number = data.phone_number
            if "first_name" in asdict(data) and data.first_name != customer.first_name:
                must_update = True
                new_customer.first_name = data.first_name
            if "last_name" in asdict(data) and data.last_name != customer.last_name:
                must_update = True
                new_customer.last_name = data.last_name
            if must_update:
                customer = self.endpoint(channel_id=self.integration.channel_id).update(
                    id=customer.pk, item=new_customer)
        else:
            new_customer = Customer()
            new_customer.channel = self.integration.channel_id
            new_customer.email = data.email
            new_customer.phone_number = data.phone_number
            new_customer.first_name = data.first_name
            new_customer.last_name = data.last_name
            new_customer.extra_field = data.extra_field or {}
            new_customer.channel_code = data.channel_code
            new_customer.is_active = data.is_active or True
            new_customer = self.endpoint(channel_id=self.integration.channel_id).create(
                item=new_customer)
            customer = new_customer
        return [customer]
