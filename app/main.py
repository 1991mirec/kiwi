import logging

from aiohttp import web
from aiohttp_swagger3 import SwaggerDocs, SwaggerUiSettings, SwaggerInfo

from api.request_handlers.flight import FlightHandler


logger = logging.getLogger(__name__)


def create_app():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    flight_handler = FlightHandler()

    app.on_startup.append(flight_handler.startup)

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
