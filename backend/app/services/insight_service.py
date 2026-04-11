from datetime import datetime

from app.config.risk_metadata import get_all_region_risk_metadata, get_region_risk_metadata
from app.services.routing_service import haversine_km


HUB_CITIES = {
    "Mumbai": [72.8777, 19.0760],
    "Delhi": [77.1025, 28.7041],
    "Chennai": [80.2707, 13.0827],
    "Kolkata": [88.3639, 22.5726],
    "Hyderabad": [78.4867, 17.3850],
}


PORT_CITIES = {"mumbai", "chennai", "kochi", "visakhapatnam", "kolkata", "surat"}


def _nearest_hub(destination_coordinates):
    nearest_city = None
    nearest_distance = None
    for city, coordinates in HUB_CITIES.items():
        distance = haversine_km(destination_coordinates, coordinates)
        if nearest_distance is None or distance < nearest_distance:
            nearest_city = city
            nearest_distance = distance
    return nearest_city, round(nearest_distance or 0, 1)


def _build_distribution_model(route_snapshot):
    route = route_snapshot["route"]
    region_type = route_snapshot["region_type"]
    destination_coordinates = route["destination_coordinates"]
    nearest_hub, hub_distance = _nearest_hub(destination_coordinates)

    if region_type == "tier_3":
        return {
            "model": "Hub-and-spoke distribution",
            "hub_city": nearest_hub,
            "description": (
                f"Stage primary movement through {nearest_hub} and use scheduled feeder dispatch "
                f"for the final {hub_distance} km regional leg."
            ),
        }
    if region_type == "sez":
        return {
            "model": "Controlled corridor dispatch",
            "hub_city": nearest_hub,
            "description": (
                "Use time-windowed gate entry, pre-cleared documentation, and controlled outbound dispatch "
                "to reduce SEZ exit variability."
            ),
        }
    return {
        "model": "Direct multi-modal corridor",
        "hub_city": nearest_hub,
        "description": (
            f"Primary movement can run direct, with {nearest_hub} retained as contingency hub "
            "for rerouting or buffer storage."
        ),
    }


def _build_route_stages(route_snapshot):
    route = route_snapshot["route"]
    region_type = route_snapshot["region_type"]
    distribution_model = _build_distribution_model(route_snapshot)

    stages = [
        {
            "stage": "Origin dispatch",
            "detail": f"Release cargo from {route['source']} using {route['transport_profile']['label']} primary leg.",
        },
        {
            "stage": "Line-haul corridor",
            "detail": f"Execute {route['distance_text']} movement with active risk monitoring across trunk corridor.",
        },
        {
            "stage": "Transfer node",
            "detail": (
                f"Use {distribution_model['hub_city']} as operational fallback node for buffer stock, transshipment, or mode switch."
            ),
        },
        {
            "stage": "Last-mile completion",
            "detail": (
                "Apply additional dispatch controls for final-mile delivery."
                if region_type == "tier_3"
                else "Close route with standard handoff and proof-of-delivery controls."
            ),
        },
    ]
    return stages


def build_route_decision_support(route_snapshot):
    route = route_snapshot["route"]
    risk = route_snapshot["risk"]
    weather = route_snapshot["weather"]
    region_type = route_snapshot["region_type"]
    suggested_mode = route_snapshot["suggested_transport_mode"]
    distribution_model = _build_distribution_model(route_snapshot)

    source_city = route["source"].strip().lower()
    destination_city = route["destination"].strip().lower()
    corridor_has_port_exposure = source_city in PORT_CITIES or destination_city in PORT_CITIES

    if region_type == "tier_3":
        last_mile_strategy = (
            f"Use {distribution_model['hub_city']} as feeder hub, release smaller dispatch batches, "
            "and maintain extra delivery buffer for rural/low-redundancy nodes."
        )
    elif region_type == "sez":
        last_mile_strategy = (
            "Coordinate gate slots, customs documentation, and bonded transfer timing before final dispatch."
        )
    else:
        last_mile_strategy = (
            "Maintain direct dispatch with contingency stock positioned at the nearest metro or regional hub."
        )

    if region_type == "sez" or corridor_has_port_exposure:
        sez_strategy = (
            "Monitor compliance and port-adjacent congestion windows; prioritize off-peak dispatch and pre-file documentation."
        )
    else:
        sez_strategy = (
            "No direct SEZ dependency on this route, but retain customs-ready paperwork if cargo may pass through controlled trade zones."
        )

    action_items = [
        "Validate weather and congestion exposure before truck release.",
        f"Keep {distribution_model['hub_city']} available as contingency node.",
        suggested_mode["rationale"],
    ]
    if risk["overall_risk"] == "High":
        action_items.append("Pre-position safety stock and extend customer ETA buffer.")
    if weather.get("rainfall_mm", 0) >= 10:
        action_items.append("Increase waterproof handling and route monitoring during rainfall window.")

    executive_summary = (
        f"{route['source']} to {route['destination']} is operating under {risk['overall_risk'].lower()} risk. "
        f"{distribution_model['model']} is recommended, and {suggested_mode['label']} is the preferred mode "
        "when resilience is prioritized over default dispatch."
    )

    return {
        "executive_summary": executive_summary,
        "distribution_model": distribution_model,
        "last_mile_strategy": last_mile_strategy,
        "sez_strategy": sez_strategy,
        "route_stages": _build_route_stages(route_snapshot),
        "action_items": action_items,
        "llm_prompt_text": format_route_for_llm(route_snapshot, executive_summary, action_items),
    }


def build_supply_chain_intelligence(route_snapshot, simulation_result=None):
    route = route_snapshot["route"]
    weather = route_snapshot["weather"]
    risk = route_snapshot["risk"]
    region_type = route_snapshot["region_type"]
    suggested_mode = route_snapshot["suggested_transport_mode"]

    score_pct = risk["weighted_score_pct"]
    if simulation_result or score_pct >= 70:
        system_status = "critical"
        system_label = "Critical"
    elif score_pct >= 40:
        system_status = "warning"
        system_label = "Risky"
    else:
        system_status = "normal"
        system_label = "Normal"

    alerts = []
    if weather.get("rainfall_mm", 0) >= 10 or weather["condition"] in {"rain", "thunderstorm"}:
        alerts.append("Heavy rainfall risk affecting corridor operations")
    if route.get("congestion_index", 0) >= 0.6:
        alerts.append("Congestion pressure elevated near route nodes")
    if region_type == "tier_3":
        alerts.append("Tier-3 delay risk high due to last-mile fragility")
    if region_type == "sez":
        alerts.append("SEZ gate processing stable but monitor exit window compliance")
    if suggested_mode["mode"] != route["transport_mode"]:
        alerts.append(f"Operational recommendation: shift from {route['transport_mode']} to {suggested_mode['mode']}")
    if simulation_result:
        alerts.append(f"Scenario active: {simulation_result['requested_disruption_label']} disruption modeled")
    if not alerts:
        alerts.append("No major active alerts. Corridor conditions within expected range.")

    weak_points = []
    if region_type == "tier_3":
        weak_points.append("Delay expected at last-mile delivery node in Tier-3 region")
    if route.get("congestion_index", 0) >= 0.55:
        weak_points.append("Urban transfer node likely to create dispatch queue buildup")
    if weather["weather_risk_score"] >= 0.45:
        weak_points.append("Weather-sensitive route segment requires dispatch monitoring")
    if route["transport_profile"]["reliability_score_pct"] <= 72:
        weak_points.append("Current transport mode shows lower reliability under disruption conditions")
    if not weak_points:
        weak_points.append("No critical fault points detected on the selected route")

    return {
        "system_status": system_status,
        "system_label": system_label,
        "alerts": alerts,
        "weak_points": weak_points,
    }


def build_india_context(route_snapshot):
    region_type = route_snapshot["region_type"]
    selected_region = get_region_risk_metadata(region_type)
    all_regions = get_all_region_risk_metadata()
    month = datetime.utcnow().month

    if month in {6, 7, 8, 9}:
        seasonal_note = "Monsoon window active: review rainfall and road resilience before dispatch."
    elif month in {10, 11}:
        seasonal_note = "Festival and post-monsoon volatility: allow gate and labor buffers."
    elif month in {12, 1, 2}:
        seasonal_note = "Winter visibility risk may affect northern corridors and air movements."
    else:
        seasonal_note = "Pre-monsoon planning window: use this period for bulk movement and inventory repositioning."

    region_cards = []
    for code, metadata in all_regions.items():
        region_cards.append(
            {
                "code": code,
                "label": code.replace("_", "-").upper(),
                "connectivity_label": metadata["connectivity_label"],
                "description": metadata["description"],
                "infrastructure_quality": metadata["infrastructure_quality"],
                "last_mile_profile": metadata["last_mile_profile"],
                "sez_exit_delay_risk": metadata["sez_exit_delay_risk"],
                "recommended_buffer_hours": metadata["recommended_buffer_hours"],
                "is_active": code == region_type,
            }
        )

    return {
        "active_region": region_type,
        "selected_region_summary": {
            "connectivity_label": selected_region["connectivity_label"],
            "description": selected_region["description"],
            "infrastructure_quality": selected_region["infrastructure_quality"],
            "last_mile_profile": selected_region["last_mile_profile"],
            "sez_exit_delay_risk": selected_region["sez_exit_delay_risk"],
            "recommended_buffer_hours": selected_region["recommended_buffer_hours"],
        },
        "seasonal_note": seasonal_note,
        "region_cards": region_cards,
    }


def format_route_for_llm(route_snapshot, executive_summary, action_items):
    route = route_snapshot["route"]
    risk = route_snapshot["risk"]
    weather = route_snapshot["weather"]
    suggested = route_snapshot["suggested_transport_mode"]

    return (
        "Supply chain route decision brief:\n"
        f"- Corridor: {route['source']} to {route['destination']}\n"
        f"- Selected mode: {route['transport_profile']['label']}\n"
        f"- Estimated time: {route['duration_text']}\n"
        f"- Estimated cost INR: {route['estimated_cost_inr']}\n"
        f"- Risk level: {risk['overall_risk']}\n"
        f"- Weather condition: {weather['condition']}\n"
        f"- Suggested mode: {suggested['label']}\n"
        f"- Executive summary: {executive_summary}\n"
        f"- Action items: {'; '.join(action_items)}\n"
        "Generate mitigation options, final dispatch advice, and executive-ready planning notes."
    )


def format_simulation_for_llm(simulation_output):
    before = simulation_output["before"]
    after = simulation_output["after"]

    return (
        "Supply chain disruption analysis:\n"
        f"- Disruption type: {simulation_output['disruption_type']}\n"
        f"- Requested scenario label: {simulation_output['requested_disruption_label']}\n"
        f"- Baseline duration (seconds): {before['duration_seconds']}\n"
        f"- Simulated duration (seconds): {after['duration_seconds']}\n"
        f"- Baseline cost INR: {before['estimated_cost_inr']}\n"
        f"- Simulated cost INR: {after['estimated_cost_inr']}\n"
        f"- Risk transition: {simulation_output['risk_change']}\n"
        f"- Delay percentage: {simulation_output['delay_percentage']}%\n"
        f"- Cost increase percentage: {simulation_output['cost_increase_percentage']}%\n"
        f"- Baseline recommendation: {before['risk']['recommendation']}\n"
        f"- Simulated recommendation: {after['risk']['recommendation']}\n"
        f"- Scenario best mode: {simulation_output['best_transport_mode']['label']}\n"
        f"- Mitigation actions: {'; '.join(simulation_output['mitigation_actions'])}\n"
        "Generate mitigation options, preferred transport alternatives, and executive-ready action items."
    )
