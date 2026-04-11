from app.services.routing_service import haversine_km


TRANSPORT_PROFILES = {
    "road": {
        "label": "Road",
        "base_reliability": 0.78,
        "speed_kmph": 42,
        "cost_per_km_inr": 32,
        "fixed_cost_inr": 800,
        "distance_factor": 1.0,
    },
    "rail": {
        "label": "Rail",
        "base_reliability": 0.84,
        "speed_kmph": 55,
        "cost_per_km_inr": 18,
        "fixed_cost_inr": 1800,
        "distance_factor": 0.96,
        "handling_hours": 4.0,
    },
    "air": {
        "label": "Air",
        "base_reliability": 0.88,
        "speed_kmph": 620,
        "cost_per_km_inr": 118,
        "fixed_cost_inr": 9500,
        "distance_factor": 1.05,
        "handling_hours": 5.5,
    },
    "waterways": {
        "label": "Waterways",
        "base_reliability": 0.7,
        "speed_kmph": 22,
        "cost_per_km_inr": 12,
        "fixed_cost_inr": 2600,
        "distance_factor": 1.22,
        "handling_hours": 10.0,
    },
}


REGION_RELIABILITY_ADJUSTMENT = {
    "tier_2": -0.03,
    "tier_3": -0.09,
    "sez": 0.04,
}


WEATHER_SENSITIVITY = {
    "road": 0.12,
    "rail": 0.07,
    "air": 0.1,
    "waterways": 0.16,
}


MODE_CONGESTION_SENSITIVITY = {
    "road": 0.16,
    "rail": 0.08,
    "air": 0.06,
    "waterways": 0.1,
}


def _format_distance_text(distance_meters):
    distance_km = round(distance_meters / 1000, 1)
    if float(distance_km).is_integer():
        distance_km = int(distance_km)
    return f"{distance_km} km"


def _format_duration_text(duration_seconds):
    total_minutes = max(1, round(duration_seconds / 60))
    if total_minutes < 60:
        return f"{total_minutes} mins"

    total_hours = round(duration_seconds / 3600, 1)
    if float(total_hours).is_integer():
        whole_hours = int(total_hours)
        return f"{whole_hours} {'hour' if whole_hours == 1 else 'hours'}"

    return f"{total_hours} hours"


def _normalize_reliability(mode, region_type, weather_score, congestion_index):
    profile = TRANSPORT_PROFILES[mode]
    base_reliability = profile["base_reliability"]
    base_reliability += REGION_RELIABILITY_ADJUSTMENT.get(region_type, 0)
    base_reliability -= weather_score * WEATHER_SENSITIVITY[mode]
    base_reliability -= congestion_index * MODE_CONGESTION_SENSITIVITY[mode]
    return max(0.45, min(0.96, round(base_reliability, 2)))


def _mode_distance_km(base_route_data, mode):
    road_distance_km = base_route_data["distance_meters"] / 1000
    source_coordinates = base_route_data["source_coordinates"]
    destination_coordinates = base_route_data["destination_coordinates"]
    geodesic_distance_km = haversine_km(source_coordinates, destination_coordinates)

    if mode == "road":
        return road_distance_km
    if mode == "rail":
        return max(road_distance_km * TRANSPORT_PROFILES[mode]["distance_factor"], geodesic_distance_km * 1.05)
    if mode == "air":
        return max(geodesic_distance_km * TRANSPORT_PROFILES[mode]["distance_factor"], 180)
    return max(road_distance_km * TRANSPORT_PROFILES[mode]["distance_factor"], geodesic_distance_km * 1.12)


def enrich_route_with_transport_data(base_route_data, transport_mode, region_type, weather, congestion_index):
    profile = TRANSPORT_PROFILES[transport_mode]
    distance_km = round(_mode_distance_km(base_route_data, transport_mode), 1)
    travel_hours = distance_km / profile["speed_kmph"]
    handling_hours = profile.get("handling_hours", 0.0)
    duration_hours = travel_hours + handling_hours
    duration_seconds = int(round(duration_hours * 3600))
    distance_meters = int(round(distance_km * 1000))
    reliability_score = _normalize_reliability(
        transport_mode,
        region_type,
        weather.get("weather_risk_score", 0),
        congestion_index,
    )
    estimated_cost_inr = round(
        (distance_km * profile["cost_per_km_inr"]) + profile["fixed_cost_inr"],
        2,
    )

    enriched = dict(base_route_data)
    enriched["transport_mode"] = transport_mode
    enriched["distance_meters"] = distance_meters
    enriched["distance_km"] = distance_km
    enriched["distance_text"] = _format_distance_text(distance_meters)
    enriched["duration_seconds"] = duration_seconds
    enriched["duration_hours"] = round(duration_hours, 2)
    enriched["duration_text"] = _format_duration_text(duration_seconds)
    enriched["estimated_cost_inr"] = estimated_cost_inr
    enriched["reliability_score_pct"] = int(round(reliability_score * 100))
    enriched["congestion_index"] = round(congestion_index, 2)
    enriched["api_source"] = (
        base_route_data["api_source"]
        if transport_mode == "road"
        else f"{base_route_data['api_source']}_modal_estimate"
    )
    enriched["transport_profile"] = {
        "mode": transport_mode,
        "label": profile["label"],
        "reliability_score": reliability_score,
        "reliability_score_pct": int(round(reliability_score * 100)),
        "estimated_cost": estimated_cost_inr,
        "estimated_cost_inr": estimated_cost_inr,
        "cost_currency": "INR",
        "avg_speed_kmph": profile["speed_kmph"],
    }

    return enriched


def build_modal_comparison(base_route_data, region_type, weather, congestion_index):
    options = []
    for mode in TRANSPORT_PROFILES:
        option_route = enrich_route_with_transport_data(
            base_route_data,
            mode,
            region_type,
            weather,
            congestion_index,
        )
        options.append(
            {
                "mode": mode,
                "label": TRANSPORT_PROFILES[mode]["label"],
                "distance_km": option_route["distance_km"],
                "distance_text": option_route["distance_text"],
                "duration_hours": option_route["duration_hours"],
                "duration_text": option_route["duration_text"],
                "estimated_cost_inr": option_route["estimated_cost_inr"],
                "reliability_score_pct": option_route["reliability_score_pct"],
            }
        )
    return options


def choose_recommended_mode(modal_options, risk_lookup, current_mode):
    scored_options = []
    for option in modal_options:
        mode = option["mode"]
        risk_value = risk_lookup.get(mode, {}).get("weighted_score", 1)
        time_penalty = min(option["duration_hours"] / 40, 1)
        cost_penalty = min(option["estimated_cost_inr"] / 100000, 1)
        reliability_bonus = option["reliability_score_pct"] / 100
        composite = round(
            (risk_value * 0.45) + (time_penalty * 0.2) + (cost_penalty * 0.15) - (reliability_bonus * 0.2),
            3,
        )
        scored_options.append({**option, "composite_score": composite})

    scored_options.sort(key=lambda item: item["composite_score"])
    best_option = scored_options[0]
    rationale = (
        "Current selection remains operationally sound."
        if best_option["mode"] == current_mode
        else f"Switch to {best_option['label']} to improve resilience under current risk conditions."
    )
    return {
        "mode": best_option["mode"],
        "label": best_option["label"],
        "composite_score": best_option["composite_score"],
        "rationale": rationale,
    }
