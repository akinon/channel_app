class AppException(Exception):
    def __init__(self, params=None):
        super(BaseException, self).__init__()
        self.params = params

class IntegrationMappingException(AppException):
    pass


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


class OrderException(AppException):
    pass


class CargoCompanyException(AppException):
    pass


class CustomerException(AppException):
    pass
