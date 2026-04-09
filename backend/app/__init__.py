from flask import Flask
from flask_cors import CORS

from app.config.settings import get_config
from app.routes import register_blueprints
from app.utils.errors import register_error_handlers
from app.utils.logger import configure_logging


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config())

    configure_logging(app)
    CORS(app)

    register_blueprints(app)
    register_error_handlers(app)

    return app
