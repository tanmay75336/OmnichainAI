from app.services.gemini_service import generate_json, gemini_is_configured


AGENCY_PROFILES = {
    "road": [
        {"name": "Delhivery Surface", "multiplier": 1.0, "flat_markup_inr": 0, "serviceability": "Strong urban and tier-2 coverage"},
        {"name": "DTDC Cargo", "multiplier": 1.06, "flat_markup_inr": 120, "serviceability": "Balanced national surface network"},
        {"name": "Gati Express", "multiplier": 1.11, "flat_markup_inr": 220, "serviceability": "FTL and part-truck corridor specialist"},
        {"name": "Blue Dart Surface", "multiplier": 1.18, "flat_markup_inr": 260, "serviceability": "Premium SLA-focused surface movement"},
    ],
    "rail": [
        {"name": "CONCOR Rail Cargo", "multiplier": 1.0, "flat_markup_inr": 0, "serviceability": "Containerized long-haul rail corridors"},
        {"name": "Safexpress Rail", "multiplier": 1.08, "flat_markup_inr": 240, "serviceability": "Integrated rail plus road last-mile operations"},
        {"name": "Gati Rail Logistics", "multiplier": 1.12, "flat_markup_inr": 320, "serviceability": "Scheduled rail cargo consolidation"},
    ],
    "air": [
        {"name": "Blue Dart Air", "multiplier": 1.0, "flat_markup_inr": 0, "serviceability": "Time-critical express air cargo"},
        {"name": "IndiGo CarGo", "multiplier": 0.96, "flat_markup_inr": 350, "serviceability": "Domestic air belly-capacity network"},
        {"name": "Air India Cargo", "multiplier": 1.08, "flat_markup_inr": 420, "serviceability": "Airport-to-airport scheduled cargo movement"},
    ],
    "waterways": [
        {"name": "Shreyas Coastal", "multiplier": 1.0, "flat_markup_inr": 0, "serviceability": "Coastal container and feeder legs"},
        {"name": "Inland Barge Logistics", "multiplier": 0.94, "flat_markup_inr": 300, "serviceability": "Inland waterway bulk movement"},
        {"name": "PortLink Multimodal", "multiplier": 1.1, "flat_markup_inr": 450, "serviceability": "Port-led multimodal consolidation"},
    ],
}


MODE_COST_FACTORS = {
    "road": {
        "base_linehaul_per_km": 11.8,
        "weight_rate_inr_per_kg": 2.6,
        "piece_fee_inr": 18,
        "booking_fee_inr": 240,
        "fuel_surcharge_pct": 0.13,
        "gst_pct": 0.05,
        "toll_per_km": 1.9,
        "handling_fee_inr": 160,
        "fuel_efficiency_kmpl": 8.8,
        "fuel_price_inr_per_l": 92,
    },
    "rail": {
        "base_linehaul_per_km": 8.2,
        "weight_rate_inr_per_kg": 1.7,
        "piece_fee_inr": 14,
        "booking_fee_inr": 520,
        "fuel_surcharge_pct": 0.07,
        "gst_pct": 0.05,
        "toll_per_km": 0.4,
        "handling_fee_inr": 320,
        "fuel_efficiency_kmpl": 18.0,
        "fuel_price_inr_per_l": 92,
    },
    "air": {
        "base_linehaul_per_km": 24.5,
        "weight_rate_inr_per_kg": 9.2,
        "piece_fee_inr": 28,
        "booking_fee_inr": 1400,
        "fuel_surcharge_pct": 0.18,
        "gst_pct": 0.18,
        "toll_per_km": 0.0,
        "handling_fee_inr": 640,
        "fuel_efficiency_kmpl": 4.0,
        "fuel_price_inr_per_l": 120,
    },
    "waterways": {
        "base_linehaul_per_km": 6.1,
        "weight_rate_inr_per_kg": 1.25,
        "piece_fee_inr": 10,
        "booking_fee_inr": 760,
        "fuel_surcharge_pct": 0.09,
        "gst_pct": 0.05,
        "toll_per_km": 0.2,
        "handling_fee_inr": 410,
        "fuel_efficiency_kmpl": 3.1,
        "fuel_price_inr_per_l": 88,
    },
}


REGION_SURCHARGE = {
    "tier_2": 0.03,
    "tier_3": 0.08,
    "sez": 0.06,
}


TIER_2_CITIES = {
    "mumbai", "thane", "navi mumbai", "pune", "delhi", "new delhi", "gurugram",
    "noida", "bengaluru", "bangalore", "chennai", "hyderabad", "kolkata",
    "ahmedabad", "surat", "jaipur", "lucknow", "nagpur", "indore", "bhopal",
    "coimbatore", "kochi", "visakhapatnam", "nashik", "vadodara", "chandigarh",
}


SEZ_KEYWORDS = (
    "sez",
    "special economic zone",
    "export processing zone",
    "free trade warehousing zone",
)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def normalize_cargo_profile(payload):
    cargo = payload or {}
    dimensions = cargo.get("dimensions_cm") or {}

    quantity = max(1, _safe_int(cargo.get("quantity"), 1))
    weight_kg = max(0.0, round(_safe_float(cargo.get("weight_kg"), 0.0), 2))
    length_cm = max(0.0, round(_safe_float(dimensions.get("length"), 0.0), 1))
    width_cm = max(0.0, round(_safe_float(dimensions.get("width"), 0.0), 1))
    height_cm = max(0.0, round(_safe_float(dimensions.get("height"), 0.0), 1))

    volume_cm3_per_item = round(length_cm * width_cm * height_cm, 1)
    total_volume_cm3 = round(volume_cm3_per_item * quantity, 1)
    volumetric_weight_kg = 0.0
    if volume_cm3_per_item > 0:
        volumetric_weight_kg = round((total_volume_cm3 / 5000), 2)

    billable_weight_kg = round(max(weight_kg, volumetric_weight_kg), 2)
    density_ratio = round(weight_kg / volumetric_weight_kg, 2) if volumetric_weight_kg else None

    return {
        "quantity": quantity,
        "weight_kg": weight_kg,
        "dimensions_cm": {
            "length": length_cm,
            "width": width_cm,
            "height": height_cm,
        },
        "volume_cm3_per_item": volume_cm3_per_item,
        "total_volume_cm3": total_volume_cm3,
        "volumetric_weight_kg": volumetric_weight_kg,
        "billable_weight_kg": billable_weight_kg,
        "density_ratio": density_ratio,
        "is_complete": bool(weight_kg or volume_cm3_per_item),
    }


def _extract_locality(location):
    if not location:
        return ""

    address = location.get("address") or {}
    return (
        address.get("city")
        or address.get("town")
        or address.get("state_district")
        or address.get("county")
        or ""
    ).strip().lower()


def classify_region_type(destination_location, destination_query, config, logger):
    query = (destination_query or "").strip()
    query_normalized = query.lower()
    locality = _extract_locality(destination_location)
    address = destination_location.get("address") or {}
    postcode = (address.get("postcode") or "").strip()

    if any(keyword in query_normalized for keyword in SEZ_KEYWORDS):
        heuristic = {
            "region_type": "sez",
            "confidence": 0.95,
            "reason": "Destination address contains SEZ-related keywords.",
            "source": "heuristic",
        }
    elif locality in TIER_2_CITIES:
        heuristic = {
            "region_type": "tier_2",
            "confidence": 0.82,
            "reason": "Destination locality matches the metro and tier-2 operational list.",
            "source": "heuristic",
        }
    else:
        heuristic = {
            "region_type": "tier_3",
            "confidence": 0.68,
            "reason": "Destination appears outside the core metro/tier-2 list, so last-mile risk is treated as tier-3.",
            "source": "heuristic",
        }

    if not gemini_is_configured(config):
        return {
            **heuristic,
            "query": query,
            "postcode": postcode or None,
            "locality": locality or None,
        }

    prompt = "\n".join(
        [
            "You are classifying an Indian delivery destination for logistics planning.",
            "Return valid JSON only.",
            'Schema: {"region_type":"tier_2|tier_3|sez","confidence":0.0,"reason":"string"}',
            "Choose exactly one region_type.",
            "Use SEZ only when the address strongly indicates a special economic zone, export zone, or controlled industrial customs corridor.",
            "Use tier_2 for metro, major urban, and well-connected city deliveries.",
            "Use tier_3 for smaller-city, rural, low-redundancy, or peripheral deliveries.",
            f"Destination query: {query or 'n/a'}",
            f"Resolved locality: {locality or 'n/a'}",
            f"Postcode: {postcode or 'n/a'}",
            f"Resolved address: {destination_location.get('display_name') or 'n/a'}",
            f"Heuristic suggestion: {heuristic['region_type']} ({heuristic['reason']})",
        ]
    )
    parsed = generate_json(prompt, config, logger, temperature=0.1)

    region_type = (parsed or {}).get("region_type")
    confidence = _safe_float((parsed or {}).get("confidence"), heuristic["confidence"])
    reason = (parsed or {}).get("reason") or heuristic["reason"]
    if region_type not in {"tier_2", "tier_3", "sez"}:
        region_type = heuristic["region_type"]
        confidence = heuristic["confidence"]
        reason = heuristic["reason"]
        source = "heuristic"
    else:
        source = "gemini"

    return {
        "region_type": region_type,
        "confidence": round(_clamp(confidence, 0.0, 1.0), 2),
        "reason": reason,
        "source": source,
        "query": query,
        "postcode": postcode or None,
        "locality": locality or None,
    }


def _fuel_cost(distance_km, mode, billable_weight_kg):
    profile = MODE_COST_FACTORS[mode]
    load_penalty = 1 + min(billable_weight_kg / 1600, 0.28)
    liters = max(0.0, distance_km / max(profile["fuel_efficiency_kmpl"], 0.1)) * load_penalty
    return round(liters * profile["fuel_price_inr_per_l"], 2)


def _mode_cost_breakdown(mode, distance_km, region_type, cargo_profile):
    profile = MODE_COST_FACTORS[mode]
    billable_weight_kg = cargo_profile["billable_weight_kg"]
    quantity = cargo_profile["quantity"]
    dimensional_penalty = 1.0
    if cargo_profile["volumetric_weight_kg"] > cargo_profile["weight_kg"] * 1.15:
        dimensional_penalty = 1.08

    linehaul_inr = round(
        (
            distance_km * profile["base_linehaul_per_km"]
            + billable_weight_kg * profile["weight_rate_inr_per_kg"]
            + quantity * profile["piece_fee_inr"]
            + profile["booking_fee_inr"]
        )
        * dimensional_penalty,
        2,
    )
    fuel_cost_inr = _fuel_cost(distance_km, mode, billable_weight_kg)
    fuel_surcharge_inr = round(fuel_cost_inr * profile["fuel_surcharge_pct"], 2)
    handling_inr = round(profile["handling_fee_inr"] + max(quantity - 1, 0) * (profile["piece_fee_inr"] * 0.6), 2)
    tolls_and_access_inr = round(distance_km * profile["toll_per_km"], 2)
    regional_surcharge_inr = round(
        (linehaul_inr + handling_inr + tolls_and_access_inr) * REGION_SURCHARGE.get(region_type, 0.04),
        2,
    )
    subtotal_inr = round(
        linehaul_inr
        + handling_inr
        + tolls_and_access_inr
        + fuel_surcharge_inr
        + regional_surcharge_inr,
        2,
    )
    gst_inr = round(subtotal_inr * profile["gst_pct"], 2)
    total_inr = round(subtotal_inr + gst_inr, 2)

    return {
        "mode": mode,
        "linehaul_inr": linehaul_inr,
        "fuel_cost_inr": fuel_cost_inr,
        "fuel_surcharge_inr": fuel_surcharge_inr,
        "handling_inr": handling_inr,
        "tolls_and_access_inr": tolls_and_access_inr,
        "regional_surcharge_inr": regional_surcharge_inr,
        "taxes_inr": gst_inr,
        "subtotal_inr": subtotal_inr,
        "total_inr": total_inr,
    }


def _agency_quotes(mode, base_breakdown):
    quotes = []
    for agency in AGENCY_PROFILES.get(mode, []):
        subtotal = round((base_breakdown["subtotal_inr"] * agency["multiplier"]) + agency["flat_markup_inr"], 2)
        taxes_inr = round(base_breakdown["taxes_inr"] * agency["multiplier"], 2)
        total_estimate_inr = round(subtotal + taxes_inr, 2)
        quotes.append(
            {
                "agency": agency["name"],
                "mode": mode,
                "serviceability": agency["serviceability"],
                "linehaul_inr": round(base_breakdown["linehaul_inr"] * agency["multiplier"], 2),
                "fuel_surcharge_inr": round(base_breakdown["fuel_surcharge_inr"] * agency["multiplier"], 2),
                "handling_inr": round(base_breakdown["handling_inr"] * agency["multiplier"], 2),
                "taxes_inr": taxes_inr,
                "total_estimate_inr": total_estimate_inr,
            }
        )

    return sorted(quotes, key=lambda item: item["total_estimate_inr"])


def build_shipment_pricing(route_snapshot, cargo_profile, selected_mode):
    modal_options = route_snapshot.get("modal_options") or []
    if not modal_options:
        return None

    mode_estimates = {}
    all_quotes = []
    for option in modal_options:
        mode = option["mode"]
        distance_km = option["distance_km"]
        breakdown = _mode_cost_breakdown(
            mode,
            distance_km,
            route_snapshot["region_type"],
            cargo_profile,
        )
        quotes = _agency_quotes(mode, breakdown)
        mode_estimates[mode] = {
            "mode": mode,
            "distance_km": distance_km,
            "duration_text": option["duration_text"],
            "estimated_total_cost_inr": breakdown["total_inr"],
            "taxes_inr": breakdown["taxes_inr"],
            "fuel_cost_inr": breakdown["fuel_cost_inr"],
            "breakdown": breakdown,
            "quotes": quotes,
        }
        all_quotes.extend(quotes[:2])

    selected = mode_estimates.get(selected_mode) or next(iter(mode_estimates.values()))
    selected_quotes = selected["quotes"] or []
    low_quote = min((quote["total_estimate_inr"] for quote in selected_quotes), default=selected["estimated_total_cost_inr"])
    high_quote = max((quote["total_estimate_inr"] for quote in selected_quotes), default=selected["estimated_total_cost_inr"])

    return {
        "selected_mode": selected_mode,
        "selected_estimate_inr": selected["estimated_total_cost_inr"],
        "estimated_range_inr": {
            "min": low_quote,
            "max": high_quote,
        },
        "taxes_inr": selected["taxes_inr"],
        "fuel_cost_inr": selected["fuel_cost_inr"],
        "mode_estimates": mode_estimates,
        "benchmark_quotes": selected_quotes,
        "market_watch_quotes": sorted(all_quotes, key=lambda item: item["total_estimate_inr"])[:5],
        "assumptions": [
            "Quotes are modeled benchmarks derived from distance, mode, billable weight, fuel, toll/access, and GST.",
            "Region surcharge increases when the destination is auto-classified as tier-3 or SEZ.",
            "Actual carrier quotes can change with SLA, pickup slot, packaging, and restricted-access surcharges.",
        ],
        "source_note": "Modeled agency benchmarks with operational cost math, not live carrier tariff scraping.",
    }


def build_traffic_analysis(base_route, cargo_profile, congestion_index, weather):
    primary_delay_multiplier = 1 + max(congestion_index - 0.35, 0) * 0.75 + (weather.get("weather_risk_score", 0) * 0.08)
    projected_primary_minutes = round((base_route["duration_seconds"] / 60) * primary_delay_multiplier)

    alternatives = []
    for alternative in base_route.get("alternative_routes") or []:
        relief_factor = 1 - min(max(congestion_index - 0.3, 0), 0.28)
        alternative_projected_minutes = round((alternative["duration_seconds"] / 60) * relief_factor)
        extra_distance_km = round(alternative["distance_km"] - base_route["distance_km"], 1)
        fuel_delta_inr = round(
            _fuel_cost(alternative["distance_km"], "road", cargo_profile["billable_weight_kg"])
            - _fuel_cost(base_route["distance_km"], "road", cargo_profile["billable_weight_kg"]),
            2,
        )
        time_saved_minutes = projected_primary_minutes - alternative_projected_minutes
        alternatives.append(
            {
                "route_id": alternative["route_id"],
                "label": alternative["label"],
                "distance_km": alternative["distance_km"],
                "distance_text": alternative["distance_text"],
                "duration_text": alternative["duration_text"],
                "projected_duration_minutes": alternative_projected_minutes,
                "time_saved_minutes": time_saved_minutes,
                "extra_distance_km": extra_distance_km,
                "fuel_delta_inr": fuel_delta_inr,
                "geometry_coordinates": alternative.get("geometry_coordinates") or [],
                "directions_preview": alternative.get("directions_preview") or [],
                "is_recommended": False,
            }
        )

    alternatives.sort(key=lambda item: (-item["time_saved_minutes"], item["extra_distance_km"]))
    recommended = None
    if alternatives and alternatives[0]["time_saved_minutes"] > 0:
        alternatives[0]["is_recommended"] = True
        recommended = alternatives[0]

    status = "light"
    if projected_primary_minutes - round(base_route["duration_seconds"] / 60) >= 15:
        status = "heavy"
    elif projected_primary_minutes - round(base_route["duration_seconds"] / 60) >= 6:
        status = "moderate"

    return {
        "source": "operational_model",
        "is_live_traffic": False,
        "status": status,
        "congestion_index": round(congestion_index, 2),
        "projected_primary_duration_minutes": projected_primary_minutes,
        "projected_delay_minutes": max(0, projected_primary_minutes - round(base_route["duration_seconds"] / 60)),
        "recommended_alternate": recommended,
        "alternative_routes": alternatives,
        "advisory": (
            f"Projected corridor traffic is {status}. "
            + (
                f"Switch to {recommended['label']} to save about {recommended['time_saved_minutes']} minutes."
                if recommended
                else "No faster alternate road corridor is currently projected."
            )
        ),
    }


def build_gemini_cargo_brief(route_snapshot, cargo_profile, shipment_pricing, config, logger):
    if not gemini_is_configured(config) or not shipment_pricing:
        return None

    prompt = "\n".join(
        [
            "You are preparing a concise Indian logistics planning note.",
            "Return valid JSON only.",
            'Schema: {"summary":"string","cost_driver":"string","operations_note":"string"}',
            f"Route: {route_snapshot['route']['source']} -> {route_snapshot['route']['destination']}",
            f"Mode: {route_snapshot['route']['transport_mode']}",
            f"Region type: {route_snapshot['region_type']}",
            f"Weight kg: {cargo_profile['weight_kg']}",
            f"Billable weight kg: {cargo_profile['billable_weight_kg']}",
            f"Quantity: {cargo_profile['quantity']}",
            f"Estimated shipment cost INR: {shipment_pricing['selected_estimate_inr']}",
            f"Benchmark range INR: {shipment_pricing['estimated_range_inr']['min']} - {shipment_pricing['estimated_range_inr']['max']}",
            "Focus on cost drivers and delivery planning. Do not invent live tariffs.",
        ]
    )
    parsed = generate_json(prompt, config, logger, temperature=0.2)
    if not parsed:
        return None

    return {
        "summary": parsed.get("summary") or "",
        "cost_driver": parsed.get("cost_driver") or "",
        "operations_note": parsed.get("operations_note") or "",
    }
