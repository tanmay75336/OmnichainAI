from app.models.domain import RouteRequest
from app.services.risk_service import calculate_risk, derive_congestion_index
from app.services.routing_service import get_route_data
from app.services.transport_service import (
    build_modal_comparison,
    choose_recommended_mode,
    enrich_route_with_transport_data,
)
from app.services.weather_service import get_weather_for_location


def build_route_snapshot(source, destination, transport_mode, region_type, config, logger):
    route_request = RouteRequest(
        source=source,
        destination=destination,
        transport_mode=transport_mode,
        region_type=region_type,
    )

    base_route = get_route_data(route_request=route_request, config=config, logger=logger)
    weather = get_weather_for_location(destination, config=config, logger=logger)
    congestion_index = derive_congestion_index(base_route, weather, route_request.region_type)

    selected_route = enrich_route_with_transport_data(
        base_route,
        route_request.transport_mode,
        route_request.region_type,
        weather,
        congestion_index,
    )
    risk = calculate_risk(selected_route, weather, route_request.region_type)

    modal_options = []
    modal_risks = {}
    for option in build_modal_comparison(
        base_route,
        route_request.region_type,
        weather,
        congestion_index,
    ):
        mode_route = enrich_route_with_transport_data(
            base_route,
            option["mode"],
            route_request.region_type,
            weather,
            congestion_index,
        )
        option_risk = calculate_risk(mode_route, weather, route_request.region_type)
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

    return {
        "base_route": base_route,
        "route": selected_route,
        "weather": weather,
        "region_type": route_request.region_type,
        "risk": risk,
        "modal_options": modal_options,
        "suggested_transport_mode": suggested_transport_mode,
    }
