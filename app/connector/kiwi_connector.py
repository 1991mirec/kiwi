import os
from typing import List, Optional, Dict

import aiohttp
from aiohttp import web
from aiohttp.http_exceptions import HttpProcessingError

from api.error_handlers.http_error_handler import CountryDoesNotExistError
from api.error_handlers.http_error_handler import AirportDoesNotExistError


class KiwiConnector:
    _BASE_URL = 'https://api.tequila.kiwi.com'
    _HEADERS = {
        'accept': 'application/json',
        'apikey': os.environ.get('APIKEY'),
        'User-Agent': 'interview-task-Miroslav-Kovac'
    }
    
    def __init__(self):
        self._session = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(headers=self._HEADERS)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._session.close()

    async def get_country(self, term) -> str:
        params = {
            'term': term,
            'limit': 1,
            'location_types': 'country',
            'active_only': 'true'
        }
        url = f'{self._BASE_URL}/locations/query'
        async with self._session.get(url, params=params) as response:
            resp = await response.json()
            if resp.get('error_code', 0) == 429:
                raise web.HTTPTooManyRequests()
            if resp['results_retrieved'] == 0:
                raise CountryDoesNotExistError(term)
            else:
                return resp['locations'][0]['id']

    async def get_airports(self, term) -> List[str]:
        params = {
            'term': term,
            'limit': 3,
            'location_types': 'airport',
            'active_only': 'true',
            'sort': '-dst_popularity_score'
        }
        url = f'{self._BASE_URL}/locations/subentity'
        async with self._session.get(url, params=params) as response:
            resp = await response.json()
            if resp.get('error_code', 0) == 429:
                raise web.HTTPTooManyRequests()
            if resp['results_retrieved'] == 0:
                raise AirportDoesNotExistError(term)
            else:
                return [location['id'] for location in resp['locations']]

    async def search_flights(self, fly_from: str, fly_to: str, date_from_to: str) -> Optional[Dict[str, str]]:
        params = {
            'fly_from': f'airport:{fly_from}',
            'fly_to': f'airport:{fly_to}',
            'date_from': date_from_to,
            'date_to': date_from_to,
            'max_fly_duration': 20,  # was default not sure what 0 does
            'ret_from_diff_city': 'false',
            'ret_to_diff_city': 'false',
            'one_for_city': 0,
            'adults': 1,
            'selected_cabins': 'M',
            'only_working_days': 'false',
            'only_weekends': 'false',
            'max_stopovers': 2,
            'max_sector_stopovers': 2,
            'conn_on_diff_airport': 0,
            'ret_from_diff_airport': 0,
            'ret_to_diff_airport': 0,
            'sort': 'price',
            'limit': 1
        }
        url = f'{self._BASE_URL}/v2/search'
        async with self._session.get(url, params=params) as response:
            resp = await response.json()
            if resp.get('error_code', 0) == 429:
                raise web.HTTPTooManyRequests()
            if resp['_results'] == 0:
                return None
            else:
                data = resp['data'][0]
                return {
                    'src': data['flyFrom'],
                    'dst': data['flyTo'],
                    'price': data['price']
                }
