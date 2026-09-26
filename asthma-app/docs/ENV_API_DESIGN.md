# Environment API — Design (Elena feature parity)

Elena's model expects **19 environment columns** per `(user, date)` plus user/device fields. This doc covers how to fetch the env block at inference time.

## Feature map

| Elena column | AAMOS source (training) | Live API source | Notes |
|---|---|---|---|
| `temperature` | OpenWeather daily mean °C | Open-Meteo `temperature_2m_mean` **or** OW One Call daily | Match daily aggregate, not instant |
| `temperature_min` | OW daily min | Open-Meteo `temperature_2m_min` / OW `temp.min` | |
| `temperature_max` | OW daily max | Open-Meteo `temperature_2m_max` / OW `temp.max` | |
| `pressure` | hPa | Open-Meteo `surface_pressure` (already hPa) | AAMOS uses ~1015 hPa; do **not** divide by 100 |
| `humidity` | % | Open-Meteo `relative_humidity_2m_mean` | 0–100 |
| `wind_speed` | m/s | Open-Meteo `wind_speed_10m_max` or mean | |
| `wind_deg` | 0–360 | Open-Meteo `wind_direction_10m_dominant` | Dominant direction for the day |
| `aqi` | **1–5** (OW scale) | **OpenWeather Air Pollution** `main.aqi` | Do **not** use US/EU raw AQI without mapping |
| `co`, `no`, `no2`, `o3`, `so2`, `pm2_5`, `pm10`, `nh3` | μg/m³ | OW Air Pollution `components.*` | Daily mean of hourly/current readings |
| `grass_pollen` | category | Pollen provider → bucket | `Low` / `Moderate` / `High` / `Very High` |
| `tree_pollen` | category | Pollen provider → bucket | Same |
| `weed_pollen` | category | Pollen provider → bucket | Same |

**Not from env API** (App / user history):

| Elena column | Source |
|---|---|
| `sleep_minutes_lag`, `sedentary_minutes_lag`, `running_minutes_lag`, `total_steps_lag`, `avg_hr_lag` | HealthKit / watch sync; store per user per day |
| `is_flare_up` | Today's questionnaire: `(puffs ≥ 3) OR (night AND day AND limit_activity)` |

## Recommended API stack

AAMOS `anonym_aamos00_environment.csv` matches **OpenWeather** air pollution (AQI 1–5, pollutant names/units). Use OW for pollutants; add weather + pollen from the options below.

### Option A — Best parity with training data (recommended)

| Layer | Provider | Endpoint | Key |
|---|---|---|---|
| Weather (daily min/max/mean, pressure, humidity, wind) | OpenWeather | One Call API 3.0 `day` summary **or** Forecast 2.5 `/forecast` aggregated | `OPENWEATHER_API_KEY` |
| Air quality (all 9 pollutant fields + AQI 1–5) | OpenWeather | `/data/2.5/air_pollution` (+ `/history` for past dates) | same key |
| Pollen (grass / tree / weed categories) | **Google Pollen API** | `forecast:lookup` → map `indexInfo.category` | `GOOGLE_POLLEN_API_KEY` |

Google returns categories like `LOW`, `MODERATE`, `HIGH`, `VERY_HIGH` — capitalize to match AAMOS (`Low`, `Moderate`, `High`, `Very High`).

### Option B — Free / no keys (dev & EU users)

| Layer | Provider | Notes |
|---|---|---|
| Weather | [Open-Meteo Forecast](https://open-meteo.com/en/docs) | Free, no key |
| Air quality | [Open-Meteo Air Quality](https://open-meteo.com/en/docs/air-quality-api) | PM, gases, NH3 (EU); **no `no`**; AQI is EU/US scale — map to OW 1–5 |
| Pollen | Open-Meteo `grass_pollen`, `birch_pollen`, `ragweed_pollen`, … | **Europe only**; grains/m³ → bucket via thresholds |

Use Option B for local dev; Option A for production parity with Elena's model.

## Pollen bucket mapping (Open-Meteo grains/m³ → AAMOS categories)

Calibrate thresholds against `data/raw/anonym_aamos00_environment.csv` once Google/OW pollen is unavailable:

```python
# Starting point — tune from AAMOS quantiles
POLLEN_BUCKETS = [
    (0, 20, "Low"),
    (20, 100, "Moderate"),
    (100, 300, "High"),
    (300, float("inf"), "Very High"),
]
```

Elena treats `grass_pollen`, `tree_pollen`, `weed_pollen` as **categorical** (`get_dummies(..., drop_first=True)`). Exact string labels must match training exports in `feature_columns.json`.

## AQI mapping (if not using OpenWeather)

OpenWeather `main.aqi`: 1=Good … 5=Very Poor. If using Open-Meteo `us_aqi` (0–500):

```python
def us_aqi_to_openweather_band(us_aqi: float) -> int:
    if us_aqi <= 50: return 1
    if us_aqi <= 100: return 2
    if us_aqi <= 150: return 3
    if us_aqi <= 200: return 4
    return 5
```

## API surface

### `GET /env/daily`

Fetch one Elena-compatible env row for a location and calendar date.

**Query params**

| Param | Required | Description |
|---|---|---|
| `lat` | yes | WGS84 latitude |
| `lon` | yes | WGS84 longitude |
| `date` | no | `YYYY-MM-DD`, default today (user timezone) |
| `provider` | no | `openweather` (default) or `openmeteo` |

**Response** (`EnvDailyResponse`)

```json
{
  "date": "2026-06-16",
  "lat": 60.17,
  "lon": 24.94,
  "provider": "openweather",
  "features": {
    "temperature": 15.91,
    "temperature_min": 14.21,
    "temperature_max": 17.2,
    "pressure": 1015,
    "humidity": 88,
    "wind_speed": 0.89,
    "wind_deg": 53,
    "aqi": 1,
    "co": 161.89,
    "no": 0.19,
    "no2": 8.65,
    "o3": 47.92,
    "so2": 2.89,
    "pm2_5": 7.55,
    "pm10": 8.51,
    "nh3": 0.82,
    "grass_pollen": "High",
    "tree_pollen": "Low",
    "weed_pollen": "Moderate"
  },
  "missing": [],
  "cached": false
}
```

### Integration with `/predict`

```
App → GET /env/daily?lat=&lon=     → 19 env fields
App → POST /predict { ...symptoms, ...watch_lags, env: {...} }
         → model/elena_features.py merges + get_dummies
         → predict_elena_ml()
```

Phase 1: `/env/daily` standalone. Phase 2: `/predict` accepts optional `lat`/`lon` and auto-fetches env server-side.

## Module layout

```
asthma-app/
  api/env.py                 # GET /env/daily route
  services/
    env_fetcher.py           # orchestrator + cache
    providers/
      openweather.py         # weather + air pollution
      openmeteo.py           # free fallback
      google_pollen.py       # grass/tree/weed categories
  model/elena_env_schema.py  # column list, pollen/AQI helpers
```

## Caching & limits

| Key | TTL | Reason |
|---|---|---|
| `(lat, lon, date, provider)` | 6 h for today; 7 d for past | OW free tier ~1000 calls/day |
| Round lat/lon to 2 decimals | — | ~1 km grid, fewer duplicate calls |

Store cache in memory (dev) or Redis (prod).

## Env vars

```bash
OPENWEATHER_API_KEY=...      # required for Option A
GOOGLE_POLLEN_API_KEY=...      # pollen (Option A)
ENV_PROVIDER=openweather       # or openmeteo
ENV_CACHE_TTL_SECONDS=21600
```

## Implementation order

1. **`model/elena_env_schema.py`** — `ENV_FEATURE_COLUMNS`, pollen/AQI mappers, validate response dict
2. **`services/providers/openmeteo.py`** — free path; validate against AAMOS CSV stats (no key blocker)
3. **`services/providers/openweather.py`** — air pollution + daily weather; match AAMOS column names
4. **`services/providers/google_pollen.py`** — GRASS / TREE / WEED → categories
5. **`services/env_fetcher.py`** — provider switch, cache, daily aggregation (mean of hourly)
6. **`api/env.py`** + register in `api/main.py`
7. **`model/elena_features.py`** — merge env + user lags + `is_flare_up` → encoded row for joblib model
8. **Validation script** — fetch env for a known AAMOS user location/date and compare distributions

## Risks

| Risk | Mitigation |
|---|---|
| Pollen unavailable outside EU (Open-Meteo) | Google Pollen API or default `Moderate` + flag in `missing[]` |
| `no` missing in Open-Meteo | Use OpenWeather for production; or impute from notebook's IterativeImputer stats |
| `nh3` sparse globally | OW has NH3; fallback median from AAMOS (~1.28 μg/m³) |
| Provider drift vs training | Log provider + raw values; periodic AUC check on holdout |

## Quick validation (after implementation)

```bash
# Compare live fetch to AAMOS row (user 113, date index 1)
curl "http://localhost:8000/env/daily?lat=60.17&lon=24.94&date=2022-06-01"
python -c "import pandas as pd; print(pd.read_csv('data/raw/anonym_aamos00_environment.csv').head(2))"
```
