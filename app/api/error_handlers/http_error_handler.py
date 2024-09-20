from aiohttp import web


class WrongDateError(web.HTTPBadRequest):
    def __init__(self, input_date):
        super().__init__(text=f'Date {input_date} is not of format "DD/MM/YYYY"')
        self.content_type = 'application/json'

class CountryDoesNotExistError(web.HTTPBadRequest):
    def __init__(self, country):
        super().__init__(text=f'country {country} does not exist. Please try to search with different country')
        self.content_type = 'application/json'


class AirportDoesNotExistError(web.HTTPBadRequest):
    def __init__(self, country_id):
        super().__init__(text=f'There is no airport for country with id {country_id}. Please try to search with different country')
        self.content_type = 'application/json'
