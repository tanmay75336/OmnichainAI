import hashlib

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


def _cache_key(location):
    raw = f"weather::{location.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_weather_for_location(location, config, logger):
    cache_key = _cache_key(location)
    cached = shared_cache.get(cache_key)
    if cached:
        logger.info("Weather cache hit for %s", location)
        return cached

    api_key = config.get("OPENWEATHER_API_KEY")
    if not api_key:
        raise ExternalAPIError("OPENWEATHER_API_KEY is not configured.")

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
        raise ExternalAPIError("Failed to fetch weather data.") from exc

    weather_items = payload.get("weather") or []
    primary_weather = (weather_items[0].get("main", "Clear") if weather_items else "Clear").lower()
    risk_mapping = WEATHER_RISK_FACTORS.get(primary_weather, {"label": "watch", "score": 0.3})

    weather_data = {
        "location": location,
        "condition": primary_weather,
        "description": weather_items[0].get("description", "n/a") if weather_items else "n/a",
        "temperature": payload.get("main", {}).get("temp"),
        "humidity": payload.get("main", {}).get("humidity"),
        "wind_speed": payload.get("wind", {}).get("speed"),
        "weather_risk_label": risk_mapping["label"],
        "weather_risk_score": risk_mapping["score"],
        "api_source": "openweather",
    }

    shared_cache.set(cache_key, weather_data, ttl=config["CACHE_TTL_SECONDS"])
    return weather_data
