from flask import Blueprint, current_app

from app.services.gemini_service import gemini_is_configured
from app.services.tracking_service import build_tracking_health
from app.utils.responses import success_response


health_bp = Blueprint("health", __name__)


@health_bp.get("/")
def root():
    return success_response(
        message="Smart Supply Chain Optimization backend is running.",
        data={
            "status": "ok",
            "service": "Smart Supply Chain Optimization System",
            "tracking": build_tracking_health(current_app.config),
            "gemini": {
                "configured": gemini_is_configured(current_app.config),
            },
            "available_endpoints": [
                "/health",
                "/get-route",
                "/simulate",
                "/tracking/health",
                "/tracking/shipments",
                "/tracking/shipments/<shipment_id>",
                "/tracking/shipments/<shipment_id>/telemetry",
            ],
        },
    )


@health_bp.get("/health")
def health_check():
    return success_response(
        message="Smart Supply Chain Optimization backend is healthy.",
        data={
            "status": "ok",
            "tracking": build_tracking_health(current_app.config),
            "gemini": {
                "configured": gemini_is_configured(current_app.config),
            },
        },
    )
