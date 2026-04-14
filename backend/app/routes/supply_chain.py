from flask import Blueprint, current_app, request

from app.services.insight_service import (
    build_india_context,
    build_route_decision_support,
    build_supply_chain_intelligence,
    format_simulation_for_llm,
)
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
    region_type = payload.get("region_type")
    cargo = payload.get("cargo") or {}

    if not source or not destination or not transport_mode:
        raise ValidationError(
            "Fields 'source', 'destination', and 'transport_mode' are required."
        )

    route_snapshot = build_route_snapshot(
        source=source,
        destination=destination,
        transport_mode=transport_mode,
        region_type=region_type,
        cargo=cargo,
        config=current_app.config,
        logger=current_app.logger,
    )
    route_snapshot["intelligence"] = build_supply_chain_intelligence(route_snapshot)
    route_snapshot["india_context"] = build_india_context(route_snapshot)
    route_snapshot["decision_support"] = build_route_decision_support(route_snapshot)
    response_payload = {key: value for key, value in route_snapshot.items() if key != "base_route"}

    return success_response(
        message="Route intelligence generated successfully.",
        data=response_payload,
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
    region_type = route_payload.get("region_type")
    cargo = route_payload.get("cargo") or {}

    if not source or not destination or not transport_mode:
        raise ValidationError(
            "Route must include 'source', 'destination', and 'transport_mode'."
        )

    route_snapshot = build_route_snapshot(
        source=source,
        destination=destination,
        transport_mode=transport_mode,
        region_type=region_type,
        cargo=cargo,
        config=current_app.config,
        logger=current_app.logger,
    )

    simulation_result = simulate_disruption(
        route_snapshot=route_snapshot,
        disruption_type=disruption_type,
        baseline_risk=route_snapshot["risk"],
    )
    simulation_result["intelligence"] = build_supply_chain_intelligence(
        route_snapshot,
        simulation_result=simulation_result,
    )
    simulation_result["ai_prompt_text"] = format_simulation_for_llm(simulation_result)

    return success_response(
        message="Simulation completed successfully.",
        data=simulation_result,
    )
