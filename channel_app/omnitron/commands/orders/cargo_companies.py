from typing import List

from omnisdk.omnitron.endpoints import ChannelCargoEndpoint
from omnisdk.omnitron.models import CargoCompany

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.omnitron.exceptions import CargoCompanyException


class GetCargoCompany(OmnitronCommandInterface):
    endpoint = ChannelCargoEndpoint

    def get_cargo_company(self, data):
        cargo_company_code = self.objects
        for cargo_company in data:
            if cargo_company.erp_code == cargo_company_code:
                return cargo_company
        raise CargoCompanyException("CargoCompany does not exists: {}".format(
            cargo_company_code))

    def get_data(self) -> List[CargoCompany]:
        """
        :return: [
            {
                "pk": 1,
                "name": "Yurtici Kargo",
                "erp_code": "yurtici-kargo",
                "shipping_company": "yurtici"
            },
        ]
        """
        params = getattr(self, "param_{}".format("params"), {})

        end_point = self.endpoint(channel_id=self.integration.channel_id)
        cargo_companies = end_point.list(
            params=params)
        for next_cargo_companies in end_point.iterator:
            cargo_companies.extend(next_cargo_companies)

        cargo_company = self.get_cargo_company(data=cargo_companies)
        return [cargo_company]
