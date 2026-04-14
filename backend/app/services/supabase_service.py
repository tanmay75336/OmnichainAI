import requests

from app.utils.errors import ExternalAPIError


def supabase_enabled(config):
    return bool(
        (config.get("SUPABASE_URL") or "").strip()
        and (config.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    )


def _headers(config):
    token = (config.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return {
        "apikey": token,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _table_url(config):
    base_url = (config.get("SUPABASE_URL") or "").strip().rstrip("/")
    table = (config.get("SUPABASE_SHIPMENTS_TABLE") or "shipment_tracking").strip()
    return f"{base_url}/rest/v1/{table}"


def get_shipment_record(shipment_id, config):
    response = requests.get(
        _table_url(config),
        headers=_headers(config),
        params={
            "shipment_id": f"eq.{shipment_id}",
            "select": "*",
            "limit": 1,
        },
        timeout=config["REQUEST_TIMEOUT_SECONDS"],
    )
    response.raise_for_status()
    payload = response.json()
    return payload[0] if payload else None


def create_shipment_record(record, config):
    response = requests.post(
        _table_url(config),
        headers={
            **_headers(config),
            "Prefer": "return=representation",
        },
        json=record,
        timeout=config["REQUEST_TIMEOUT_SECONDS"],
    )
    response.raise_for_status()
    payload = response.json()
    return payload[0] if payload else record


def update_shipment_record(shipment_id, patch_data, config):
    response = requests.patch(
        _table_url(config),
        headers={
            **_headers(config),
            "Prefer": "return=representation",
        },
        params={"shipment_id": f"eq.{shipment_id}", "select": "*"},
        json=patch_data,
        timeout=config["REQUEST_TIMEOUT_SECONDS"],
    )
    response.raise_for_status()
    payload = response.json()
    return payload[0] if payload else patch_data


def safe_fetch_shipment_record(shipment_id, config, logger):
    try:
        return get_shipment_record(shipment_id, config)
    except requests.RequestException as exc:
        logger.warning("Supabase fetch failed for %s: %s", shipment_id, exc)
        raise ExternalAPIError("Failed to fetch shipment from Supabase.") from exc


def safe_create_shipment_record(record, config, logger):
    try:
        return create_shipment_record(record, config)
    except requests.RequestException as exc:
        logger.warning("Supabase create failed for %s: %s", record.get("shipment_id"), exc)
        raise ExternalAPIError("Failed to persist shipment to Supabase.") from exc


def safe_update_shipment_record(shipment_id, patch_data, config, logger):
    try:
        return update_shipment_record(shipment_id, patch_data, config)
    except requests.RequestException as exc:
        logger.warning("Supabase update failed for %s: %s", shipment_id, exc)
        raise ExternalAPIError("Failed to update shipment in Supabase.") from exc
