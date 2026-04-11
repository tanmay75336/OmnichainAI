import hashlib
from math import asin, cos, radians, sin, sqrt

import requests

from app.utils.cache import shared_cache
from app.utils.errors import ExternalAPIError, ValidationError


OPENROUTESERVICE_DIRECTIONS_URL = (
    "https://api.openrouteservice.org/v2/directions/driving-car"
)
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


SUPPORTED_TRANSPORT_MODES = {"road", "rail", "air", "waterways"}


# Coordinates are stored as [longitude, latitude] to match OpenRouteService.
CITY_COORDINATES = {
    "mumbai": [72.8777, 19.0760],
    "pune": [73.8567, 18.5204],
    "delhi": [77.1025, 28.7041],
    "new delhi": [77.2090, 28.6139],
    "bengaluru": [77.5946, 12.9716],
    "bangalore": [77.5946, 12.9716],
    "chennai": [80.2707, 13.0827],
    "hyderabad": [78.4867, 17.3850],
    "kolkata": [88.3639, 22.5726],
    "ahmedabad": [72.5714, 23.0225],
    "surat": [72.8311, 21.1702],
    "jaipur": [75.7873, 26.9124],
    "lucknow": [80.9462, 26.8467],
    "nagpur": [79.0882, 21.1458],
    "visakhapatnam": [83.2185, 17.6868],
    "kochi": [76.2673, 9.9312],
}


def _normalize_city_name(city_name):
    return " ".join(city_name.strip().lower().split())


def _cache_key(source, destination, mode):
    raw = f"route::{source.lower()}::{destination.lower()}::{mode.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _geocode_cache_key(city_name):
    raw = f"geocode::{city_name.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _format_distance_text(distance_meters):
    distance_km = distance_meters / 1000
    rounded_distance = round(distance_km, 1)
    if float(rounded_distance).is_integer():
        rounded_distance = int(rounded_distance)
    return f"{rounded_distance} km"


def _format_duration_text(duration_seconds):
    total_minutes = max(1, round(duration_seconds / 60))
    if total_minutes < 60:
        return f"{total_minutes} mins"

    total_hours = round(duration_seconds / 3600, 1)
    if float(total_hours).is_integer():
        whole_hours = int(total_hours)
        label = "hour" if whole_hours == 1 else "hours"
        return f"{whole_hours} {label}"

    return f"{total_hours} hours"


def haversine_km(source_coordinates, destination_coordinates):
    lon1, lat1 = source_coordinates
    lon2, lat2 = destination_coordinates

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    inner = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(inner))


def _build_route_payload(
    route_request,
    *,
    distance_meters,
    duration_seconds,
    api_source,
    api_mode_used,
    is_fallback=False,
    source_coordinates=None,
    destination_coordinates=None,
):
    normalized_distance = max(1, int(round(distance_meters)))
    normalized_duration = max(60, int(round(duration_seconds)))

    return {
        "source": route_request.source,
        "destination": route_request.destination,
        "transport_mode": route_request.transport_mode,
        "source_coordinates": source_coordinates,
        "destination_coordinates": destination_coordinates,
        "distance_meters": normalized_distance,
        "distance_km": round(normalized_distance / 1000, 1),
        "distance_text": _format_distance_text(normalized_distance),
        "duration_seconds": normalized_duration,
        "duration_hours": round(normalized_duration / 3600, 2),
        "duration_text": _format_duration_text(normalized_duration),
        "api_source": api_source,
        "route_source": api_source,
        "is_fallback": is_fallback,
        "api_mode_used": api_mode_used,
    }


def _build_simple_route_response(route_data):
    return {
        "distance": route_data["distance_text"],
        "duration": route_data["duration_text"],
        "source": route_data["route_source"],
        "is_fallback": route_data["is_fallback"],
    }


def _extract_route_summary(payload):
    routes = payload.get("routes") or []
    summary = routes[0].get("summary") if routes else None

    if not summary:
        raise ExternalAPIError("OpenRouteService returned an invalid route response.")

    distance = summary.get("distance")
    duration = summary.get("duration")
    if distance is None or duration is None:
        raise ExternalAPIError("OpenRouteService response is missing route summary data.")

    return float(distance), float(duration)


def _build_fallback_route(route_request, source_coordinates, destination_coordinates):
    geodesic_distance_km = haversine_km(source_coordinates, destination_coordinates)
    estimated_distance_km = max(25, round(geodesic_distance_km * 1.22, 1))
    estimated_duration_hours = estimated_distance_km / 42

    return _build_route_payload(
        route_request,
        distance_meters=estimated_distance_km * 1000,
        duration_seconds=estimated_duration_hours * 3600,
        api_source="geodesic_fallback",
        api_mode_used="estimated-road",
        is_fallback=True,
        source_coordinates=source_coordinates,
        destination_coordinates=destination_coordinates,
    )


def _fetch_openrouteservice_route(source_coordinates, destination_coordinates, api_key, timeout):
    response = requests.post(
        OPENROUTESERVICE_DIRECTIONS_URL,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
        },
        json={"coordinates": [source_coordinates, destination_coordinates]},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _fetch_nominatim_coordinates(city_name, config, logger):
    cache_key = _geocode_cache_key(city_name)
    cached = shared_cache.get(cache_key)
    if cached:
        logger.info("Geocode cache hit for %s", city_name)
        return cached

    params = {
        "q": f"{city_name}, India",
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "in",
        "addressdetails": 1,
    }
    headers = {
        "User-Agent": config.get(
            "NOMINATIM_USER_AGENT",
            "smart-supply-chain-optimization/1.0",
        )
    }
    email = (config.get("NOMINATIM_EMAIL") or "").strip()
    if email:
        params["email"] = email

    logger.info("Using Nominatim geocoding for %s", city_name)
    try:
        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=config["REQUEST_TIMEOUT_SECONDS"],
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise ExternalAPIError("Failed to geocode city with Nominatim.") from exc
    except ValueError as exc:
        raise ExternalAPIError("Nominatim returned an invalid geocoding response.") from exc

    if not payload:
        raise ValidationError(f"Could not find city '{city_name}' in India.")

    first_match = payload[0]
    longitude = first_match.get("lon")
    latitude = first_match.get("lat")
    if longitude is None or latitude is None:
        raise ExternalAPIError("Nominatim response is missing coordinates.")

    coordinates = [float(longitude), float(latitude)]
    shared_cache.set(cache_key, coordinates, ttl=config["CACHE_TTL_SECONDS"])
    return coordinates


def get_coordinates(city_name, config=None, logger=None):
    normalized_city = _normalize_city_name(city_name)
    coordinates = CITY_COORDINATES.get(normalized_city)

    if coordinates:
        return list(coordinates)

    if config is None or logger is None:
        raise ValidationError(
            f"City '{city_name}' is not available in the local route map."
        )

    return _fetch_nominatim_coordinates(city_name, config, logger)


def get_route_data(route_request, config, logger):
    if route_request.transport_mode not in SUPPORTED_TRANSPORT_MODES:
        supported_modes = ", ".join(sorted(SUPPORTED_TRANSPORT_MODES))
        raise ValidationError(
            f"Unsupported transport_mode '{route_request.transport_mode}'. Use: {supported_modes}."
        )

    cache_key = _cache_key(
        route_request.source,
        route_request.destination,
        route_request.transport_mode,
    )
    cached = shared_cache.get(cache_key)
    if cached:
        logger.info(
            "Route cache hit for %s -> %s",
            route_request.source,
            route_request.destination,
        )
        return cached

    try:
        source_coordinates = get_coordinates(
            route_request.source,
            config=config,
            logger=logger,
        )
        destination_coordinates = get_coordinates(
            route_request.destination,
            config=config,
            logger=logger,
        )
    except ValidationError:
        raise
    except ExternalAPIError as exc:
        raise ExternalAPIError(
            f"Route geocoding failed. Details: {exc}"
        ) from exc

    api_key = (config.get("ORS_API_KEY") or "").strip()
    if not api_key:
        route_data = _build_fallback_route(
            route_request,
            source_coordinates,
            destination_coordinates,
        )
        shared_cache.set(cache_key, route_data, ttl=config["CACHE_TTL_SECONDS"])
        logger.warning("ORS_API_KEY missing. Using fallback route for %s -> %s", route_request.source, route_request.destination)
        return route_data

    try:
        logger.info(
            "Using OpenRouteService for %s -> %s",
            route_request.source,
            route_request.destination,
        )
        payload = _fetch_openrouteservice_route(
            source_coordinates,
            destination_coordinates,
            api_key,
            config["REQUEST_TIMEOUT_SECONDS"],
        )
        distance_meters, duration_seconds = _extract_route_summary(payload)
        route_data = _build_route_payload(
            route_request,
            distance_meters=distance_meters,
            duration_seconds=duration_seconds,
            api_source="openrouteservice",
            api_mode_used="driving-car",
            source_coordinates=source_coordinates,
            destination_coordinates=destination_coordinates,
        )
    except (requests.RequestException, ExternalAPIError, TypeError, ValueError) as exc:
        logger.warning(
            "OpenRouteService request failed for %s -> %s. Using fallback. Details: %s",
            route_request.source,
            route_request.destination,
            exc,
        )
        route_data = _build_fallback_route(
            route_request,
            source_coordinates,
            destination_coordinates,
        )

    shared_cache.set(cache_key, route_data, ttl=config["CACHE_TTL_SECONDS"])
    return route_data


def get_route(source, destination, config, logger):
    from app.models.domain import RouteRequest

    route_request = RouteRequest(
        source=source,
        destination=destination,
        transport_mode="road",
        region_type="tier_2",
    )
    route_data = get_route_data(route_request=route_request, config=config, logger=logger)
    return _build_simple_route_response(route_data)
