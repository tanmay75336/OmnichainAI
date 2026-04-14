import hashlib
from datetime import datetime

import requests

from app.utils.cache import shared_cache


OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


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


def _forecast_cache_key(latitude, longitude):
    raw = f"forecast::{round(latitude, 4)}::{round(longitude, 4)}"
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


def _map_weather_code(code):
    if code in {0, 1}:
        return "clear"
    if code in {2, 3, 45, 48}:
        return "clouds"
    if code in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        return "rain"
    if code in {71, 73, 75, 77, 85, 86}:
        return "snow"
    if code in {95, 96, 99}:
        return "thunderstorm"
    return "watch"


def _route_outlook_fallback(route_locations, current_weather):
    base_temperature = current_weather.get("temperature") or 28
    base_condition = current_weather.get("condition") or "clear"
    outlook = []

    for day in range(7):
        outlook.append(
            {
                "date_index": day,
                "date": None,
                "avg_temp_c": round(base_temperature + ((day % 3) - 1), 1),
                "min_temp_c": round(base_temperature - 3, 1),
                "max_temp_c": round(base_temperature + 4, 1),
                "condition": base_condition,
                "condition_label": base_condition.replace("_", " ").title(),
                "sample_count": len(route_locations),
                "is_fallback": True,
            }
        )

    return outlook


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


def _fetch_point_forecast(latitude, longitude, config, logger):
    cache_key = _forecast_cache_key(latitude, longitude)
    cached = shared_cache.get(cache_key)
    if cached:
        logger.info("Forecast cache hit for %.4f, %.4f", latitude, longitude)
        return cached

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "weathercode,temperature_2m_max,temperature_2m_min",
        "forecast_days": 7,
        "timezone": "auto",
    }

    response = requests.get(
        OPEN_METEO_FORECAST_URL,
        params=params,
        timeout=config["REQUEST_TIMEOUT_SECONDS"],
    )
    response.raise_for_status()
    payload = response.json()
    daily = payload.get("daily") or {}

    forecast = []
    dates = daily.get("time") or []
    codes = daily.get("weathercode") or []
    mins = daily.get("temperature_2m_min") or []
    maxes = daily.get("temperature_2m_max") or []

    for index, date in enumerate(dates):
        min_temp = mins[index] if index < len(mins) else None
        max_temp = maxes[index] if index < len(maxes) else None
        condition = _map_weather_code(codes[index] if index < len(codes) else None)
        forecast.append(
            {
                "date": date,
                "min_temp_c": min_temp,
                "max_temp_c": max_temp,
                "avg_temp_c": round(((min_temp or 0) + (max_temp or 0)) / 2, 1) if min_temp is not None and max_temp is not None else None,
                "condition": condition,
            }
        )

    shared_cache.set(cache_key, forecast, ttl=config["CACHE_TTL_SECONDS"])
    return forecast


def get_route_weather_outlook(route_locations, current_weather, config, logger):
    sample_locations = [location for location in (route_locations or []) if location and location.get("coordinates")]
    if not sample_locations:
        return _route_outlook_fallback([], current_weather)

    point_forecasts = []
    for location in sample_locations:
        longitude, latitude = location["coordinates"]
        try:
            point_forecasts.append(
                _fetch_point_forecast(latitude, longitude, config, logger)
            )
        except (requests.RequestException, ValueError) as exc:
            logger.warning(
                "Forecast request failed for %.4f, %.4f: %s",
                latitude,
                longitude,
                exc,
            )
            return _route_outlook_fallback(sample_locations, current_weather)

    outlook = []
    day_count = min(len(forecast) for forecast in point_forecasts) if point_forecasts else 0
    for index in range(day_count):
        day_entries = [forecast[index] for forecast in point_forecasts if len(forecast) > index]
        if not day_entries:
            continue

        avg_temp = round(
            sum(entry["avg_temp_c"] for entry in day_entries if entry["avg_temp_c"] is not None)
            / max(sum(1 for entry in day_entries if entry["avg_temp_c"] is not None), 1),
            1,
        )
        min_temp = min(entry["min_temp_c"] for entry in day_entries if entry["min_temp_c"] is not None)
        max_temp = max(entry["max_temp_c"] for entry in day_entries if entry["max_temp_c"] is not None)

        condition_scores = {}
        for entry in day_entries:
            condition = entry["condition"]
            condition_scores[condition] = condition_scores.get(condition, 0) + 1
        dominant_condition = max(condition_scores.items(), key=lambda item: item[1])[0]

        outlook.append(
            {
                "date_index": index,
                "date": day_entries[0]["date"],
                "avg_temp_c": avg_temp,
                "min_temp_c": min_temp,
                "max_temp_c": max_temp,
                "condition": dominant_condition,
                "condition_label": dominant_condition.replace("_", " ").title(),
                "sample_count": len(day_entries),
                "is_fallback": False,
            }
        )

    if not outlook:
        return _route_outlook_fallback(sample_locations, current_weather)

    return outlook
