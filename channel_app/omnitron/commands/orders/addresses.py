from omnisdk.omnitron.endpoints import (ChannelAddressEndpoint,
                                        ChannelCountryEndpoint,
                                        ChannelCityEndpoint,
                                        ChannelTownshipEndpoint,
                                        ChannelDistrictEndpoint,
                                        ChannelRetailStoreEndpoint)
from omnisdk.omnitron.models import (City, Country, Township, District, Address,
                                     Customer)
from requests import HTTPError

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.data import AddressDto
from channel_app.omnitron.constants import INTEGRATION_TYPE, ErrorType
from channel_app.omnitron.exceptions import (CountryException,
                                             IntegrationMappingException,
                                             CityException, TownshipException,
                                             DistrictException)


class GetOrCreateAddress(OmnitronCommandInterface):
    endpoint = ChannelAddressEndpoint

    def get_data(self) -> dict:
        """
        :return:
        {
            "email": "john.doe@akinon.com",
            "phone_number": "05556667788",
            "first_name": "John",
            "last_name": "Doe",
            "country": 1,
            "city": 80,
            "line": "Hemen sahil kenarı",
            "title": "COMM-876",
            "township": 933,
            "district": 71387,
            "postcode": "",
            "notes": null,
            "company_name": "",
            "tax_office": "",
            "tax_no": "",
            "e_bill_taxpayer": false,
            "hash_data": "b5e07b50cb033f5e4c86de7f1093bb37",
            "address_type": "customer",
            "retail_store": null,
            "remote_id": null,
            "identity_number": null,
            "extra_field": {},
            "customer": 36406,
            "is_active": true
        },
        """
        address: AddressDto = self.objects["address"]
        customer: Customer = self.objects["customer"]
        country_pk, city_pk, township_pk, district_pk = \
            self.get_location_objects(address.country,
                                      address.city,
                                      address.township,
                                      address.district)
        data = {
            "email": address.email[:254],
            "phone_number": address.phone_number[:128],
            "first_name": (address.first_name or customer.first_name)[:255],
            "last_name": (address.last_name or customer.last_name)[:255],
            "customer": customer.pk,
            "country": country_pk,
            "city": city_pk,
            "township": township_pk,
            "district": district_pk,
            "title": address.title and address.title[:128],
            "line": address.line[:255],
            "postcode": address.postcode and address.postcode[:64],
            "notes": address.notes and address.notes[:512],
            "company_name": address.company_name and address.company_name[:255],
            "tax_office": address.tax_office and address.tax_office[:64],
            "tax_no": address.tax_no and address.tax_no[:20],
            "e_bill_taxpayer": address.e_bill_taxpayer or False,
            "remote_id": address.remote_id,
            "identity_number": address.identity_number and address.identity_number[:64],
            "extra_field": address.extra_field or {}
        }
        self.get_retail_store_id(address, data)
        return data

    def get_retail_store_id(self, address, data):
        """

        :param data: omnitron address payload dict
        :param address: AddressDto
        """
        if address.retail_store:
            endpoint = ChannelRetailStoreEndpoint(
                channel_id=self.integration.channel_id)
            params = {"erp_code": address.retail_store}
            retail_store = endpoint.list(params=params)
            if len(retail_store) == 1:
                data["retail_store"] = retail_store[0].pk
                data["address_type"] = "retail_store"
            else:
                raise IntegrationMappingException(params={
                    "code": address.retail_store})

    def send(self, validated_data) -> object:
        """

        :param validated_data: data for address
        :return: address objects
        """
        try:
            address_obj = Address(**validated_data)
            address = self.endpoint(
                channel_id=self.integration.channel_id).create(
                item=address_obj)
        except HTTPError as e:
            addresses = []
            if ("hash_data" in e.response.text and
                    "non_field_errors" in e.response.text):
                try:
                    error_data = e.response.json()['non_field_errors'].split()[0].split(':')
                    if error_data[0] == "hash_data":
                        hash_data = error_data[1]
                        addresses = self.endpoint(
                            channel_id=self.integration.channel_id).list(
                            params={"hash_data": hash_data})
                except Exception:
                    pass
            if len(addresses) != 1:
                raise
            address = addresses[0]
        return [address]

    def check_run(self,  is_ok, formatted_data):
        if formatted_data:
            return True
        return False

    def get_location_objects(self, country_code, city_name, township_name=None,
                             district_name=None):
        """
        :param country_code: country code ("Tr")
        :param city_name: city name ("Istanbul")
        :param township_name: town ship ("Kadikoy")
        :param district_name: district name ("Moda")
        :return: country_pk, city_pk, township_pk, district_pk
        """
        country = self.get_country(country_code=country_code)
        country_pk = country.pk

        city = self.get_city(country=country, city_name=city_name)
        city_pk = city.pk
        township = None
        township_pk = None
        if township_name:
            township = self.get_township(country=country, city=city,
                                         township_name=township_name)
            township_pk = township.pk
        district_pk = None
        if district_name and township:
            district = self.get_district(country=country, city=city,
                                         township=township,
                                         district_name=district_name)
            district_pk = district.pk
        return country_pk, city_pk, township_pk, district_pk

    def get_mapping_object(self, code, endpoint, extra_filters=None):
        """
        :param code: Identifier code for the City and Country on the Sales Channel. This is
            prefix with channel_id as integration_code
        :param endpoint: omnitron sdk endpoint
        :param extra_filters: extra filters for the endpoint, dict or None
        :return: mapped objects E.g (City, Country)
        """
        integration_code = f"{self.integration.channel_id}_{code}"
        params = {"mapping__code__exact": integration_code,
                  "mapping__integration_type": INTEGRATION_TYPE}
        if extra_filters:
            params.update(extra_filters)
        objects = endpoint.list(params=params)
        if len(objects) != 1:
            raise IntegrationMappingException(params={"code": integration_code})
        return objects

    def get_country(self, country_code: str) -> Country:
        endpoint = ChannelCountryEndpoint(channel_id=self.integration.channel_id)

        params = {"code__exact": country_code, "is_active": True}
        countries = endpoint.list(params=params)
        if len(countries) == 1:
            return countries[0]
        params = {"name__exact": country_code, "is_active": True}
        countries = endpoint.list(params=params)
        if len(countries) == 1:
            return countries[0]        
        try:
            countries = self.get_mapping_object(country_code, endpoint)
        except IntegrationMappingException as exc:
            raise CountryException(params={
                "type": ErrorType.country.value,
                "remote_code": exc.params['code'],
                "country_code": country_code,
                "name": country_code,
                "integration_type": INTEGRATION_TYPE,
                "err_code": "Country was not found",
                "err_desc": f"Country code {country_code} was not found in Omnitron"})
        return countries[0]

    def get_city(self, country: Country, city_name: str) -> City:
        endpoint = ChannelCityEndpoint(channel_id=self.integration.channel_id)

        params = {
            "name__iexact": city_name,
            "country": country.pk,
            "is_active": True
        }
        cities = endpoint.list(params=params)
        if len(cities) == 1:
            return cities[0]
        try:
            cities = self.get_mapping_object(code=city_name, endpoint=endpoint)
        except IntegrationMappingException as exc:
            raise CityException(
                params={"type": ErrorType.city.value,
                        "remote_code": exc.params['code'],
                        "country_id": country.pk,
                        "integration_type": INTEGRATION_TYPE,
                        "err_code": "integrations_200_10_2",
                        "err_desc": f"Address is not valid. channel: {self.integration.channel_id} "
                                    f"code:{exc.params['code']} "
                                    f"model: City country id: {country.pk}"})
        return cities[0]

    def get_township(self, country: Country, city: City, township_name: str) -> Township:
        endpoint = ChannelTownshipEndpoint(channel_id=self.integration.channel_id)

        params = {
            "name__iexact": township_name,
            "country": country.pk,
            "city": city.pk,
            "is_active": True
        }
        townships = endpoint.list(params=params)
        if len(townships) == 1:
            return townships[0]
        try:
            extra_filters = {"city": city.pk, "is_active": True}
            townships = self.get_mapping_object(township_name, endpoint, extra_filters)
        except IntegrationMappingException as exc:
            raise TownshipException(
                params={"type": ErrorType.township.value,
                        "remote_code": exc.params['code'],
                        "city_id": city.pk,
                        "name": township_name,
                        "integration_type": INTEGRATION_TYPE,
                        "err_code": "integrations_200_10_1",
                        "err_desc": f"Address is not valid. channel: {self.integration.channel_id}"
                                    f"code: {exc.params['code']} "
                                    f"model: Township city id: {city.pk}"})
        return townships[0]

    def get_district(self, country: Country, city: City, township: Township,
                     district_name: str) -> District:
        endpoint = ChannelDistrictEndpoint(channel_id=self.integration.channel_id)

        params = {
            "name__exact": district_name,
            "country": country.pk,
            "city": city.pk,
            "township": township.pk,
            "is_active": True
        }
        districts = endpoint.list(params=params)
        if len(districts) == 1:
            return districts[0]
        try:
            extra_filters = {"city": city.pk, "township": township.pk, "is_active": True}
            districts = self.get_mapping_object(district_name, endpoint, extra_filters)
        except IntegrationMappingException as exc:
            raise DistrictException(
                params={"type": ErrorType.district.value,
                        "remote_code": exc.params['code'],
                        "city_id": city.pk,
                        "township_id": township.pk,
                        "name": district_name,
                        "integration_type": INTEGRATION_TYPE,
                        "err_code": "integrations_200_10_3",
                        "err_desc": f"Address is not valid. channel: {self.integration.channel_id}"
                                    f"code: {exc.params['code']} "
                                    f"model: District township id: {township.pk}"}
            )
        return districts[0]
