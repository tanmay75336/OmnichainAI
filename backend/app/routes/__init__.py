from flask import Flask

from app.routes.health import health_bp
from app.routes.supply_chain import supply_chain_bp
from app.routes.tracking import tracking_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_bp)
    app.register_blueprint(supply_chain_bp)
    app.register_blueprint(tracking_bp)
