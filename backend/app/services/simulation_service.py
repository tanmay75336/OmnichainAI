from app.services.risk_service import calculate_risk
from app.services.transport_service import (
    build_modal_comparison,
    choose_recommended_mode,
    enrich_route_with_transport_data,
)
from app.utils.errors import ValidationError


DISRUPTION_ALIASES = {
    "heavy rainfall in a region": ("heavy_rainfall", None),
    "heavy_rainfall": ("heavy_rainfall", None),
    "monsoon": ("heavy_rainfall", "Monsoon modeled using heavy rainfall disruption profile."),
    "flood": ("heavy_rainfall", "Flood modeled using heavy rainfall disruption profile."),
    "port congestion or delays": ("port_congestion", None),
    "port_congestion": ("port_congestion", None),
    "congestion": ("port_congestion", "Generic congestion modeled using port congestion profile."),
    "increased demand in tier-2 cities": ("demand_spike", None),
    "tier2 demand": ("demand_spike", None),
    "demand_spike": ("demand_spike", None),
    "route blockage due to regulatory or operational issues": ("route_blockage", None),
    "route_blockage": ("route_blockage", None),
    "strike": ("route_blockage", "Strike modeled using route blockage disruption profile."),
    "political crisis": ("route_blockage", "Political crisis modeled using route blockage disruption profile."),
    "political_crisis": ("route_blockage", "Political crisis modeled using route blockage disruption profile."),
    "govt holiday": ("demand_spike", "Government holiday modeled using demand and capacity profile."),
    "government holiday": ("demand_spike", "Government holiday modeled using demand and capacity profile."),
}


DISRUPTION_PROFILES = {
    "heavy_rainfall": {
        "time_multiplier": 1.38,
        "cost_multiplier": 1.16,
        "weather_override": 0.86,
        "weather_label": "high_risk",
        "congestion_increment": 0.09,
        "reliability_penalty": 0.07,
    },
    "port_congestion": {
        "time_multiplier": 1.42,
        "cost_multiplier": 1.19,
        "weather_override": None,
        "weather_label": None,
        "congestion_increment": 0.18,
        "reliability_penalty": 0.08,
    },
    "demand_spike": {
        "time_multiplier": 1.2,
        "cost_multiplier": 1.15,
        "weather_override": None,
        "weather_label": None,
        "congestion_increment": 0.11,
        "reliability_penalty": 0.05,
    },
    "route_blockage": {
        "time_multiplier": 1.58,
        "cost_multiplier": 1.27,
        "weather_override": None,
        "weather_label": None,
        "congestion_increment": 0.14,
        "reliability_penalty": 0.12,
    },
}


def _normalize_disruption_type(disruption_type):
    normalized = disruption_type.strip().lower()
    alias = DISRUPTION_ALIASES.get(normalized)
    if not alias:
        supported = ", ".join(sorted(DISRUPTION_ALIASES.keys()))
        raise ValidationError(
            f"Unsupported disruption_type '{disruption_type}'. Use: {supported}."
        )
    return alias


def _format_duration_text(duration_seconds):
    total_minutes = max(1, round(duration_seconds / 60))
    if total_minutes < 60:
        return f"{total_minutes} mins"

    total_hours = round(duration_seconds / 3600, 1)
    if float(total_hours).is_integer():
        whole_hours = int(total_hours)
        return f"{whole_hours} {'hour' if whole_hours == 1 else 'hours'}"

    return f"{total_hours} hours"


def _build_mitigation_actions(route_snapshot, scenario_mode):
    route = route_snapshot["route"]
    region_type = route_snapshot["region_type"]
    actions = [
        f"Shift contingency planning toward {scenario_mode['label']} if primary dispatch degrades further.",
        "Review ETA buffer and notify downstream nodes before dispatch commitment.",
        "Track corridor congestion and weather every 2-4 hours during execution.",
    ]
    if region_type == "tier_3":
        actions.append("Use hub-based feeder dispatch to protect the last-mile leg in Tier-3 delivery zones.")
    if region_type == "sez":
        actions.append("Lock gate slot timing and pre-clear compliance documents to avoid SEZ exit slippage.")
    return actions


def simulate_disruption(route_snapshot, disruption_type, baseline_risk):
    normalized_type, note = _normalize_disruption_type(disruption_type)
    profile = DISRUPTION_PROFILES[normalized_type]

    base_route = route_snapshot["base_route"]
    route_data = route_snapshot["route"]
    weather = dict(route_snapshot["weather"])
    region_type = route_snapshot["region_type"]

    before = {
        "distance_meters": route_data["distance_meters"],
        "distance_text": route_data["distance_text"],
        "duration_seconds": route_data["duration_seconds"],
        "duration_text": route_data["duration_text"],
        "estimated_cost_inr": route_data["estimated_cost_inr"],
        "reliability_score_pct": route_data["transport_profile"]["reliability_score_pct"],
        "risk": baseline_risk,
    }

    if profile["weather_override"] is not None:
        weather["weather_risk_score"] = profile["weather_override"]
        weather["weather_risk_label"] = profile["weather_label"]
        weather["condition"] = normalized_type.lower()
        weather["rainfall_mm"] = max(weather.get("rainfall_mm", 0), 30)

    after_route = dict(route_data)
    after_route["duration_seconds"] = int(route_data["duration_seconds"] * profile["time_multiplier"])
    after_route["duration_hours"] = round(after_route["duration_seconds"] / 3600, 2)
    after_route["duration_text"] = _format_duration_text(after_route["duration_seconds"])
    after_route["estimated_cost_inr"] = round(
        route_data["estimated_cost_inr"] * profile["cost_multiplier"],
        2,
    )
    after_route["transport_profile"] = dict(route_data["transport_profile"])
    after_route["transport_profile"]["estimated_cost"] = after_route["estimated_cost_inr"]
    after_route["transport_profile"]["estimated_cost_inr"] = after_route["estimated_cost_inr"]
    after_route["transport_profile"]["reliability_score"] = max(
        0.4,
        round(route_data["transport_profile"]["reliability_score"] - profile["reliability_penalty"], 2),
    )
    after_route["transport_profile"]["reliability_score_pct"] = int(
        round(after_route["transport_profile"]["reliability_score"] * 100)
    )
    after_route["reliability_score_pct"] = after_route["transport_profile"]["reliability_score_pct"]
    after_route["congestion_index"] = min(
        1.0,
        round(route_data.get("congestion_index", 0.4) + profile["congestion_increment"], 2),
    )

    after_risk = calculate_risk(after_route, weather, region_type)
    scenario_options = []
    scenario_risks = {}
    for option in build_modal_comparison(
        base_route,
        region_type,
        weather,
        after_route["congestion_index"],
    ):
        option_route = enrich_route_with_transport_data(
            base_route,
            option["mode"],
            region_type,
            weather,
            after_route["congestion_index"],
        )
        option_risk = calculate_risk(option_route, weather, region_type)
        scenario_risks[option["mode"]] = option_risk
        scenario_options.append(
            {
                **option,
                "overall_risk": option_risk["overall_risk"],
                "weighted_score_pct": option_risk["weighted_score_pct"],
            }
        )

    best_transport_mode = choose_recommended_mode(
        scenario_options,
        scenario_risks,
        route_data["transport_mode"],
    )
    for option in scenario_options:
        option["is_recommended"] = option["mode"] == best_transport_mode["mode"]

    delay_percentage = round((profile["time_multiplier"] - 1) * 100, 2)
    cost_increase_percentage = round((profile["cost_multiplier"] - 1) * 100, 2)
    mitigation_actions = _build_mitigation_actions(route_snapshot, best_transport_mode)

    return {
        "disruption_type": normalized_type,
        "requested_disruption_label": disruption_type,
        "scenario_modeling_note": note,
        "before": before,
        "after": {
            "distance_meters": after_route["distance_meters"],
            "distance_text": after_route["distance_text"],
            "duration_seconds": after_route["duration_seconds"],
            "duration_text": after_route["duration_text"],
            "estimated_cost_inr": after_route["estimated_cost_inr"],
            "reliability_score_pct": after_route["reliability_score_pct"],
            "risk": after_risk,
        },
        "risk_change": f"{baseline_risk['overall_risk']} -> {after_risk['overall_risk']}",
        "delay_percentage": delay_percentage,
        "cost_increase_percentage": cost_increase_percentage,
        "summary": _build_summary(normalized_type, delay_percentage, cost_increase_percentage),
        "recommendation": after_risk["recommendation"],
        "best_transport_mode": best_transport_mode,
        "scenario_modal_options": scenario_options,
        "mitigation_actions": mitigation_actions,
    }


def _build_summary(disruption_type, delay_percentage, cost_increase_percentage):
    label = disruption_type.replace("_", " ").title()
    return (
        f"{label} scenario applied. "
        f"Transit time increases by {delay_percentage}% and trip cost rises by {cost_increase_percentage}%."
    )
