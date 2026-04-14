import hashlib
from math import asin, cos, radians, sin, sqrt

import requests

from app.utils.cache import shared_cache
from app.utils.errors import ExternalAPIError, ValidationError


OPENROUTESERVICE_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


SUPPORTED_TRANSPORT_MODES = {"road", "rail", "air", "waterways"}


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
    "thane": [72.9781, 19.2183],
    "badlapur": [73.2667, 19.1667],
}


def _normalize_query(value):
    return " ".join((value or "").strip().lower().split())


def _cache_key(source, destination, mode):
    raw = f"route::{_normalize_query(source)}::{_normalize_query(destination)}::{mode.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _location_cache_key(query):
    raw = f"location::{_normalize_query(query)}"
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
        total_hours = int(total_hours)
        return f"{total_hours} {'hour' if total_hours == 1 else 'hours'}"

    return f"{total_hours} hours"


def haversine_km(source_coordinates, destination_coordinates):
    lon1, lat1 = source_coordinates
    lon2, lat2 = destination_coordinates

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    inner = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(inner))


def _decode_polyline(encoded, precision=5):
    coordinates = []
    latitude = 0
    longitude = 0
    factor = 10 ** precision
    index = 0

    while index < len(encoded):
        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        latitude += ~(result >> 1) if result & 1 else result >> 1

        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        longitude += ~(result >> 1) if result & 1 else result >> 1

        coordinates.append([round(longitude / factor, 6), round(latitude / factor, 6)])

    return coordinates


def _extract_city_from_address(address):
    if not address:
        return None

    return (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
        or address.get("state_district")
        or None
    )


def _title_case(text):
    if not text:
        return text

    return " ".join(part.capitalize() for part in str(text).split())


def _build_location_payload(query, longitude, latitude, *, source, display_name=None, address=None):
    address = address or {}
    locality = _extract_city_from_address(address)
    state = address.get("state")
    postcode = address.get("postcode")
    label_parts = [locality, state, postcode]
    label = ", ".join(part for part in label_parts if part) or display_name or query

    return {
        "query": query,
        "label": label,
        "display_name": display_name or label,
        "coordinates": [round(float(longitude), 6), round(float(latitude), 6)],
        "address": address,
        "locality": locality,
        "state": state,
        "postcode": postcode,
        "country": address.get("country", "India"),
        "source": source,
    }


def _build_static_location_payload(query, coordinates):
    return _build_location_payload(
        query,
        coordinates[0],
        coordinates[1],
        source="local_city_catalog",
        display_name=query,
        address={"city": _title_case(query), "country": "India"},
    )


def _guess_location_from_catalog(query):
    normalized = _normalize_query(query)
    matches = []
    for city_name, coordinates in CITY_COORDINATES.items():
        index = normalized.find(city_name)
        if index >= 0:
            matches.append((index, -len(city_name), city_name, coordinates))

    if not matches:
        return None

    matches.sort()
    _, _, city_name, coordinates = matches[0]
    return _build_location_payload(
        query,
        coordinates[0],
        coordinates[1],
        source="address_city_fallback",
        display_name=query,
        address={"city": _title_case(city_name), "country": "India"},
    )


def _fetch_nominatim_location(query, config, logger):
    cache_key = _location_cache_key(query)
    cached = shared_cache.get(cache_key)
    if cached:
        logger.info("Location cache hit for %s", query)
        return cached

    params = {
        "q": query,
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
        guessed = _guess_location_from_catalog(query)
        if guessed:
            logger.warning(
                "Nominatim request failed for %s. Falling back to catalog-matched city. Details: %s",
                query,
                exc,
            )
            return guessed
        raise ExternalAPIError("Failed to geocode the provided address.") from exc
    except ValueError as exc:
        raise ExternalAPIError("Invalid geocoding payload returned by Nominatim.") from exc

    if not payload:
        raise ValidationError(f"Could not resolve location '{query}' in India.")

    first_match = payload[0]
    longitude = first_match.get("lon")
    latitude = first_match.get("lat")
    if longitude is None or latitude is None:
        raise ExternalAPIError("Nominatim response is missing coordinates.")

    location = _build_location_payload(
        query,
        longitude,
        latitude,
        source="nominatim",
        display_name=first_match.get("display_name") or query,
        address=first_match.get("address") or {},
    )
    shared_cache.set(cache_key, location, ttl=config["CACHE_TTL_SECONDS"])
    return location


def resolve_location(query, config, logger):
    normalized = _normalize_query(query)
    if not normalized:
        raise ValidationError("Address is required.")

    if normalized in CITY_COORDINATES:
        return _build_static_location_payload(query, CITY_COORDINATES[normalized])

    guessed = _guess_location_from_catalog(query)
    if guessed:
        return guessed

    return _fetch_nominatim_location(query, config, logger)


def get_coordinates(city_name, config=None, logger=None):
    location = resolve_location(city_name, config, logger)
    return list(location["coordinates"])


def _build_route_payload(
    route_request,
    *,
    source_location,
    destination_location,
    distance_meters,
    duration_seconds,
    api_source,
    api_mode_used,
    geometry_coordinates=None,
    directions_preview=None,
    alternative_routes=None,
    is_fallback=False,
):
    normalized_distance = max(1, int(round(distance_meters)))
    normalized_duration = max(60, int(round(duration_seconds)))

    return {
        "source": route_request.source,
        "destination": route_request.destination,
        "transport_mode": route_request.transport_mode,
        "source_coordinates": source_location["coordinates"],
        "destination_coordinates": destination_location["coordinates"],
        "source_details": source_location,
        "destination_details": destination_location,
        "distance_meters": normalized_distance,
        "distance_km": round(normalized_distance / 1000, 1),
        "distance_text": _format_distance_text(normalized_distance),
        "duration_seconds": normalized_duration,
        "duration_hours": round(normalized_duration / 3600, 2),
        "duration_text": _format_duration_text(normalized_duration),
        "geometry_coordinates": geometry_coordinates or [],
        "directions_preview": directions_preview or [],
        "alternative_routes": alternative_routes or [],
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


def _format_step(step):
    return {
        "instruction": step.get("instruction") or "Continue on route",
        "distance_meters": round(float(step.get("distance", 0)), 1),
        "distance_text": _format_distance_text(float(step.get("distance", 0))),
        "duration_seconds": round(float(step.get("duration", 0)), 1),
        "duration_text": _format_duration_text(float(step.get("duration", 0))),
    }


def _extract_route_variant(
    route_payload,
    route_request,
    source_location,
    destination_location,
    *,
    label,
    route_id,
):
    summary = route_payload.get("summary") or {}
    distance = summary.get("distance")
    duration = summary.get("duration")
    if distance is None or duration is None:
        raise ExternalAPIError("OpenRouteService response is missing route summary data.")

    geometry = route_payload.get("geometry")
    if isinstance(geometry, str):
        geometry_coordinates = _decode_polyline(geometry)
    else:
        geometry_coordinates = []

    segments = route_payload.get("segments") or []
    first_segment = segments[0] if segments else {}
    steps = first_segment.get("steps") or []

    return {
        "route_id": route_id,
        "label": label,
        "distance_meters": int(round(distance)),
        "distance_km": round(float(distance) / 1000, 1),
        "distance_text": _format_distance_text(float(distance)),
        "duration_seconds": int(round(duration)),
        "duration_text": _format_duration_text(float(duration)),
        "geometry_coordinates": geometry_coordinates,
        "directions_preview": [_format_step(step) for step in steps[:8]],
        "source_coordinates": source_location["coordinates"],
        "destination_coordinates": destination_location["coordinates"],
        "source": route_request.source,
        "destination": route_request.destination,
    }


def _fetch_openrouteservice_routes(source_coordinates, destination_coordinates, api_key, timeout):
    response = requests.post(
        OPENROUTESERVICE_DIRECTIONS_URL,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
        },
        json={
            "coordinates": [source_coordinates, destination_coordinates],
            "instructions": True,
            "alternative_routes": {
                "target_count": 2,
                "weight_factor": 1.6,
                "share_factor": 0.6,
            },
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _build_fallback_route(route_request, source_location, destination_location):
    geodesic_distance_km = haversine_km(
        source_location["coordinates"],
        destination_location["coordinates"],
    )
    estimated_distance_km = max(25, round(geodesic_distance_km * 1.22, 1))
    estimated_duration_hours = estimated_distance_km / 42
    directions_preview = [
        {
            "instruction": f"Start from {source_location['label']}",
            "distance_meters": 0,
            "distance_text": "0 km",
            "duration_seconds": 0,
            "duration_text": "0 mins",
        },
        {
            "instruction": f"Proceed toward {destination_location['label']} via the primary road corridor.",
            "distance_meters": int(round(estimated_distance_km * 1000)),
            "distance_text": _format_distance_text(estimated_distance_km * 1000),
            "duration_seconds": int(round(estimated_duration_hours * 3600)),
            "duration_text": _format_duration_text(estimated_duration_hours * 3600),
        },
    ]

    return _build_route_payload(
        route_request,
        source_location=source_location,
        destination_location=destination_location,
        distance_meters=estimated_distance_km * 1000,
        duration_seconds=estimated_duration_hours * 3600,
        api_source="geodesic_fallback",
        api_mode_used="estimated-road",
        geometry_coordinates=[
            source_location["coordinates"],
            destination_location["coordinates"],
        ],
        directions_preview=directions_preview,
        alternative_routes=[],
        is_fallback=True,
    )


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

    source_location = resolve_location(route_request.source, config, logger)
    destination_location = resolve_location(route_request.destination, config, logger)

    api_key = (config.get("ORS_API_KEY") or "").strip()
    if not api_key:
        route_data = _build_fallback_route(
            route_request,
            source_location,
            destination_location,
        )
        shared_cache.set(cache_key, route_data, ttl=config["CACHE_TTL_SECONDS"])
        logger.warning(
            "ORS_API_KEY missing. Using fallback route for %s -> %s",
            route_request.source,
            route_request.destination,
        )
        return route_data

    try:
        payload = _fetch_openrouteservice_routes(
            source_location["coordinates"],
            destination_location["coordinates"],
            api_key,
            config["REQUEST_TIMEOUT_SECONDS"],
        )
        routes = payload.get("routes") or []
        if not routes:
            raise ExternalAPIError("OpenRouteService returned no routes.")

        primary = _extract_route_variant(
            routes[0],
            route_request,
            source_location,
            destination_location,
            label="Primary route",
            route_id="primary",
        )
        alternatives = []
        for index, route_variant in enumerate(routes[1:], start=1):
            try:
                alternatives.append(
                    _extract_route_variant(
                        route_variant,
                        route_request,
                        source_location,
                        destination_location,
                        label=f"Alternate route {index}",
                        route_id=f"alternate_{index}",
                    )
                )
            except ExternalAPIError:
                continue

        route_data = _build_route_payload(
            route_request,
            source_location=source_location,
            destination_location=destination_location,
            distance_meters=primary["distance_meters"],
            duration_seconds=primary["duration_seconds"],
            api_source="openrouteservice",
            api_mode_used="driving-car",
            geometry_coordinates=primary["geometry_coordinates"],
            directions_preview=primary["directions_preview"],
            alternative_routes=alternatives,
            is_fallback=False,
        )
    except (requests.RequestException, ExternalAPIError, TypeError, ValueError, IndexError) as exc:
        logger.warning(
            "OpenRouteService request failed for %s -> %s. Using fallback. Details: %s",
            route_request.source,
            route_request.destination,
            exc,
        )
        route_data = _build_fallback_route(
            route_request,
            source_location,
            destination_location,
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
