import json
from typing import Optional, List, Dict

from redis.asyncio import BlockingConnectionPool, Redis, RedisError
import logging
import asyncio

logger = logging.getLogger(__name__)


class RedisCache:
    RECONNECTION_TIME = 10
    CONNECTION_CHECK_TIME = 60
    EXPIRATION_TIME = 86400

    def __init__(self, db: int, expiration: int):
        self.__pool = BlockingConnectionPool(host='redis', decode_responses=True, db=db)
        self._pool = None
        self._connected = False
        self._connecting = False
        self._expiration = expiration

    async def init(self):
        try:
            self._pool = Redis(connection_pool=self.__pool)
            await self._pool.ping()  # Check if the connection is successful
            self._connected = True
            logger.info('Connected to Redis.')
        except RedisError as e:
            logger.warning(f'Failed to connect to Redis: {e}')
            self._connected = False
        return self

    async def _reconnect(self):
        """
        Attempts to reconnect to Redis.
        """
        self._connecting = True
        while not self._connected:
            logger.info('Attempting to reconnect to Redis...')
            try:
                await self.init()
                if self._connected:
                    logger.info('Reconnected to Redis successfully.')
                    self._connecting = False
                    break
            except RedisError as e:
                logger.warning(f'Reconnection failed: {e} trying again in {self.RECONNECTION_TIME} seconds')
            await asyncio.sleep(self.RECONNECTION_TIME)

    async def connection_checker(self):
        """
        Checks the Redis connection every self.CONNECTION_CHECK_TIME seconds and reconnects if needed.
        """
        while True:
            if self._connecting:
                # we are already trying to reconnect
                await asyncio.sleep(self.CONNECTION_CHECK_TIME)
            if not self._connected:
                logger.warning('Redis connection lost. Reconnecting...')
                await self._reconnect()
            else:
                # we should be connected lets check if connection was not lost
                try:
                    await self._pool.ping()
                except RedisError as e:
                    logger.warning(f'Failed to connect to Redis: {e}')
                    self._connected = False
                    await self._reconnect()
            await asyncio.sleep(self.CONNECTION_CHECK_TIME)

    async def _set(self, key: str, value: str) -> None:
        try:
            if self._connected:
                await self._pool.set(key, value, ex=self._expiration)
            else:
                logger.warning(f'Cannot set value. Redis is disconnected. key: "{key}" with value: "{value}" will not be cached')
        except RedisError as e:
            logger.warning(f'Cannot set value. Redis is disconnected. key: "{key}" with value: "{value}" will not be cached', e)
            self._connected = False

    async def _get(self, key: str) -> Optional[str]:
        try:
            if self._connected:
                return await self._pool.get(key)
            else:
                logger.warning(f'Cannot get value. Redis is disconnected. Forced to request new data for key "{key}"')
        except RedisError as e:
            logger.warning(f'Cannot get value. Redis is disconnected. Forced to request new data for key "{key}"', e)
            self._connected = False


# key is "src_country-dst_country" and values is "json output"
class FlightsCache(RedisCache):
    def __init__(self):
        super().__init__(db=0, expiration=self.EXPIRATION_TIME)

    async def get_flights(self, key) -> Optional[Dict[str, str]]:
        flights_str = await self._get(key)
        return json.loads(flights_str) if flights_str else None

    async def set_flights(self, key: str, values: List[Dict[str, str]]) -> None:
        await self._set(key, json.dumps(values))


class AirportsCache(RedisCache):
    def __init__(self):
        super().__init__(db=1, expiration=self.EXPIRATION_TIME*3)

    async def get_airports(self, key) -> Optional[List[str]]:
        airports_str = await self._get(key)
        return airports_str.split(',') if airports_str else None

    async def set_airports(self, key: str, values: List[str]) -> None:
        await self._set(key, ','.join(values))
