from app.config.risk_metadata import get_region_risk_metadata


RISK_WEIGHTS = {
    "weather": 0.32,
    "infrastructure": 0.28,
    "transport": 0.24,
    "congestion": 0.16,
}


RISK_LEVELS = (
    (0.0, 0.35, "Low"),
    (0.35, 0.65, "Medium"),
    (0.65, 1.1, "High"),
)


NODE_CONGESTION = {
    "mumbai": 0.68,
    "chennai": 0.61,
    "kolkata": 0.6,
    "delhi": 0.66,
    "new delhi": 0.66,
    "bengaluru": 0.64,
    "bangalore": 0.64,
    "hyderabad": 0.52,
    "ahmedabad": 0.48,
    "visakhapatnam": 0.54,
    "kochi": 0.5,
}


REGION_CONGESTION = {
    "tier_2": 0.38,
    "tier_3": 0.46,
    "sez": 0.28,
}


class RuleBasedRiskModel:
    """A lightweight scorer that can later be swapped for an ML-backed model."""

    def score(self, weather_score, infrastructure_score, transport_score, congestion_score):
        return (
            weather_score * RISK_WEIGHTS["weather"]
            + infrastructure_score * RISK_WEIGHTS["infrastructure"]
            + transport_score * RISK_WEIGHTS["transport"]
            + congestion_score * RISK_WEIGHTS["congestion"]
        )


def _transport_risk_score(route_data):
    reliability_score = route_data["transport_profile"]["reliability_score"]
    return round(1 - reliability_score, 2)


def _risk_label(score):
    for lower, upper, label in RISK_LEVELS:
        if lower <= score < upper:
            return label
    return "High"


def derive_congestion_index(route_data, weather, region_type):
    destination_key = route_data["destination"].strip().lower()
    source_key = route_data["source"].strip().lower()
    node_pressure = max(
        NODE_CONGESTION.get(destination_key, 0.35),
        NODE_CONGESTION.get(source_key, 0.32),
    )
    region_pressure = REGION_CONGESTION.get(region_type, 0.38)
    weather_pressure = weather.get("weather_risk_score", 0) * 0.35
    distance_pressure = min(route_data["distance_meters"] / 2_000_000, 0.18)

    return round(
        min(1.0, node_pressure * 0.45 + region_pressure * 0.35 + weather_pressure + distance_pressure),
        2,
    )


def calculate_risk(route_data, weather, region_type, model=None):
    metadata = get_region_risk_metadata(region_type)
    infrastructure_score = metadata["infrastructure_risk_score"]
    weather_score = weather["weather_risk_score"]
    transport_score = _transport_risk_score(route_data)
    congestion_score = route_data.get("congestion_index")
    if congestion_score is None:
        congestion_score = derive_congestion_index(route_data, weather, region_type)

    active_model = model or RuleBasedRiskModel()
    weighted_score = round(
        active_model.score(
            weather_score,
            infrastructure_score,
            transport_score,
            congestion_score,
        ),
        2,
    )
    weighted_score_pct = int(round(weighted_score * 100))
    overall_risk = _risk_label(weighted_score)

    return {
        "overall_risk": overall_risk,
        "weighted_score": weighted_score,
        "weighted_score_pct": weighted_score_pct,
        "congestion_index": congestion_score,
        "factors": {
            "weather": {
                "condition": weather["condition"],
                "score": weather_score,
                "impact": weather["weather_risk_label"],
                "rainfall_mm": weather.get("rainfall_mm"),
            },
            "infrastructure": {
                "region_type": region_type,
                "score": infrastructure_score,
                "impact": metadata["description"],
                "connectivity_label": metadata.get("connectivity_label"),
            },
            "transport": {
                "mode": route_data["transport_mode"],
                "score": transport_score,
                "impact": f"Reliability score {route_data['transport_profile']['reliability_score_pct']}/100",
            },
            "congestion": {
                "score": congestion_score,
                "impact": "Node congestion, corridor pressure, and distance exposure.",
            },
        },
        "recommendation": _build_recommendation(overall_risk, route_data["transport_mode"], congestion_score),
    }


def _build_recommendation(overall_risk, transport_mode, congestion_score):
    if overall_risk == "High":
        return (
            f"High disruption exposure detected on the current {transport_mode} plan. "
            "Use backup capacity, extend dispatch buffer, and evaluate a lower-risk mode."
        )
    if overall_risk == "Medium":
        if congestion_score >= 0.6:
            return "Moderate risk with elevated congestion. Dispatch with monitoring and consider off-peak release windows."
        return "Moderate risk detected. Track weather and node congestion before dispatch."
    return "Route conditions look stable. Proceed with routine monitoring and standard dispatch controls."
