TRANSPORT_PROFILES = {
    "road": {"reliability_score": 0.72, "base_cost_per_km": 1.0},
    "rail": {"reliability_score": 0.82, "base_cost_per_km": 0.7},
    "air": {"reliability_score": 0.9, "base_cost_per_km": 2.8},
    "waterways": {"reliability_score": 0.68, "base_cost_per_km": 0.55},
}


def enrich_route_with_transport_data(route_data, transport_mode):
    profile = TRANSPORT_PROFILES[transport_mode]
    distance_km = route_data["distance_meters"] / 1000

    enriched = dict(route_data)
    enriched["transport_profile"] = {
        "mode": transport_mode,
        "reliability_score": profile["reliability_score"],
        "estimated_cost": round(distance_km * profile["base_cost_per_km"], 2),
        "cost_currency": "USD",
    }

    if transport_mode != "road":
        multiplier = {
            "rail": {"duration": 1.2, "distance": 1.05},
            "air": {"duration": 0.45, "distance": 1.1},
            "waterways": {"duration": 1.6, "distance": 1.15},
        }[transport_mode]

        enriched["distance_meters"] = int(route_data["distance_meters"] * multiplier["distance"])
        enriched["duration_seconds"] = int(route_data["duration_seconds"] * multiplier["duration"])
        enriched["distance_text"] = f"{round(enriched['distance_meters'] / 1000, 1)} km (estimated)"
        enriched["duration_text"] = f"{round(enriched['duration_seconds'] / 3600, 1)} hours (estimated)"
        enriched["api_source"] = "google_distance_matrix_plus_modal_adjustment"

    return enriched
