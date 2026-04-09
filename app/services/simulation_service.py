from app.services.risk_service import calculate_risk
from app.utils.errors import ValidationError


DISRUPTION_PROFILES = {
    "monsoon": {"time_multiplier": 1.35, "cost_multiplier": 1.18, "weather_override": 0.82},
    "strike": {"time_multiplier": 1.5, "cost_multiplier": 1.3, "weather_override": None},
    "congestion": {"time_multiplier": 1.25, "cost_multiplier": 1.1, "weather_override": None},
}


def simulate_disruption(route_snapshot, disruption_type, baseline_risk):
    profile = DISRUPTION_PROFILES.get(disruption_type.lower())
    if not profile:
        supported = ", ".join(DISRUPTION_PROFILES.keys())
        raise ValidationError(
            f"Unsupported disruption_type '{disruption_type}'. Use: {supported}."
        )

    route_data = route_snapshot["route"]
    weather = dict(route_snapshot["weather"])
    region_type = route_snapshot["region_type"]

    before = {
        "distance_meters": route_data["distance_meters"],
        "duration_seconds": route_data["duration_seconds"],
        "estimated_cost": route_data["transport_profile"]["estimated_cost"],
        "risk": baseline_risk,
    }

    if profile["weather_override"] is not None:
        weather["weather_risk_score"] = profile["weather_override"]
        weather["weather_risk_label"] = "high_risk"
        weather["condition"] = disruption_type.lower()

    after_route = dict(route_data)
    after_route["duration_seconds"] = int(route_data["duration_seconds"] * profile["time_multiplier"])
    after_route["transport_profile"] = dict(route_data["transport_profile"])
    after_route["transport_profile"]["estimated_cost"] = round(
        route_data["transport_profile"]["estimated_cost"] * profile["cost_multiplier"],
        2,
    )

    after_risk = calculate_risk(after_route, weather, region_type)
    delay_percentage = round((profile["time_multiplier"] - 1) * 100, 2)
    cost_increase_percentage = round((profile["cost_multiplier"] - 1) * 100, 2)

    return {
        "disruption_type": disruption_type.lower(),
        "before": before,
        "after": {
            "distance_meters": after_route["distance_meters"],
            "duration_seconds": after_route["duration_seconds"],
            "estimated_cost": after_route["transport_profile"]["estimated_cost"],
            "risk": after_risk,
        },
        "risk_change": f"{baseline_risk['overall_risk']} -> {after_risk['overall_risk']}",
        "delay_percentage": delay_percentage,
        "cost_increase_percentage": cost_increase_percentage,
        "summary": _build_summary(disruption_type, delay_percentage, cost_increase_percentage),
    }


def _build_summary(disruption_type, delay_percentage, cost_increase_percentage):
    return (
        f"{disruption_type.title()} scenario applied. "
        f"Transit time increases by {delay_percentage}% and cost rises by {cost_increase_percentage}%."
    )
