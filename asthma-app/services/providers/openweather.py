"""OpenWeather weather + air pollution — best match to AAMOS training data."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone

import httpx

from model.elena_env_schema import google_pollen_category

AIR_POLLUTION_URL = "https://api.openweathermap.org/data/2.5/air_pollution"
AIR_HISTORY_URL = "https://api.openweathermap.org/data/2.5/air_pollution/history"
ONE_CALL_URL = "https://api.openweathermap.org/data/3.0/onecall"


class OpenWeatherEnvProvider:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY", "")

    async def fetch_daily(self, lat: float, lon: float, day: date) -> dict:
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY is required for openweather provider")

        async with httpx.AsyncClient(timeout=30) as client:
            air = await self._fetch_air(client, lat, lon, day)
            weather = await self._fetch_weather(client, lat, lon, day)
            
            # Wire Google Pollen if API key available
            google_key = os.getenv("GOOGLE_POLLEN_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
            pollen = {}
            if google_key:
                try:
                    pollen = await fetch_google_pollen(lat, lon, google_key)
                except Exception:
                    pass  # Fallback to AAMOS_FALLBACK in env_fetcher

        return {**weather, **air, **pollen}

    async def _fetch_air(self, client: httpx.AsyncClient, lat: float, lon: float, day: date) -> dict:
        today = date.today()
        params = {"lat": lat, "lon": lon, "appid": self.api_key}

        if day >= today:
            r = await client.get(AIR_POLLUTION_URL, params=params)
        else:
            start = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
            end = start + 86400
            r = await client.get(AIR_HISTORY_URL, params={**params, "start": start, "end": end})

        r.raise_for_status()
        readings = r.json().get("list") or []
        if not readings:
            return {}

        # Daily mean across hourly samples
        def avg(key: str) -> float:
            vals = [x["components"][key] for x in readings if key in x.get("components", {})]
            return sum(vals) / len(vals) if vals else None

        aqi_vals = [x["main"]["aqi"] for x in readings if "main" in x]
        aqi = round(sum(aqi_vals) / len(aqi_vals)) if aqi_vals else None

        return {
            "aqi": aqi,
            "co": avg("co"),
            "no": avg("no"),
            "no2": avg("no2"),
            "o3": avg("o3"),
            "so2": avg("so2"),
            "pm2_5": avg("pm2_5"),
            "pm10": avg("pm10"),
            "nh3": avg("nh3"),
        }

    async def _fetch_weather(self, client: httpx.AsyncClient, lat: float, lon: float, day: date) -> dict:
        """One Call 3.0 daily block; falls back to empty dict if plan lacks access."""
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "exclude": "current,minutely,hourly,alerts",
        }
        r = await client.get(ONE_CALL_URL, params=params)
        if r.status_code == 401:
            return {}
        r.raise_for_status()

        day_ts = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
        daily = next((d for d in r.json().get("daily", []) if d.get("dt") == day_ts), None)
        if not daily:
            daily = r.json().get("daily", [{}])[0]

        temp = daily.get("temp", {})
        return {
            "temperature": temp.get("day"),
            "temperature_min": temp.get("min"),
            "temperature_max": temp.get("max"),
            "pressure": daily.get("pressure"),
            "humidity": daily.get("humidity"),
            "wind_speed": daily.get("wind_speed"),
            "wind_deg": daily.get("wind_deg"),
            # One Call 3.0 may include pollen on some plans — extend when available
        }


async def fetch_google_pollen(lat: float, lon: float, api_key: str) -> dict:
    """Optional: grass / tree / weed categories from Google Pollen API."""
    url = "https://pollen.googleapis.com/v1/forecast:lookup"
    params = {"location.latitude": lat, "location.longitude": lon, "days": 1, "key": api_key}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    out = {}
    for day_info in data.get("dailyInfo", []):
        for pt in day_info.get("pollenTypeInfo", []):
            code = pt.get("code", "").upper()
            cat = google_pollen_category(pt.get("indexInfo", {}).get("category", "MODERATE"))
            if code == "GRASS":
                out["grass_pollen"] = cat
            elif code == "TREE":
                out["tree_pollen"] = cat
            elif code == "WEED":
                out["weed_pollen"] = cat
    return out
