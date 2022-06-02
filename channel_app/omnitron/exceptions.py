class IntegrationMappingException(Exception):
    def __init__(self, params=None):
        super(IntegrationMappingException, self).__init__()
        self.params = params


class CountryException(IntegrationMappingException):
    pass


class CityException(IntegrationMappingException):
    pass


class TownshipException(IntegrationMappingException):
    pass


class DistrictException(IntegrationMappingException):
    pass


class AddressException(IntegrationMappingException):
    pass


class OrderException(Exception):
    def __init__(self, params=None):
        super(OrderException, self).__init__()
        self.params = params


class CargoCompanyException(Exception):
    def __init__(self, params=None):
        super().__init__()
        self.params = params


class CustomerException(Exception):
    def __init__(self, params=None):
        super(CustomerException, self).__init__()
        self.params = params
