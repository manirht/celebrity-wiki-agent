from __future__ import annotations

"""Weather API tool wrapping Open-Meteo.

Exposed as a LangChain tool so it can be called from the LangGraph workflow.
"""

from typing import Dict

import httpx
from langchain_core.tools import tool

from app.config import WeatherConfig


def _geocode_city(cfg: WeatherConfig, city: str, country: str) -> Dict:
    """Synchronous helper to geocode a city using Open-Meteo."""

    params = {"name": city, "count": 1, "language": "en", "format": "json"}
    if country:
        params["country"] = country
    resp = httpx.get(cfg.base_geocoding_url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("results"):
        raise ValueError(f"No geocoding results for {city}, {country}")
    return data["results"][0]


def _get_weather(cfg: WeatherConfig, lat: float, lon: float) -> Dict:
    """Synchronous helper to fetch current weather from Open-Meteo."""

    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
    }
    resp = httpx.get(cfg.base_weather_url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


@tool("get_current_weather")
def get_current_weather(city: str, country: str = "") -> Dict:
    """Get current weather for a city using Open-Meteo.

    Returns a dict with keys: temperature_c, windspeed, weather_code, source_url.
    The source_url can be cited directly in the final report.
    """

    # Handle empty city gracefully
    if not city or not city.strip():
        return {
            "city": "",
            "country": country,
            "latitude": None,
            "longitude": None,
            "temperature_c": None,
            "windspeed": None,
            "weather_code": None,
            "source_url": "",
            "error": "No city provided"
        }

    cfg = WeatherConfig()
    try:
        geo = _geocode_city(cfg, city, country)
    except ValueError as e:
        return {
            "city": city,
            "country": country,
            "latitude": None,
            "longitude": None,
            "temperature_c": None,
            "windspeed": None,
            "weather_code": None,
            "source_url": "",
            "error": str(e)
        }
    lat = float(geo["latitude"])
    lon = float(geo["longitude"])
    weather = _get_weather(cfg, lat, lon)

    current = weather.get("current_weather") or {}
    # Construct a representative API URL for citation.
    source_url = (
        f"{cfg.base_weather_url}?latitude={lat}&longitude={lon}&current_weather=true"
    )

    return {
        "city": city,
        "country": country,
        "latitude": lat,
        "longitude": lon,
        "temperature_c": current.get("temperature"),
        "windspeed": current.get("windspeed"),
        "weather_code": current.get("weathercode"),
        "source_url": source_url,
    }

