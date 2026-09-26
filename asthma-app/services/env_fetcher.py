"""Environment data orchestrator — provider switch, cache, Elena feature validation."""

from __future__ import annotations

import os
import time
from datetime import date, timedelta

from dotenv import load_dotenv

from model.elena_env_schema import validate_env_features
from services.providers.openmeteo import OpenMeteoEnvProvider
from services.providers.openweather import OpenWeatherEnvProvider

load_dotenv()

_cache: dict[tuple, tuple[float, dict]] = {}
CACHE_TTL_TODAY = int(os.getenv("ENV_CACHE_TTL_SECONDS", "21600"))
CACHE_TTL_PAST = 7 * 24 * 3600


def _cache_key(lat: float, lon: float, day: date, provider: str) -> tuple:
    return (round(lat, 2), round(lon, 2), day.isoformat(), provider)


def _cache_ttl(day: date) -> int:
    return CACHE_TTL_TODAY if day >= date.today() else CACHE_TTL_PAST


def _get_provider(name: str):
    if name == "openweather":
        return OpenWeatherEnvProvider()
    return OpenMeteoEnvProvider()


async def fetch_env_daily(
    lat: float,
    lon: float,
    day: date | None = None,
    provider: str | None = None,
) -> dict:
    """Fetch one Elena-compatible env row for a location and calendar date."""
    day = day or date.today()
    provider = provider or os.getenv("ENV_PROVIDER", "openmeteo")
    if provider not in ("openweather", "openmeteo"):
        raise ValueError(f"Unknown provider '{provider}'. Use openweather or openmeteo.")

    key = _cache_key(lat, lon, day, provider)
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached[0] < _cache_ttl(day):
        result = dict(cached[1])
        result["cached"] = True
        return result

    raw = await _get_provider(provider).fetch_daily(lat, lon, day)
    features, missing = validate_env_features(raw)

    result = {
        "date": day.isoformat(),
        "lat": lat,
        "lon": lon,
        "provider": provider,
        "features": features,
        "missing": missing,
        "cached": False,
    }
    max_entries = int(os.getenv("ENV_CACHE_MAX_ENTRIES", "5000"))
    if len(_cache) >= max_entries and _cache:
        _cache.pop(next(iter(_cache)))
    _cache[key] = (now, result)
    return result
