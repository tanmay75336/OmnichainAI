from flask import Blueprint, current_app, request

from app.services.insight_service import format_simulation_for_llm
from app.services.risk_service import calculate_risk
from app.services.route_service import build_route_snapshot
from app.services.simulation_service import simulate_disruption
from app.utils.errors import ValidationError
from app.utils.responses import success_response


supply_chain_bp = Blueprint("supply_chain", __name__)


@supply_chain_bp.post("/get-route")
def get_route():
    payload = request.get_json(silent=True) or {}

    source = payload.get("source")
    destination = payload.get("destination")
    transport_mode = payload.get("transport_mode")
    region_type = payload.get("region_type", "tier_2")

    if not source or not destination or not transport_mode:
        raise ValidationError(
            "Fields 'source', 'destination', and 'transport_mode' are required."
        )

    route_snapshot = build_route_snapshot(
        source=source,
        destination=destination,
        transport_mode=transport_mode,
        region_type=region_type,
        config=current_app.config,
        logger=current_app.logger,
    )

    risk_assessment = calculate_risk(
        route_data=route_snapshot["route"],
        weather=route_snapshot["weather"],
        region_type=region_type,
    )

    route_snapshot["risk"] = risk_assessment

    return success_response(
        message="Route intelligence generated successfully.",
        data=route_snapshot,
    )


@supply_chain_bp.post("/simulate")
def simulate():
    payload = request.get_json(silent=True) or {}

    route_payload = payload.get("route") or {}
    disruption_type = payload.get("disruption_type")

    if not route_payload or not disruption_type:
        raise ValidationError("Fields 'route' and 'disruption_type' are required.")

    source = route_payload.get("source")
    destination = route_payload.get("destination")
    transport_mode = route_payload.get("transport_mode")
    region_type = route_payload.get("region_type", "tier_2")

    if not source or not destination or not transport_mode:
        raise ValidationError(
            "Route must include 'source', 'destination', and 'transport_mode'."
        )

    route_snapshot = build_route_snapshot(
        source=source,
        destination=destination,
        transport_mode=transport_mode,
        region_type=region_type,
        config=current_app.config,
        logger=current_app.logger,
    )

    baseline_risk = calculate_risk(
        route_data=route_snapshot["route"],
        weather=route_snapshot["weather"],
        region_type=region_type,
    )

    simulation_result = simulate_disruption(
        route_snapshot=route_snapshot,
        disruption_type=disruption_type,
        baseline_risk=baseline_risk,
    )
    simulation_result["ai_prompt_text"] = format_simulation_for_llm(simulation_result)

    return success_response(
        message="Simulation completed successfully.",
        data=simulation_result,
    )
