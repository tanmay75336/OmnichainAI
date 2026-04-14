from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from app.services.insight_service import (
    build_india_context,
    build_route_decision_support,
    build_supply_chain_intelligence,
)
from app.services.logistics_service import normalize_cargo_profile
from app.services.route_service import build_route_snapshot
from app.services.routing_service import haversine_km
from app.services.supabase_service import (
    safe_create_shipment_record,
    safe_fetch_shipment_record,
    safe_update_shipment_record,
    supabase_enabled,
)
from app.utils.errors import ValidationError


_LOCAL_SHIPMENTS = {}
_STORE_LOCK = Lock()


def _now_utc():
    return datetime.now(timezone.utc)


def _iso_now():
    return _now_utc().isoformat()


def _shipment_id(source, destination):
    source_code = (source or "SRC").strip().upper()[:3]
    destination_code = (destination or "DST").strip().upper()[:3]
    timestamp_code = _now_utc().strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:6].upper()
    return f"OMNI-{source_code}-{destination_code}-{timestamp_code}-{suffix}"


def _safe_ratio(numerator, denominator):
    if not denominator:
        return 0.0
    return max(0.0, min(1.0, numerator / denominator))


def _interpolate_coordinates(source_coordinates, destination_coordinates, progress_ratio):
    if not source_coordinates or not destination_coordinates:
        return None

    source_lon, source_lat = source_coordinates
    destination_lon, destination_lat = destination_coordinates
    return [
        round(source_lon + (destination_lon - source_lon) * progress_ratio, 6),
        round(source_lat + (destination_lat - source_lat) * progress_ratio, 6),
    ]


def _path_distance_km(path):
    if not path or len(path) < 2:
        return 0.0

    total = 0.0
    for index in range(1, len(path)):
        total += haversine_km(path[index - 1], path[index])
    return total


def _interpolate_along_path(path, progress_ratio):
    if not path:
        return None
    if len(path) == 1:
        return path[0]

    total_distance = _path_distance_km(path)
    if total_distance <= 0:
        return path[-1]

    target_distance = total_distance * progress_ratio
    traversed = 0.0

    for index in range(1, len(path)):
        start = path[index - 1]
        end = path[index]
        segment_distance = haversine_km(start, end)
        if traversed + segment_distance >= target_distance:
            local_ratio = (target_distance - traversed) / max(segment_distance, 0.001)
            return [
                round(start[0] + (end[0] - start[0]) * local_ratio, 6),
                round(start[1] + (end[1] - start[1]) * local_ratio, 6),
            ]
        traversed += segment_distance

    return path[-1]


def _status_from_progress(progress_ratio):
    if progress_ratio >= 1:
        return "Delivered"
    if progress_ratio >= 0.78:
        return "Approaching destination"
    if progress_ratio >= 0.25:
        return "In transit"
    return "Dispatch initiated"


def _timeline_from_progress(route_snapshot, progress_ratio, generated_at_iso):
    route = route_snapshot["route"]
    route_stages = route_snapshot["decision_support"]["route_stages"]

    if progress_ratio >= 1:
        statuses = ["completed", "completed", "completed", "completed"]
    elif progress_ratio >= 0.65:
        statuses = ["completed", "completed", "active", "planned"]
    elif progress_ratio >= 0.25:
        statuses = ["completed", "active", "planned", "planned"]
    else:
        statuses = ["active", "planned", "planned", "planned"]

    return [
        {
            "id": "origin_dispatch",
            "label": route_stages[0]["stage"],
            "detail": route_stages[0]["detail"],
            "status": statuses[0],
            "location": route["source"],
            "timestamp": generated_at_iso,
        },
        {
            "id": "line_haul",
            "label": route_stages[1]["stage"],
            "detail": route_stages[1]["detail"],
            "status": statuses[1],
            "location": f"{round(route['distance_km'] * min(progress_ratio, 0.6), 1)} km from origin",
            "timestamp": generated_at_iso,
        },
        {
            "id": "transfer_node",
            "label": route_stages[2]["stage"],
            "detail": route_stages[2]["detail"],
            "status": statuses[2],
            "location": route_snapshot["decision_support"]["distribution_model"]["hub_city"],
            "timestamp": generated_at_iso,
        },
        {
            "id": "last_mile",
            "label": route_stages[3]["stage"],
            "detail": route_stages[3]["detail"],
            "status": statuses[3],
            "location": route["destination"],
            "timestamp": generated_at_iso,
        },
    ]


def _build_live_snapshot(record, route_snapshot):
    route = route_snapshot["route"]
    dispatch_started_at = datetime.fromisoformat(record["dispatch_started_at"])
    generated_at = _now_utc()
    elapsed_seconds = max(0.0, (generated_at - dispatch_started_at).total_seconds())
    planned_duration_seconds = max(route["duration_seconds"], 1)
    progress_ratio = _safe_ratio(elapsed_seconds, planned_duration_seconds)
    progress_pct = round(progress_ratio * 100, 2)

    telemetry = record.get("latest_telemetry") or {}
    telemetry_coordinates = telemetry.get("coordinates")
    coordinate_source = "telemetry" if telemetry_coordinates else "computed_live"
    route_line = route.get("geometry_coordinates") or [
        route["source_coordinates"],
        route["destination_coordinates"],
    ]
    current_coordinates = telemetry_coordinates or _interpolate_along_path(
        route_line,
        progress_ratio,
    ) or _interpolate_coordinates(
        route["source_coordinates"],
        route["destination_coordinates"],
        progress_ratio,
    )

    covered_distance_km = round(route["distance_km"] * progress_ratio, 1)
    remaining_distance_km = round(max(0.0, route["distance_km"] - covered_distance_km), 1)
    suggested_mode = route_snapshot["suggested_transport_mode"]

    return {
        "shipment_id": record["shipment_id"],
        "tracking_mode": coordinate_source,
        "generated_at": generated_at.isoformat(),
        "dispatch_started_at": record["dispatch_started_at"],
        "shipment_date": record.get("shipment_date"),
        "source": record["source"],
        "destination": record["destination"],
        "transport_mode": record["transport_mode"],
        "region_type": record["region_type"],
        "current_status": _status_from_progress(progress_ratio),
        "progress_ratio": round(progress_ratio, 4),
        "progress_pct": progress_pct,
        "distance_covered_km": covered_distance_km,
        "distance_remaining_km": remaining_distance_km,
        "current_location": {
            "label": (
                telemetry.get("label")
                or f"{covered_distance_km} km covered"
            ),
            "coordinates": current_coordinates,
        },
        "route_line": route_line,
        "eta_text": route["duration_text"],
        "risk": route_snapshot["risk"],
        "weather": route_snapshot["weather"],
        "weather_outlook": route_snapshot.get("weather_outlook"),
        "intelligence": route_snapshot["intelligence"],
        "decision_support": route_snapshot["decision_support"],
        "suggested_transport_mode": suggested_mode,
        "region_context": route_snapshot.get("region_context"),
        "cargo_profile": route_snapshot.get("cargo_profile"),
        "shipment_pricing": route_snapshot.get("shipment_pricing"),
        "alternate_route_advice": (
            "Alternate corridor or mode switch recommended due to congestion ahead."
            if route["congestion_index"] >= 0.62 or suggested_mode["mode"] != route["transport_mode"]
            else "Primary corridor remains acceptable. Continue monitoring node congestion and weather."
        ),
        "timeline": _timeline_from_progress(
            route_snapshot,
            progress_ratio,
            generated_at.isoformat(),
        ),
    }


def _record_from_payload(payload):
    source = (payload.get("source") or "").strip()
    destination = (payload.get("destination") or "").strip()
    transport_mode = (payload.get("transport_mode") or "").strip().lower()
    region_type = (payload.get("region_type") or "").strip().lower() or None
    shipment_date = (payload.get("shipment_date") or "").strip() or None
    cargo_profile = normalize_cargo_profile(payload.get("cargo") or {})

    if not source or not destination or not transport_mode:
        raise ValidationError(
            "Fields 'source', 'destination', and 'transport_mode' are required."
        )

    return {
        "shipment_id": _shipment_id(source, destination),
        "source": source,
        "destination": destination,
        "transport_mode": transport_mode,
        "region_type": region_type,
        "shipment_date": shipment_date,
        "cargo_profile": cargo_profile,
        "dispatch_started_at": _iso_now(),
        "created_at": _iso_now(),
        "updated_at": _iso_now(),
        "latest_telemetry": None,
    }


def _fetch_route_snapshot(record, config, logger):
    route_snapshot = build_route_snapshot(
        source=record["source"],
        destination=record["destination"],
        transport_mode=record["transport_mode"],
        region_type=record["region_type"],
        cargo=record.get("cargo_profile"),
        config=config,
        logger=logger,
    )
    route_snapshot["intelligence"] = build_supply_chain_intelligence(route_snapshot)
    route_snapshot["india_context"] = build_india_context(route_snapshot)
    route_snapshot["decision_support"] = build_route_decision_support(route_snapshot)
    return route_snapshot


def _persist_record(record, config, logger):
    if supabase_enabled(config):
        safe_create_shipment_record(
            {key: value for key, value in record.items() if key != "cargo_profile"},
            config,
            logger,
        )
        return "supabase"

    with _STORE_LOCK:
        _LOCAL_SHIPMENTS[record["shipment_id"]] = record
    return "memory"


def _load_record(shipment_id, config, logger):
    if supabase_enabled(config):
        record = safe_fetch_shipment_record(shipment_id, config, logger)
    else:
        with _STORE_LOCK:
            record = _LOCAL_SHIPMENTS.get(shipment_id)

    if not record:
        raise ValidationError(f"Shipment '{shipment_id}' was not found.", status_code=404)

    return record


def _update_record(shipment_id, patch_data, config, logger):
    if supabase_enabled(config):
        safe_update_shipment_record(shipment_id, patch_data, config, logger)
        return

    with _STORE_LOCK:
        current = _LOCAL_SHIPMENTS.get(shipment_id)
        if current:
            current.update(patch_data)


def create_tracking_shipment(payload, config, logger):
    record = _record_from_payload(payload)
    route_snapshot = _fetch_route_snapshot(record, config, logger)
    storage_backend = _persist_record(record, config, logger)
    live_snapshot = _build_live_snapshot(record, route_snapshot)
    live_snapshot["storage_backend"] = storage_backend
    live_snapshot["poll_seconds"] = config["TRACKING_POLL_SECONDS"]
    return live_snapshot


def get_tracking_snapshot(shipment_id, config, logger):
    record = _load_record(shipment_id, config, logger)
    route_snapshot = _fetch_route_snapshot(record, config, logger)
    live_snapshot = _build_live_snapshot(record, route_snapshot)
    _update_record(
        shipment_id,
        {
            "updated_at": _iso_now(),
            "last_progress_pct": live_snapshot["progress_pct"],
            "last_status": live_snapshot["current_status"],
            "last_snapshot": live_snapshot,
        },
        config,
        logger,
    )
    live_snapshot["storage_backend"] = "supabase" if supabase_enabled(config) else "memory"
    live_snapshot["poll_seconds"] = config["TRACKING_POLL_SECONDS"]
    return live_snapshot


def ingest_tracking_telemetry(shipment_id, payload, config, logger):
    record = _load_record(shipment_id, config, logger)
    coordinates = payload.get("coordinates")
    label = (payload.get("label") or "").strip() or "Carrier telemetry update"

    if not isinstance(coordinates, list) or len(coordinates) != 2:
        raise ValidationError("Field 'coordinates' must be a [longitude, latitude] array.")

    telemetry = {
        "coordinates": [float(coordinates[0]), float(coordinates[1])],
        "label": label,
        "received_at": _iso_now(),
    }
    record["latest_telemetry"] = telemetry
    _update_record(
        shipment_id,
        {
            "latest_telemetry": telemetry,
            "updated_at": _iso_now(),
        },
        config,
        logger,
    )
    route_snapshot = _fetch_route_snapshot(record, config, logger)
    live_snapshot = _build_live_snapshot(record, route_snapshot)
    live_snapshot["tracking_mode"] = "telemetry"
    live_snapshot["storage_backend"] = "supabase" if supabase_enabled(config) else "memory"
    live_snapshot["poll_seconds"] = config["TRACKING_POLL_SECONDS"]
    return live_snapshot


def build_tracking_health(config):
    return {
        "tracking_available": True,
        "storage_backend": "supabase" if supabase_enabled(config) else "memory",
        "telemetry_ingest_available": True,
        "poll_seconds": config["TRACKING_POLL_SECONDS"],
    }
