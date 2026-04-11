import hashlib
from datetime import datetime

import requests

from app.utils.cache import shared_cache
from app.utils.errors import ExternalAPIError


OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


WEATHER_RISK_FACTORS = {
    "clear": {"label": "stable", "score": 0.1},
    "clouds": {"label": "watch", "score": 0.25},
    "rain": {"label": "delay_risk", "score": 0.55},
    "drizzle": {"label": "delay_risk", "score": 0.45},
    "thunderstorm": {"label": "high_risk", "score": 0.9},
    "snow": {"label": "high_risk", "score": 0.75},
    "mist": {"label": "visibility_risk", "score": 0.4},
    "fog": {"label": "visibility_risk", "score": 0.5},
}


MONSOON_MONTHS = {6, 7, 8, 9}
POST_MONSOON_MONTHS = {10, 11}


def _cache_key(location):
    raw = f"weather::{location.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _seasonal_fallback(location):
    month = datetime.utcnow().month

    if month in MONSOON_MONTHS:
        condition = "rain"
        description = "seasonal monsoon risk fallback"
        rainfall_mm = 18
        visibility_m = 4500
    elif month in POST_MONSOON_MONTHS:
        condition = "clouds"
        description = "post-monsoon watch fallback"
        rainfall_mm = 4
        visibility_m = 6000
    else:
        condition = "clear"
        description = "seasonal stable-weather fallback"
        rainfall_mm = 0
        visibility_m = 8000

    risk_mapping = WEATHER_RISK_FACTORS[condition]
    return {
        "location": location,
        "condition": condition,
        "description": description,
        "temperature": None,
        "humidity": None,
        "wind_speed": None,
        "rainfall_mm": rainfall_mm,
        "visibility_m": visibility_m,
        "visibility_km": round(visibility_m / 1000, 1),
        "pressure_hpa": None,
        "weather_risk_label": risk_mapping["label"],
        "weather_risk_score": risk_mapping["score"],
        "api_source": "seasonal_fallback",
        "is_fallback": True,
    }


def get_weather_for_location(location, config, logger):
    cache_key = _cache_key(location)
    cached = shared_cache.get(cache_key)
    if cached:
        logger.info("Weather cache hit for %s", location)
        return cached

    api_key = config.get("OPENWEATHER_API_KEY")
    if not api_key:
        fallback = _seasonal_fallback(location)
        shared_cache.set(cache_key, fallback, ttl=config["CACHE_TTL_SECONDS"])
        logger.warning("Weather API key missing. Using seasonal fallback for %s", location)
        return fallback

    params = {
        "q": location,
        "appid": api_key,
        "units": config["OPENWEATHER_UNITS"],
    }

    try:
        response = requests.get(
            OPENWEATHER_URL,
            params=params,
            timeout=config["REQUEST_TIMEOUT_SECONDS"],
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        fallback = _seasonal_fallback(location)
        shared_cache.set(cache_key, fallback, ttl=config["CACHE_TTL_SECONDS"])
        logger.warning("Weather request failed for %s. Using fallback. Details: %s", location, exc)
        return fallback

    weather_items = payload.get("weather") or []
    primary_weather = (weather_items[0].get("main", "Clear") if weather_items else "Clear").lower()
    risk_mapping = WEATHER_RISK_FACTORS.get(primary_weather, {"label": "watch", "score": 0.3})
    rainfall_payload = payload.get("rain") or {}
    snowfall_payload = payload.get("snow") or {}
    rainfall_mm = rainfall_payload.get("1h")
    if rainfall_mm is None:
        rainfall_mm = rainfall_payload.get("3h")
    if rainfall_mm is None:
        rainfall_mm = snowfall_payload.get("1h")
    if rainfall_mm is None:
        rainfall_mm = 0
    visibility_m = payload.get("visibility")

    weather_data = {
        "location": location,
        "condition": primary_weather,
        "description": weather_items[0].get("description", "n/a") if weather_items else "n/a",
        "temperature": payload.get("main", {}).get("temp"),
        "humidity": payload.get("main", {}).get("humidity"),
        "wind_speed": payload.get("wind", {}).get("speed"),
        "rainfall_mm": round(float(rainfall_mm), 2),
        "visibility_m": visibility_m,
        "visibility_km": round(float(visibility_m) / 1000, 1) if visibility_m is not None else None,
        "pressure_hpa": payload.get("main", {}).get("pressure"),
        "weather_risk_label": risk_mapping["label"],
        "weather_risk_score": risk_mapping["score"],
        "api_source": "openweather",
        "is_fallback": False,
    }

    shared_cache.set(cache_key, weather_data, ttl=config["CACHE_TTL_SECONDS"])
    return weather_data
