import asyncio
import logging
import re

from aiohttp import web
from aiohttp.web_response import Response

from api.error_handlers.http_error_handler import WrongDateError
from cache.redis_cache import AirportsCache, FlightsCache
from connector.kiwi_connector import KiwiConnector

logger = logging.getLogger(__name__)
date_pattern = re.compile(r"^(0[1-9]|[12][0-9]|3[01])\/(0[1-9]|1[0-2])\/(\d{4})$")

class FlightHandler:

    def __init__(self) -> None:
        super().__init__()
        logger.info("Initiating flight handler")
        self._airport_cache = None
        self._flight_cache = None

    async def startup(self, app):
        self._airport_cache = await AirportsCache().init()
        self._flight_cache = await FlightsCache().init()
        # Start the Redis connection checker as a background task
        app.loop.create_task(self._airport_cache.connection_checker())
        app.loop.create_task(self._flight_cache.connection_checker())

    async def search_flight(self, request) -> Response:
        """
        Search for a flight based on the source and destination countries and departure date.
        ---
        summary: Search Flight
        tags:
          - flights
        parameters:
          - in: query
            name: source_country
            schema:
              type: string
            required: true
            description: The country of origin for the flight.
          - in: query
            name: destination_country
            schema:
              type: string
            required: true
            description: The destination country for the flight.
          - in: query
            name: departure_date
            schema:
              type: string
            required: true
            description: The departure date in DD/MM/YYYY format.
        responses:
          '200':
            description: Flight search results
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: object
                    properties:
                      src:
                        type: string
                        description: Source airport code (IATA).
                        example: "JFK"
                      dst:
                        type: string
                        description: Destination airport code (IATA).
                        example: "LHR"
                      price:
                        type: number
                        description: The price of the flight.
                        example: 299.99
          '400':
            description: Invalid parameters
        """
        source_country = request.rel_url.query.get('source_country')
        destination_country = request.rel_url.query.get('destination_country')
        departure_date = request.rel_url.query.get('departure_date')

        if not self._is_valid_date(departure_date):
            raise WrongDateError(departure_date)

        # check if we have already such flight cached for such date and return if yes
        json_resp = await self._flight_cache.get_flights(f'{source_country}-{destination_country}-{departure_date}')
        if json_resp:
            return web.json_response(json_resp)

        # try to search in cache the relevant airports
        source_airports = await self._airport_cache.get_airports(source_country)
        destination_airports = await self._airport_cache.get_airports(destination_country)

        async with KiwiConnector() as connector:
            # if we did not cache figure out country id and its top airports right after
            if not source_airports:
                source_country_id = await connector.get_country(source_country)
                source_airports = await connector.get_airports(source_country_id)
                asyncio.create_task(self._airport_cache.set_airports(source_country, source_airports))
            if not destination_airports:
                destination_country_id = await connector.get_country(destination_country)
                destination_airports = await connector.get_airports(destination_country_id)
                asyncio.create_task(self._airport_cache.set_airports(destination_country, destination_airports))

            # search for each source airport with each destination airport
            coros = []
            for src_airport in source_airports:
                for dst_airport in destination_airports:
                    coros.append(connector.search_flights(src_airport, dst_airport, departure_date))
            responses = await asyncio.gather(*coros)
            output = []
            for resp in responses:
                if resp:
                    output.append(resp)
            asyncio.create_task(self._flight_cache.set_flights(key=f'{source_country}-{destination_country}-{departure_date}',
                                                                   values=output))

        return web.json_response(sorted(output, key=lambda x: x['price']))

    @staticmethod
    def _is_valid_date(date_str):
        return bool(date_pattern.match(date_str))
