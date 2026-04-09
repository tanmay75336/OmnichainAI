from app.config.risk_metadata import get_region_risk_metadata


RISK_WEIGHTS = {
    "weather": 0.4,
    "infrastructure": 0.35,
    "transport": 0.25,
}


RISK_LEVELS = (
    (0.0, 0.35, "Low"),
    (0.35, 0.65, "Medium"),
    (0.65, 1.1, "High"),
)


class RuleBasedRiskModel:
    """A lightweight scorer that can later be swapped for an ML-backed model."""

    def score(self, weather_score, infrastructure_score, transport_score):
        return (
            weather_score * RISK_WEIGHTS["weather"]
            + infrastructure_score * RISK_WEIGHTS["infrastructure"]
            + transport_score * RISK_WEIGHTS["transport"]
        )


def _transport_risk_score(route_data):
    reliability_score = route_data["transport_profile"]["reliability_score"]
    return round(1 - reliability_score, 2)


def _risk_label(score):
    for lower, upper, label in RISK_LEVELS:
        if lower <= score < upper:
            return label
    return "High"


def calculate_risk(route_data, weather, region_type, model=None):
    metadata = get_region_risk_metadata(region_type)
    infrastructure_score = metadata["infrastructure_risk_score"]
    weather_score = weather["weather_risk_score"]
    transport_score = _transport_risk_score(route_data)

    active_model = model or RuleBasedRiskModel()
    weighted_score = round(
        active_model.score(weather_score, infrastructure_score, transport_score),
        2,
    )
    overall_risk = _risk_label(weighted_score)

    return {
        "overall_risk": overall_risk,
        "weighted_score": weighted_score,
        "factors": {
            "weather": {
                "condition": weather["condition"],
                "score": weather_score,
                "impact": weather["weather_risk_label"],
            },
            "infrastructure": {
                "region_type": region_type,
                "score": infrastructure_score,
                "impact": metadata["description"],
            },
            "transport": {
                "mode": route_data["transport_mode"],
                "score": transport_score,
                "impact": f"Reliability score {route_data['transport_profile']['reliability_score']}",
            },
        },
        "recommendation": _build_recommendation(overall_risk, route_data["transport_mode"]),
    }


def _build_recommendation(overall_risk, transport_mode):
    if overall_risk == "High":
        return f"High disruption exposure detected. Consider backup capacity and alternate to {transport_mode} where feasible."
    if overall_risk == "Medium":
        return "Moderate risk detected. Track weather and node congestion before dispatch."
    return "Route conditions look stable. Proceed with routine monitoring."
