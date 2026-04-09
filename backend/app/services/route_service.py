from app.models.domain import RouteRequest
from app.services.google_maps_service import get_distance_matrix_route
from app.services.transport_service import enrich_route_with_transport_data
from app.services.weather_service import get_weather_for_location


def build_route_snapshot(source, destination, transport_mode, region_type, config, logger):
    route_request = RouteRequest(
        source=source,
        destination=destination,
        transport_mode=transport_mode,
        region_type=region_type,
    )

    route_data = get_distance_matrix_route(route_request=route_request, config=config, logger=logger)
    enriched_route = enrich_route_with_transport_data(route_data, route_request.transport_mode)
    weather = get_weather_for_location(destination, config=config, logger=logger)

    return {
        "route": enriched_route,
        "weather": weather,
        "region_type": route_request.region_type,
    }
