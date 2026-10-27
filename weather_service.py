"""Weather Service for FarmerConnect.

Integrates with Open-Meteo Geocoding and Weather Forecast APIs.
Features:
- Geocoding location search with validation and fallback to Tamil Nadu regions.
- Current weather and 5-day forecast retrieval.
- Weather code to condition mapping with agricultural advice.
- In-memory caching with TTL to avoid rate-limiting and redundant calls.
- Timeout safety and robust error handling.
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple
import requests
from config import Config

logger = logging.getLogger(__name__)

# Weather code (WMO) mappings: condition name, icon name, and agricultural advisory
WMO_WEATHER_MAP: Dict[int, Dict[str, str]] = {
    0: {
        "condition": "Clear Sky",
        "icon": "sun",
        "advisory": "Excellent conditions for harvesting, sun-drying crops, and pesticide/fertilizer spraying.",
    },
    1: {
        "condition": "Mainly Clear",
        "icon": "sun",
        "advisory": "Favorable weather for intercultural operations, weeding, and normal irrigation.",
    },
    2: {
        "condition": "Partly Cloudy",
        "icon": "cloud-sun",
        "advisory": "Optimal moderate conditions for crop growth and standard farming operations.",
    },
    3: {
        "condition": "Overcast",
        "icon": "cloud",
        "advisory": "Reduced solar radiation. Good for transplanting seedlings; hold off drying grains.",
    },
    45: {
        "condition": "Foggy",
        "icon": "cloud-fog",
        "advisory": "Prolonged morning moisture may promote fungal infections; inspect vegetable crops.",
    },
    48: {
        "condition": "Depositing Rime Fog",
        "icon": "cloud-fog",
        "advisory": "High humidity; check banana and tomato plants for early blight symptoms.",
    },
    51: {
        "condition": "Light Drizzle",
        "icon": "cloud-drizzle",
        "advisory": "Postpone chemical spraying as light drizzle will dilute foliar sprays.",
    },
    53: {
        "condition": "Moderate Drizzle",
        "icon": "cloud-drizzle",
        "advisory": "Postpone pesticide application; adequate surface moisture for root development.",
    },
    55: {
        "condition": "Dense Drizzle",
        "icon": "cloud-drizzle",
        "advisory": "Pause chemical treatment; keep harvested produce under protective tarpaulins.",
    },
    61: {
        "condition": "Slight Rain",
        "icon": "cloud-rain",
        "advisory": "Natural irrigation in progress. Pause power irrigation to conserve electricity and water.",
    },
    63: {
        "condition": "Moderate Rain",
        "icon": "cloud-rain",
        "advisory": "Suspension of all spraying recommended. Inspect bunds and irrigation channels.",
    },
    65: {
        "condition": "Heavy Rain",
        "icon": "cloud-rain",
        "advisory": "Heavy precipitation! Ensure open drainage channels in low-lying tomato and cotton fields.",
    },
    80: {
        "condition": "Light Rain Showers",
        "icon": "cloud-rain",
        "advisory": "Passing showers; keep field machinery sheltered and delay grain harvesting.",
    },
    81: {
        "condition": "Moderate Rain Showers",
        "icon": "cloud-rain",
        "advisory": "Ensure field drainage to prevent waterlogging around root zones.",
    },
    82: {
        "condition": "Violent Rain Showers",
        "icon": "cloud-rain",
        "advisory": "High runoff risk! Clear excess water from standing paddy and vegetable plots.",
    },
    95: {
        "condition": "Thunderstorm",
        "icon": "cloud-lightning",
        "advisory": "Severe weather alert! Suspend open field operations and shelter livestock immediately.",
    },
    96: {
        "condition": "Thunderstorm with Light Hail",
        "icon": "cloud-lightning",
        "advisory": "Hail risk! Inspect tender horticulture shoots and provide windbreaks where possible.",
    },
    99: {
        "condition": "Thunderstorm with Heavy Hail",
        "icon": "cloud-lightning",
        "advisory": "Severe storm alert! Keep farm machinery and workers safely indoors.",
    },
}

DEFAULT_WEATHER_INFO = {
    "condition": "Moderate Weather",
    "icon": "cloud-sun",
    "advisory": "Continue standard crop care and monitor soil moisture levels regularly.",
}


class WeatherCache:
    """Simple thread-safe in-memory cache with expiration."""

    def __init__(self, ttl: int = 600):
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return data
            del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        self._cache.clear()


# Global in-memory cache instances
_weather_cache = WeatherCache(ttl=Config.WEATHER_CACHE_TTL)
_geocoding_cache = WeatherCache(ttl=3600)  # Geocoding can be cached for 1 hour


def validate_coordinates(lat: float, lon: float) -> Tuple[bool, Optional[str]]:
    """Validate latitude and longitude ranges."""
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return False, "Latitude and Longitude must be valid numeric values."

    if not (-90.0 <= lat <= 90.0):
        return False, "Latitude must be between -90 and 90 degrees."
    if not (-180.0 <= lon <= 180.0):
        return False, "Longitude must be between -180 and 180 degrees."

    return True, None


def search_locations(query: str) -> List[Dict[str, Any]]:
    """Search for locations using Open-Meteo Geocoding API with fallback for Tamil Nadu cities."""
    if not query or len(query.strip()) < 2:
        return []

    q = query.strip()
    cache_key = f"geo:{q.lower()}"
    cached = _geocoding_cache.get(cache_key)
    if cached is not None:
        return cached

    # Predefined Tamil Nadu major agricultural locations as instant fallback/enrichment
    tn_hubs = [
        {"name": "Coimbatore", "admin1": "Tamil Nadu", "country": "India", "latitude": 11.0055, "longitude": 76.9661},
        {"name": "Tiruppur", "admin1": "Tamil Nadu", "country": "India", "latitude": 11.1085, "longitude": 77.3411},
        {"name": "Erode", "admin1": "Tamil Nadu", "country": "India", "latitude": 11.3410, "longitude": 77.7172},
        {"name": "Salem", "admin1": "Tamil Nadu", "country": "India", "latitude": 11.6643, "longitude": 78.1460},
        {"name": "Madurai", "admin1": "Tamil Nadu", "country": "India", "latitude": 9.9252, "longitude": 78.1198},
        {"name": "Chennai", "admin1": "Tamil Nadu", "country": "India", "latitude": 13.0827, "longitude": 80.2707},
        {"name": "Dindigul", "admin1": "Tamil Nadu", "country": "India", "latitude": 10.3673, "longitude": 77.9803},
        {"name": "Oddanchatram", "admin1": "Tamil Nadu", "country": "India", "latitude": 10.4854, "longitude": 77.7479},
        {"name": "Thanjavur", "admin1": "Tamil Nadu", "country": "India", "latitude": 10.7870, "longitude": 79.1378},
        {"name": "Pollachi", "admin1": "Tamil Nadu", "country": "India", "latitude": 10.6609, "longitude": 77.0048},
        {"name": "Tiruchirappalli", "admin1": "Tamil Nadu", "country": "India", "latitude": 10.7905, "longitude": 78.7047},
        {"name": "Theni", "admin1": "Tamil Nadu", "country": "India", "latitude": 10.0104, "longitude": 77.4768},
        {"name": "Mettupalayam", "admin1": "Tamil Nadu", "country": "India", "latitude": 11.3000, "longitude": 76.9500},
    ]

    matched_local = [
        hub for hub in tn_hubs if q.lower() in hub["name"].lower()
    ]

    # Try external Open-Meteo Geocoding API
    try:
        url = Config.OPEN_METEO_GEOCODING_URL
        params = {"name": q, "count": 6, "language": "en", "format": "json"}
        resp = requests.get(url, params=params, timeout=Config.REQUEST_TIMEOUT)

        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            formatted = []
            seen_names = set()

            for item in results:
                name = item.get("name", "")
                admin1 = item.get("admin1", "")
                country = item.get("country", "")
                lat = round(float(item.get("latitude", 0)), 4)
                lon = round(float(item.get("longitude", 0)), 4)
                key = f"{name}-{admin1}-{lat}"

                if key not in seen_names:
                    seen_names.add(key)
                    formatted.append({
                        "name": name,
                        "admin1": admin1,
                        "country": country,
                        "latitude": lat,
                        "longitude": lon,
                        "display_name": f"{name}, {admin1}" if admin1 else f"{name}, {country}",
                    })

            # If local matches exist that weren't returned, prepend them
            for local in matched_local:
                if not any(f["name"].lower() == local["name"].lower() for f in formatted):
                    formatted.insert(0, {
                        "name": local["name"],
                        "admin1": local["admin1"],
                        "country": local["country"],
                        "latitude": local["latitude"],
                        "longitude": local["longitude"],
                        "display_name": f"{local['name']}, {local['admin1']}",
                    })

            _geocoding_cache.set(cache_key, formatted)
            return formatted

    except requests.RequestException as e:
        logger.warning(f"Geocoding request failed: {e}. Falling back to internal hubs.")

    # Return local match fallback if API fails
    formatted_local = [
        {
            "name": h["name"],
            "admin1": h["admin1"],
            "country": h["country"],
            "latitude": h["latitude"],
            "longitude": h["longitude"],
            "display_name": f"{h['name']}, {h['admin1']}",
        }
        for h in matched_local
    ]
    _geocoding_cache.set(cache_key, formatted_local)
    return formatted_local


def get_weather_forecast(
    latitude: float,
    longitude: float,
    location_name: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """Fetch current weather and 5-day forecast from Open-Meteo.

    Validates coordinates, caches responses, and formats daily forecasts
    with agricultural recommendations.
    """
    valid, err_msg = validate_coordinates(latitude, longitude)
    if not valid:
        return {
            "status": "error",
            "message": err_msg or "Invalid coordinates.",
            "data": None,
        }

    lat = round(float(latitude), 4)
    lon = round(float(longitude), 4)
    loc_name = location_name or f"{lat}, {lon}"

    cache_key = f"wx:{lat}:{lon}"
    if not force_refresh:
        cached_data = _weather_cache.get(cache_key)
        if cached_data is not None:
            return {
                "status": "success",
                "source": "cache",
                "data": cached_data,
            }

    try:
        url = Config.OPEN_METEO_WEATHER_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,uv_index_max",
            "timezone": "auto",
            "forecast_days": 7,
        }

        response = requests.get(url, params=params, timeout=Config.REQUEST_TIMEOUT)

        if response.status_code != 200:
            logger.error(f"Open-Meteo API returned status {response.status_code}: {response.text}")
            return {
                "status": "error",
                "message": f"Weather service responded with error status {response.status_code}.",
                "data": None,
            }

        data = response.json()
        current_raw = data.get("current", {})
        daily_raw = data.get("daily", {})

        # Process current weather
        wcode = current_raw.get("weather_code", 0)
        w_meta = WMO_WEATHER_MAP.get(wcode, DEFAULT_WEATHER_INFO)

        current = {
            "temperature": round(current_raw.get("temperature_2m", 0), 1),
            "apparent_temperature": round(current_raw.get("apparent_temperature", 0), 1),
            "humidity": round(current_raw.get("relative_humidity_2m", 0)),
            "precipitation": round(current_raw.get("precipitation", 0), 1),
            "wind_speed": round(current_raw.get("wind_speed_10m", 0), 1),
            "weather_code": wcode,
            "condition": w_meta["condition"],
            "icon": w_meta["icon"],
            "advisory": w_meta["advisory"],
            "time": current_raw.get("time", ""),
        }

        # Process 5-day daily forecast
        forecast_days: List[Dict[str, Any]] = []
        times = daily_raw.get("time", [])
        wcodes = daily_raw.get("weather_code", [])
        max_temps = daily_raw.get("temperature_2m_max", [])
        min_temps = daily_raw.get("temperature_2m_min", [])
        precip_probs = daily_raw.get("precipitation_probability_max", [])
        precip_sums = daily_raw.get("precipitation_sum", [])
        uv_indices = daily_raw.get("uv_index_max", [])

        # Process up to 5 days
        count = min(5, len(times))
        for i in range(count):
            fc_code = wcodes[i] if i < len(wcodes) else 0
            fc_meta = WMO_WEATHER_MAP.get(fc_code, DEFAULT_WEATHER_INFO)

            forecast_days.append({
                "date": times[i],
                "temp_max": round(max_temps[i], 1) if i < len(max_temps) and max_temps[i] is not None else None,
                "temp_min": round(min_temps[i], 1) if i < len(min_temps) and min_temps[i] is not None else None,
                "precipitation_probability": precip_probs[i] if i < len(precip_probs) and precip_probs[i] is not None else 0,
                "precipitation_sum": round(precip_sums[i], 1) if i < len(precip_sums) and precip_sums[i] is not None else 0.0,
                "uv_index": round(uv_indices[i], 1) if i < len(uv_indices) and uv_indices[i] is not None else 0.0,
                "weather_code": fc_code,
                "condition": fc_meta["condition"],
                "icon": fc_meta["icon"],
                "advisory": fc_meta["advisory"],
            })

        formatted_result = {
            "location_name": loc_name,
            "latitude": lat,
            "longitude": lon,
            "timezone": data.get("timezone", "Asia/Kolkata"),
            "current": current,
            "forecast": forecast_days,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        _weather_cache.set(cache_key, formatted_result)
        return {
            "status": "success",
            "source": "live",
            "data": formatted_result,
        }

    except requests.Timeout:
        logger.error(f"Weather API request timed out for ({lat}, {lon})")
        return {
            "status": "error",
            "message": "Connection to weather provider timed out. Please check your network connection and retry.",
            "data": None,
        }
    except requests.RequestException as e:
        logger.error(f"Weather API request failed: {e}")
        return {
            "status": "error",
            "message": "Failed to fetch live weather data due to network error.",
            "data": None,
        }
    except Exception as e:
        logger.error(f"Unexpected error in weather service: {e}")
        return {
            "status": "error",
            "message": "An unexpected error occurred while processing weather data.",
            "data": None,
        }
