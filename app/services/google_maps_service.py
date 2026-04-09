import hashlib

import requests

from app.utils.cache import shared_cache
from app.utils.errors import ExternalAPIError, ValidationError


GOOGLE_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


SUPPORTED_GOOGLE_MODES = {
    "road": "driving",
    "rail": "transit",
    "air": "driving",
    "waterways": "driving",
}


def _cache_key(source, destination, mode):
    raw = f"google-route::{source.lower()}::{destination.lower()}::{mode.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fetch_distance_matrix(source, destination, mode, api_key, timeout):
    response = requests.get(
        GOOGLE_DISTANCE_MATRIX_URL,
        params={
            "origins": source,
            "destinations": destination,
            "mode": mode,
            "key": api_key,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def get_distance_matrix_route(route_request, config, logger):
    transport_mode = route_request.transport_mode

    if transport_mode not in SUPPORTED_GOOGLE_MODES:
        raise ValidationError(
            f"Unsupported transport_mode '{transport_mode}'. Use road, rail, air, or waterways."
        )

    cache_key = _cache_key(route_request.source, route_request.destination, transport_mode)
    cached = shared_cache.get(cache_key)
    if cached:
        logger.info("Google route cache hit for %s -> %s", route_request.source, route_request.destination)
        return cached

    api_key = config.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ExternalAPIError("GOOGLE_MAPS_API_KEY is not configured.")

    try:
        requested_mode = SUPPORTED_GOOGLE_MODES[transport_mode]
        payload = _fetch_distance_matrix(
            route_request.source,
            route_request.destination,
            requested_mode,
            api_key,
            config["REQUEST_TIMEOUT_SECONDS"],
        )
    except requests.RequestException as exc:
        raise ExternalAPIError("Failed to fetch route data from Google Maps.") from exc

    if payload.get("status") != "OK":
        status = payload.get("status", "UNKNOWN")
        error_message = payload.get("error_message")

        if status == "REQUEST_DENIED":
            detailed_message = (
                "Google Maps request was denied. Check that the API key is valid, "
                "Distance Matrix API is enabled, billing is active, and any key restrictions allow this server."
            )
            if error_message:
                detailed_message = f"{detailed_message} Google says: {error_message}"
            raise ExternalAPIError(detailed_message)

        raise ExternalAPIError(
            f"Google Maps API returned status '{status}'."
            + (f" Details: {error_message}" if error_message else "")
        )

    rows = payload.get("rows") or []
    elements = rows[0].get("elements") if rows else []
    element = elements[0] if elements else None
    api_mode_used = requested_mode
    if (not element or element.get("status") != "OK") and transport_mode != "road":
        logger.warning(
            "Google Maps mode '%s' unavailable for %s -> %s. Falling back to driving baseline.",
            requested_mode,
            route_request.source,
            route_request.destination,
        )
        try:
            payload = _fetch_distance_matrix(
                route_request.source,
                route_request.destination,
                "driving",
                api_key,
                config["REQUEST_TIMEOUT_SECONDS"],
            )
        except requests.RequestException as exc:
            raise ExternalAPIError("Failed to fetch fallback route data from Google Maps.") from exc

        rows = payload.get("rows") or []
        elements = rows[0].get("elements") if rows else []
        element = elements[0] if elements else None
        api_mode_used = "driving_fallback"

    if not element or element.get("status") != "OK":
        raise ExternalAPIError("Google Maps could not resolve the requested route.")

    route_data = {
        "source": route_request.source,
        "destination": route_request.destination,
        "transport_mode": route_request.transport_mode,
        "distance_meters": element["distance"]["value"],
        "distance_text": element["distance"]["text"],
        "duration_seconds": element["duration"]["value"],
        "duration_text": element["duration"]["text"],
        "api_source": "google_distance_matrix",
        "api_mode_used": api_mode_used,
    }

    shared_cache.set(cache_key, route_data, ttl=config["CACHE_TTL_SECONDS"])
    return route_data
