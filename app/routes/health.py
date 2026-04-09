from flask import Blueprint

from app.utils.responses import success_response


health_bp = Blueprint("health", __name__)


@health_bp.get("/")
def root():
    return success_response(
        message="Smart Supply Chain Optimization backend is running.",
        data={
            "status": "ok",
            "service": "Smart Supply Chain Optimization System",
            "available_endpoints": ["/health", "/get-route", "/simulate"],
        },
    )


@health_bp.get("/health")
def health_check():
    return success_response(
        message="Smart Supply Chain Optimization backend is healthy.",
        data={"status": "ok"},
    )
