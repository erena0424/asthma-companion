"""Elena environment feature schema — 19 columns for classifier parity."""

from __future__ import annotations

ENV_FEATURE_COLUMNS = [
    "temperature",
    "temperature_min",
    "temperature_max",
    "pressure",
    "humidity",
    "wind_speed",
    "wind_deg",
    "aqi",
    "co",
    "no",
    "no2",
    "o3",
    "so2",
    "pm2_5",
    "pm10",
    "nh3",
    "grass_pollen",
    "tree_pollen",
    "weed_pollen",
]

POLLEN_LEVELS = ("Low", "Moderate", "High", "Very High")

POLLEN_BUCKETS = [
    (0, 20, "Low"),
    (20, 100, "Moderate"),
    (100, 300, "High"),
    (300, float("inf"), "Very High"),
]

AAMOS_FALLBACK = {
    "grass_pollen": "Moderate",
    "tree_pollen": "Low",
    "weed_pollen": "Low",
    "nh3": 1.28,
}


def grains_to_pollen_category(grains: float) -> str:
    for low, high, label in POLLEN_BUCKETS:
        if low <= grains < high:
            return label
    return "Very High"


def us_aqi_to_openweather_band(us_aqi: float) -> int:
    if us_aqi <= 50:
        return 1
    if us_aqi <= 100:
        return 2
    if us_aqi <= 150:
        return 3
    if us_aqi <= 200:
        return 4
    return 5


def google_pollen_category(category: str) -> str:
    mapping = {
        "LOW": "Low",
        "MODERATE": "Moderate",
        "HIGH": "High",
        "VERY_HIGH": "Very High",
    }
    return mapping.get(category.upper().replace(" ", "_"), "Moderate")


def validate_env_features(features: dict) -> tuple[dict, list[str]]:
    """Ensure all 19 env columns exist; fill fallbacks and track missing."""
    out = dict(features)
    missing: list[str] = []

    for col in ENV_FEATURE_COLUMNS:
        if out.get(col) is None:
            if col in AAMOS_FALLBACK:
                out[col] = AAMOS_FALLBACK[col]
            else:
                missing.append(col)

    for col in ("grass_pollen", "tree_pollen", "weed_pollen"):
        if out.get(col) not in POLLEN_LEVELS:
            if col not in missing:
                missing.append(col)
            out[col] = AAMOS_FALLBACK.get(col, "Moderate")

    return out, missing
