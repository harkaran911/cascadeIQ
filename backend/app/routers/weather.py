"""
Weather router — proxies OpenWeatherMap data and triggers zone severity updates.
"""
from fastapi import APIRouter, HTTPException
from app.core.config import settings
import httpx

router = APIRouter()

OWM_BASE = "https://api.openweathermap.org/data/2.5"

# Ludhiana — largest city on Sutlej basin; best proxy for regional flood conditions
DEFAULT_LAT = 30.9010
DEFAULT_LON = 75.8573


@router.get("/current")
async def current_weather(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
    """Fetch current weather conditions for a location."""
    if settings.OPENWEATHER_API_KEY == "demo":
        # Return mock data for demo mode
        return _mock_weather(lat, lon)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{OWM_BASE}/weather",
            params={"lat": lat, "lon": lon, "appid": settings.OPENWEATHER_API_KEY, "units": "metric"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="OpenWeatherMap error")
    data = resp.json()
    return {
        "location": data.get("name"),
        "temp_c": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "description": data["weather"][0]["description"],
        "wind_speed_ms": data["wind"]["speed"],
        "rain_1h_mm": data.get("rain", {}).get("1h", 0.0),
    }


@router.get("/forecast")
async def rainfall_forecast(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
    """3-day rainfall forecast — used to pre-position resources (PRO Stage A)."""
    if settings.OPENWEATHER_API_KEY == "demo":
        return _mock_forecast()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{OWM_BASE}/forecast",
            params={"lat": lat, "lon": lon, "appid": settings.OPENWEATHER_API_KEY, "units": "metric", "cnt": 24},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="OpenWeatherMap error")
    items = resp.json()["list"]
    return [
        {
            "dt": i["dt"],
            "rain_3h_mm": i.get("rain", {}).get("3h", 0.0),
            "temp_c": i["main"]["temp"],
        }
        for i in items
    ]


def _mock_weather(lat, lon):
    return {
        "location": "Ludhiana (demo)",
        "lat": lat, "lon": lon,
        "temp_c": 28.4,
        "humidity": 88,
        "description": "heavy intensity rain",
        "wind_speed_ms": 6.2,
        "rain_1h_mm": 14.5,
    }


def _mock_forecast():
    import time
    now = int(time.time())
    return [
        {"dt": now + i * 10800, "rain_3h_mm": [18, 22, 15, 8, 5, 3, 2, 1][i % 8], "temp_c": 27.0}
        for i in range(8)
    ]
