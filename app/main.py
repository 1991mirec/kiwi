import logging

from aiohttp import web
from aiohttp_swagger3 import SwaggerDocs, SwaggerUiSettings, SwaggerInfo

from api.request_handlers.flight import FlightHandler
#from cache.redis_cache import RedisCache


logger = logging.getLogger(__name__)


# async def redis_connect(app):
#     app['redis'] = await RedisCache(redis_host='redis')
#
#
# async def redis_disconnect(app):
#     logger.info("Redis connection closed.")


def create_app():
    logging.basicConfig(level=logging.DEBUG)
    app = web.Application()
    flight_handler = FlightHandler()

    app.on_startup.append(flight_handler.startup)
    #app.on_cleanup.append(redis_disconnect)

    swagger_info = SwaggerInfo(
        title="Kiwi flight API",
        version="1.0.0",
        description="API documentation with OpenAPI 3.0 for Kiwi flight API",
    )
    swagger = SwaggerDocs(
        app,
        swagger_ui_settings=SwaggerUiSettings(path="/api/doc"),
        info=swagger_info
    )
    swagger.add_routes([web.get('/search-flight', flight_handler.search_flight, allow_head=False)])

    return app


if __name__ == '__main__':
    app = create_app()
    logger.info("Starting aiohttp app")
    web.run_app(app, host='0.0.0.0', port=8080)
