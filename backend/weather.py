"""
Weather lookup for Heat-Shield.

Uses Open-Meteo (https://open-meteo.com) instead of OpenWeatherMap:
- No API key / signup required — one less thing to break during a demo
- Free, no rate-limit headaches
- Returns current temperature (C) and relative humidity (%)

If you'd rather use OpenWeatherMap (e.g. you already have a key), swap the
implementation of get_current_weather() below — the return shape is what
matters to the rest of the app.
"""
import time
import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Weather doesn't change meaningfully second-to-second, and a demo can hammer
# this endpoint fast (every chip click / slider drag triggers a reading).
# Cache by rounded coordinates for a few minutes to keep things snappy and
# avoid rate limits.
_CACHE_TTL_SECONDS = 180
_cache: dict = {}  # (lat_r, lon_r) -> (timestamp, weather_dict)


class WeatherError(Exception):
    pass


def get_current_weather(lat: float, lon: float) -> dict:
    """
    Returns: {"temp_c": float, "humidity": float, "source": "open-meteo"}
    Raises WeatherError if the lookup fails.
    """
    key = (round(lat, 2), round(lon, 2))
    cached = _cache.get(key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    try:
        resp = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m",
                "timezone": "auto",
            },
            timeout=6,
        )
        resp.raise_for_status()
        data = resp.json()
        current = data["current"]
        result = {
            "temp_c": round(float(current["temperature_2m"]), 1),
            "humidity": round(float(current["relative_humidity_2m"]), 1),
            "source": "open-meteo",
        }
        _cache[key] = (time.time(), result)
        return result
    except Exception as e:
        raise WeatherError(f"weather lookup failed: {e}")
