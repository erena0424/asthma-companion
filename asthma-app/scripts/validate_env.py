"""Validate /env/daily against AAMOS environment.csv for known user/date.

Compare live API fetch to AAMOS training data for user_key=113, date=1 (Helsinki coords).
"""

import asyncio
import sys
from pathlib import Path

import httpx
import pandas as pd

# AAMOS user 113, date index 1 — Helsinki-ish coords
VALIDATION_LAT = 60.17
VALIDATION_LON = 24.94
AAMOS_USER = 113
AAMOS_DATE_INDEX = 1

AAMOS_ENV_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "anonym_aamos00_environment.csv"
API_BASE = "http://localhost:8000"


async def fetch_live_env(provider: str = "openmeteo") -> dict:
    """Fetch env features from live API."""
    url = f"{API_BASE}/env/daily"
    params = {"lat": VALIDATION_LAT, "lon": VALIDATION_LON, "provider": provider}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


def load_aamos_row() -> dict:
    """Load AAMOS environment.csv row for user 113, date index 1."""
    if not AAMOS_ENV_PATH.exists():
        raise FileNotFoundError(
            f"AAMOS environment.csv not found at {AAMOS_ENV_PATH}\n"
            "Download from https://datashare.ed.ac.uk/items/8478e384-fd1b-4a37-9555-0c6e1218e90b"
        )
    
    df = pd.read_csv(AAMOS_ENV_PATH)
    row = df[(df["user_key"] == AAMOS_USER) & (df["date"] == AAMOS_DATE_INDEX)]
    
    if row.empty:
        raise ValueError(f"No AAMOS row found for user_key={AAMOS_USER}, date={AAMOS_DATE_INDEX}")
    
    return row.iloc[0].to_dict()


def compare_features(aamos: dict, live: dict) -> None:
    """Print side-by-side comparison of 19 env columns."""
    env_cols = [
        "temperature", "temperature_min", "temperature_max",
        "pressure", "humidity", "wind_speed", "wind_deg",
        "aqi", "co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3",
        "grass_pollen", "tree_pollen", "weed_pollen",
    ]
    
    print(f"\n{'Column':<20} {'AAMOS (user 113, date 1)':<30} {'Live API':<30} {'Match':<10}")
    print("=" * 90)
    
    for col in env_cols:
        aamos_val = aamos.get(col, "N/A")
        live_val = live["features"].get(col, "N/A")
        
        # Check if values are close (for numeric) or exact (for categorical)
        if isinstance(aamos_val, (int, float)) and isinstance(live_val, (int, float)):
            match = "✓" if abs(aamos_val - live_val) < 5 else "✗"
        else:
            match = "✓" if str(aamos_val) == str(live_val) else "✗"
        
        print(f"{col:<20} {str(aamos_val):<30} {str(live_val):<30} {match:<10}")
    
    print("\nMissing fields in live API:", live.get("missing", []))
    print("Cached:", live.get("cached", False))
    print("Provider:", live.get("provider", "unknown"))


async def main():
    """Run validation."""
    print("=" * 90)
    print("ENV API VALIDATION — Compare live fetch to AAMOS training data")
    print("=" * 90)
    
    try:
        print("\n[1/2] Loading AAMOS environment.csv row (user 113, date 1)...")
        aamos = load_aamos_row()
        print(f"✓ Loaded AAMOS row: {len(aamos)} columns")
        
        print("\n[2/2] Fetching live env data from API...")
        live = await fetch_live_env(provider="openmeteo")
        print(f"✓ Fetched live data: {len(live['features'])} features")
        
        compare_features(aamos, live)
        
        print("\n" + "=" * 90)
        print("NOTES:")
        print("- AAMOS data is from 2022; live API is today's weather")
        print("- Expect differences in absolute values (different dates)")
        print("- Focus on: no missing fields, correct units, reasonable ranges")
        print("- 'no' may be missing in Open-Meteo (use OpenWeather for production)")
        print("=" * 90)
        
    except FileNotFoundError as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
