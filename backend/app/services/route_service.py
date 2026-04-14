from app.models.domain import RouteRequest
from app.services.logistics_service import (
    build_gemini_cargo_brief,
    build_shipment_pricing,
    build_traffic_analysis,
    classify_region_type,
    normalize_cargo_profile,
)
from app.services.risk_service import calculate_risk, derive_congestion_index
from app.services.routing_service import get_route_data
from app.services.transport_service import (
    build_modal_comparison,
    choose_recommended_mode,
    enrich_route_with_transport_data,
)
from app.services.weather_service import get_route_weather_outlook, get_weather_for_location


def _build_route_samples(base_route):
    geometry = base_route.get("geometry_coordinates") or []
    if geometry:
        middle = geometry[len(geometry) // 2]
    else:
        source_coordinates = base_route["source_coordinates"]
        destination_coordinates = base_route["destination_coordinates"]
        middle = [
            round((source_coordinates[0] + destination_coordinates[0]) / 2, 6),
            round((source_coordinates[1] + destination_coordinates[1]) / 2, 6),
        ]

    return [
        {
            "label": base_route["source_details"]["label"],
            "coordinates": base_route["source_coordinates"],
        },
        {
            "label": "Mid-corridor",
            "coordinates": middle,
        },
        {
            "label": base_route["destination_details"]["label"],
            "coordinates": base_route["destination_coordinates"],
        },
    ]


def build_route_snapshot(source, destination, transport_mode, region_type, config, logger, cargo=None):
    route_request = RouteRequest(
        source=source,
        destination=destination,
        transport_mode=transport_mode,
        region_type=region_type or "tier_2",
    )

    base_route = get_route_data(route_request=route_request, config=config, logger=logger)
    region_context = classify_region_type(
        base_route["destination_details"],
        destination,
        config,
        logger,
    )
    detected_region_type = region_context["region_type"]
    cargo_profile = normalize_cargo_profile(cargo or {})

    weather = get_weather_for_location(
        base_route["destination_details"]["label"],
        config=config,
        logger=logger,
    )
    congestion_index = derive_congestion_index(base_route, weather, detected_region_type)

    selected_route = enrich_route_with_transport_data(
        base_route,
        route_request.transport_mode,
        detected_region_type,
        weather,
        congestion_index,
    )
    selected_route["region_type"] = detected_region_type
    risk = calculate_risk(selected_route, weather, detected_region_type)

    modal_options = []
    modal_risks = {}
    for option in build_modal_comparison(
        base_route,
        detected_region_type,
        weather,
        congestion_index,
    ):
        mode_route = enrich_route_with_transport_data(
            base_route,
            option["mode"],
            detected_region_type,
            weather,
            congestion_index,
        )
        option_risk = calculate_risk(mode_route, weather, detected_region_type)
        modal_risks[option["mode"]] = option_risk
        modal_options.append(
            {
                **option,
                "overall_risk": option_risk["overall_risk"],
                "weighted_score_pct": option_risk["weighted_score_pct"],
            }
        )

    suggested_transport_mode = choose_recommended_mode(
        modal_options,
        modal_risks,
        route_request.transport_mode,
    )
    for option in modal_options:
        option["is_recommended"] = option["mode"] == suggested_transport_mode["mode"]

    shipment_pricing = build_shipment_pricing(
        {
            "region_type": detected_region_type,
            "modal_options": modal_options,
        },
        cargo_profile,
        route_request.transport_mode,
    )
    traffic_analysis = build_traffic_analysis(
        base_route,
        cargo_profile,
        congestion_index,
        weather,
    )
    selected_route["traffic_analysis"] = traffic_analysis
    weather_outlook = get_route_weather_outlook(
        _build_route_samples(base_route),
        weather,
        config,
        logger,
    )
    gemini_cargo_brief = build_gemini_cargo_brief(
        {
            "route": selected_route,
            "region_type": detected_region_type,
        },
        cargo_profile,
        shipment_pricing,
        config,
        logger,
    )

    return {
        "base_route": base_route,
        "route": selected_route,
        "weather": weather,
        "weather_outlook": weather_outlook,
        "region_type": detected_region_type,
        "region_context": region_context,
        "cargo_profile": cargo_profile,
        "shipment_pricing": shipment_pricing,
        "gemini_cargo_brief": gemini_cargo_brief,
        "risk": risk,
        "modal_options": modal_options,
        "suggested_transport_mode": suggested_transport_mode,
    }
