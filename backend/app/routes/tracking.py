from flask import Blueprint, current_app, request

from app.services.tracking_service import (
    build_tracking_health,
    create_tracking_shipment,
    get_tracking_snapshot,
    ingest_tracking_telemetry,
)
from app.utils.responses import success_response


tracking_bp = Blueprint("tracking", __name__)


@tracking_bp.get("/tracking/health")
def tracking_health():
    return success_response(
        message="Tracking service health generated successfully.",
        data=build_tracking_health(current_app.config),
    )


@tracking_bp.post("/tracking/shipments")
def create_shipment():
    payload = request.get_json(silent=True) or {}
    shipment = create_tracking_shipment(
        payload=payload,
        config=current_app.config,
        logger=current_app.logger,
    )
    return success_response(
        message="Tracking shipment created successfully.",
        data=shipment,
        status_code=201,
    )


@tracking_bp.get("/tracking/shipments/<shipment_id>")
def get_shipment(shipment_id):
    snapshot = get_tracking_snapshot(
        shipment_id=shipment_id,
        config=current_app.config,
        logger=current_app.logger,
    )
    return success_response(
        message="Tracking snapshot generated successfully.",
        data=snapshot,
    )


@tracking_bp.post("/tracking/shipments/<shipment_id>/telemetry")
def push_telemetry(shipment_id):
    payload = request.get_json(silent=True) or {}
    snapshot = ingest_tracking_telemetry(
        shipment_id=shipment_id,
        payload=payload,
        config=current_app.config,
        logger=current_app.logger,
    )
    return success_response(
        message="Telemetry ingested successfully.",
        data=snapshot,
    )
