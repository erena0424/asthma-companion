# Asthma Flare-up Prediction App

Predict **tomorrow's asthma flare-up** using **Elena's AAMOS-trained classifier**, served via FastAPI with GINA cold-start fallback for new users.

**Production config:** strategy 2 (XGBoost native NaN — keep missing feature values; only tomorrow's label required). **No peak flow (PEF)** in the classifier. API clients send `null` for unknown sensor fields; the server maps them to NaN (not `0`).

## Data download

This repository does not include the raw AAMOS CSV files. Download them from the Edinburgh DataShare page and place the extracted CSVs in `model/data/`:

1. Open http://datashare.ed.ac.uk/items/8478e384-fd1b-4a37-9555-0c6e1218e90b
2. Click **Download all files**
3. Extract the archive contents into `asthma-app/model/data/`

The notebook and feature engineering modules expect files named like `anonym_aamos00_dailyquestionnaire.csv`, `anonym_aamos00_environment.csv`, and so on. Peak flow CSVs are optional (not used in production training).

## Quick start

**macOS / Linux**

```bash
cd asthma-app

# 1. Start PostgreSQL
docker compose up -d postgres

# 2. Python env + dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit keys as needed

# 3. Apply migrations (creates tables)
alembic upgrade head
# (same as: python scripts/init_db.py)

# 4. Run API
./run_api.sh
```

**Windows (PowerShell)**

```powershell
cd asthma-app

# 1. Start PostgreSQL
docker compose up -d postgres

# 2. Python env + dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # edit keys as needed

# 3. Apply migrations (creates tables)
alembic upgrade head
# (same as: python scripts/init_db.py)

# 4. Run API
$env:PYTHONPATH = (Get-Location).Path
uvicorn api.main:app --reload --app-dir . --host 127.0.0.1 --port 8000
```

If PowerShell blocks script activation (`running scripts is disabled`), run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Database options**

| Environment | Setup |
|-------------|--------|
| **Local dev** | `docker compose up -d postgres` → `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mirror_lake` → `alembic upgrade head` |
| **Staging / demo (Neon)** | Neon project → pooled URL in `DATABASE_URL`, direct URL in `DATABASE_URL_DIRECT`, then `alembic upgrade head` |
| **Staging / demo (Supabase)** | Pooler in `DATABASE_URL`, direct DB host in `DATABASE_URL_DIRECT`, then `alembic upgrade head` |

Schema changes use **Alembic**, not SQLAlchemy `create_all`. After model edits:

```bash
alembic revision --autogenerate -m "describe_change"
alembic upgrade head
```

The API starts even if PostgreSQL is down (warn-and-skip on startup). Check `GET /health` — `database.connected` shows whether DB routes will work. Schema changes use Alembic; the Docker API entrypoint runs `alembic upgrade head` before uvicorn.

### Run tests

**macOS / Linux**

```bash
docker compose up -d
pip install -r requirements.txt
./run_tests.sh          # fast tests, mocked APIs (default)
./run_live_tests.sh     # real OpenWeather / Pollen / LLM — needs .env keys
```

**Windows (PowerShell)**

```powershell
docker compose up -d
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
pytest                  # fast tests, mocked APIs (default)
$env:RUN_LIVE_API_TESTS = "1"; pytest -m live -v   # live tests — needs .env keys
```

Default `pytest` skips live tests (`pytest.ini`: `-m "not live"`). Live tests call real external APIs and use keys from `.env`.

Tests use `mirror_lake_test` by default (`TEST_DATABASE_URL` to override). If PostgreSQL is unavailable, DB tests are skipped.

**If you see `ModuleNotFoundError: No module named 'api'`** you started uvicorn from the repo root (`Mirror-Lake/`). `cd asthma-app` first, or use `./run_api.sh` (macOS/Linux) / the uvicorn command above (Windows).

Open http://127.0.0.1:8000/docs for interactive API docs. Full contract details live in [`docs/API.md`](docs/API.md).

### Date windows (important)

| Window | Used for | Required? |
|--------|----------|-----------|
| **Today** (`date` / check-in day) | ML risk inputs: today's symptoms, inhaler, today's environment; **yesterday's** wearables as lags | Yes for `POST /v1/forecast` |
| **Tomorrow** (`forecast_for`) | What the model predicts; Copilot calendar loads **tomorrow's** planned events | Calendar optional — empty schedule is fine |

So: today's logged health data → tomorrow's risk score. Copilot advice can mention tomorrow's plans (soccer, etc.) when events exist; with no events it still advises from risk + environment + knowledge.

### Example API calls (`curl`)

With the API running at `http://127.0.0.1:8000` (see Quick start above):

**macOS / Linux**

```bash
# Register
curl -s -X POST http://127.0.0.1:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"demo-pass-123","name":"Demo"}'

# Login and save JWT
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"demo-pass-123"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# Today's check-in (required before forecast)
curl -s -X POST http://127.0.0.1:8000/v1/check-ins \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "daily_day_symp": false,
    "daily_night_symp": true,
    "daily_limit_activity": false,
    "puffs_today": 1,
    "triggers": ["pollen"]
  }'

# Optional: tomorrow's planned events for Copilot (not required for ML risk)
TOMORROW=$(python3 -c 'from datetime import date,timedelta; print((date.today()+timedelta(days=1)).isoformat())')
curl -s -X POST http://127.0.0.1:8000/v1/calendar/manual-events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"date\": \"$(date +%Y-%m-%d)\",
    \"events\": [{
      \"title\": \"Outdoor soccer\",
      \"start\": \"${TOMORROW}T09:00:00-05:00\",
      \"end\": \"${TOMORROW}T10:30:00-05:00\",
      \"all_day\": false,
      \"location\": \"Campus field\",
      \"description\": \"Scrimmage\"
    }]
  }" | python3 -m json.tool

# Forecast + bundled advice — look for calendar_events, calendar_source, advice
curl -s -X POST http://127.0.0.1:8000/v1/forecast \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lat": 42.36, "lon": -71.06, "advice_type": "daily"}' \
  | python3 -m json.tool

# Regenerate advice only (uses cached forecast; check-in optional)
curl -s -X POST http://127.0.0.1:8000/v1/advice \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"advice_type": "air_quality"}' \
  | python3 -m json.tool

# Health / env / profile
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
curl -s "http://127.0.0.1:8000/v1/env/daily?lat=42.36&lon=-71.06" | python3 -m json.tool
curl -s http://127.0.0.1:8000/v1/users/me \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Windows (PowerShell)**

```powershell
# Register
curl.exe -s -X POST http://127.0.0.1:8000/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"demo@example.com","password":"demo-pass-123","name":"Demo"}'

# Login
$login = curl.exe -s -X POST http://127.0.0.1:8000/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"demo@example.com","password":"demo-pass-123"}' | ConvertFrom-Json
$TOKEN = $login.access_token

# Check-in
curl.exe -s -X POST http://127.0.0.1:8000/v1/check-ins `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{\"daily_night_symp\":true,\"puffs_today\":1}'

# Optional tomorrow calendar for Copilot
$tomorrow = (Get-Date).AddDays(1).ToString("yyyy-MM-dd")
curl.exe -s -X POST http://127.0.0.1:8000/v1/calendar/manual-events `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d "{`"events`":[{`"title`":`"Outdoor soccer`",`"start`":`"${tomorrow}T09:00:00`",`"end`":`"${tomorrow}T10:30:00`",`"location`":`"Campus field`"}]}"

# Forecast + advice
curl.exe -s -X POST http://127.0.0.1:8000/v1/forecast `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{\"lat\":42.36,\"lon\":-71.06,\"advice_type\":\"daily\"}'
```

Typical daily flow: register/login → optional wearables → today's check-in and/or inhaler puff → optional tomorrow calendar events → `POST /v1/forecast` → optional `POST /v1/advice`.

### How to verify Copilot + calendar locally

Automated tests (already covering calendar → LangGraph prompt):

```bash
cd asthma-app
docker compose up -d
source .venv/bin/activate   # or: .venv\Scripts\Activate.ps1
pytest tests/test_calendar_api.py tests/test_copilot_workflow.py tests/test_forecast_advice_api.py -q
```

Offline LangGraph demo (no API keys; prints each node + calendar state):

```bash
cd asthma-app
docker compose up -d
PYTHONPATH=. python scripts/trace_copilot_workflow.py
PYTHONPATH=. python scripts/trace_copilot_workflow.py --no-calendar   # empty schedule still works
PYTHONPATH=. python scripts/trace_copilot_workflow.py --live-llm      # real Gemini/Claude
```

In the forecast JSON, check:

- `date` = today, `forecast_for` = tomorrow
- `calendar_events` / `calendar_source` (`check_in`, `request`, `google_calendar`, or empty + `data_quality.unavailable_context` containing `calendar`)
- `advice` mentions outdoor plans when events were provided

### Check LLM advice manually

**macOS / Linux**

```bash
./check_llm_advice.sh                              # direct LLM call (uses .env keys)
./check_llm_advice.sh --provider gemini --risk High --puffs 2
./check_llm_advice.sh --api                        # full flow via running API
./check_llm_advice.sh --api --lat 42.36 --lon -71.06
./check_llm_advice.sh --json > advice.json         # save raw JSON
```

**Windows (PowerShell)**

```powershell
$env:PYTHONPATH = (Get-Location).Path
python scripts/check_llm_advice.py
python scripts/check_llm_advice.py --provider gemini --risk High --puffs 2
python scripts/check_llm_advice.py --api
python scripts/check_llm_advice.py --api --lat 42.36 --lon -71.06
python scripts/check_llm_advice.py --json | Out-File -Encoding utf8 advice.json
```

Direct mode skips the server and calls Gemini/Claude with a sample scenario. `--api` registers a temp user, logs a puff, and runs `POST /v1/forecast` with real env data.

### Copilot recommendation workflow

`POST /v1/forecast` and `POST /v1/advice` use a typed LangGraph workflow:

1. Keep the ML forecast immutable.
2. Load calendar, environment, profile, and relevant historical context.
3. Compute personal insights (patterns, trends, and statistics) in Python.
4. Retrieve medical knowledge from the local JSON provider.
5. Apply prompt guardrails, invoke Gemini, and fall back to Claude when configured.
6. Validate the response before returning it.

### Lobelia Google Calendar + episode memory demo

One script that uses your connected Google account, prints tomorrow’s events,
and shows `debug.retrieved_episodes` (forces `COPILOT_DEBUG=1` for the process):

```bash
cd asthma-app
# Fast path (fake LLM; still uses real Google Calendar)
PYTHONPATH=. python scripts/demo_lobelia_calendar_memory.py \
  --email lobelia-demo@example.com --password demo-pass-123 \
  --seed-episodes --skip-llm

# Full forecast + live advice
PYTHONPATH=. python scripts/demo_lobelia_calendar_memory.py \
  --email lobelia-demo@example.com --password demo-pass-123 \
  --seed-episodes
```

`--seed-episodes` adds a few past outdoor days so retrieval isn’t empty on a new account.
Without it you’ll still see Google calendar events, but `retrieved_episodes` may be `[]`.

History uses hybrid episode memory (pgvector semantic similarity + Postgres full-text keyword search) over structured retrospective episodes — not raw calendar rows. Lookback defaults to 8 weeks (maximum one year) and sends only the most relevant examples plus compact metric windows to the LLM. Today's check-in and environment still reach the LLM through the normal Copilot nodes; empty episode memory is fine. Calendar context comes from Google Calendar (when connected), `POST /v1/calendar/manual-events`, request overrides, or legacy `calendar_event` text — wired into LangGraph via `StructuredCalendarProvider` / `ManualCalendarProvider` for tomorrow's forecast day. If both LLMs fail, the API still persists and returns the ML forecast with `advice: null` and a warning.

Backfill existing check-ins into episode memory:

```bash
EMBEDDING_PROVIDER=stub PYTHONPATH=. python scripts/backfill_episodes.py
```

Embeddings default to Gemini (`EMBEDDING_PROVIDER=gemini`, reuses `GEMINI_API_KEY`). Local Docker Postgres must use the `pgvector/pgvector:pg16` image (see `docker-compose.yml`).

Provider/model selection is configured with `LLM_PROVIDER`, `LLM_FALLBACK_PROVIDER`, `GEMINI_MODEL`, and `CLAUDE_MODEL`.

To build provenance-rich knowledge chunks from allowlisted CDC, EPA AirNow, and NHLBI sources:

```bash
python -m copilot.ingest
```

The source manifest is `knowledge/sources.json`. Every source and generated chunk declares an `audience`, allowed `advice_types`, and `medication_change_allowed` (currently always `false`). Patient retrieval derives search terms from anticipated forecast/environment triggers, applies chunk-level topic metadata, and returns no evidence rather than unrelated zero-score matches. The multi-column EXHALE PDF is disabled because its extracted columns interleave; cleaner CDC HTML sources provide the patient material. Clinician-oriented NHLBI material is retained solely for future `clinical_reference` use. GINA and American Lung Association entries accept approved local files only. Generated documents/chunks are ignored by Git. Chroma is intentionally deferred; `MedicalKnowledgeProvider` keeps retrieval storage replaceable.

### Classifier prediction (`POST /predict/classifier`)

Requires the trained artifact at `model/artifacts/flare_classifier.joblib`. Send today's environment, optional lagged sensor features (`null` if unknown), and today's flare status (or symptom fields to derive it). Returns tomorrow's flare probability.

Optional sensor / forecast fields: `sleep_minutes_lag`, `sedentary_minutes_lag`, `running_minutes_lag`, `total_steps_lag`, `avg_hr_lag`, `temp_diff_tomorrow`, `is_flare_up`. Omit or send JSON `null` — **do not use `0` for missing data**.

**macOS / Linux**

```bash
curl -s http://127.0.0.1:8000/health

curl -s -X POST http://127.0.0.1:8000/predict/classifier \
  -H "Content-Type: application/json" \
  -d '{
    "temperature": 12.5,
    "temperature_min": 8.0,
    "temperature_max": 15.0,
    "pressure": 1012.0,
    "humidity": 72.0,
    "wind_speed": 3.5,
    "wind_deg": 210.0,
    "aqi": 45.0,
    "co": 0.2,
    "no": 5.0,
    "no2": 12.0,
    "o3": 30.0,
    "so2": 2.0,
    "pm2_5": 18.0,
    "pm10": 25.0,
    "nh3": 0.5,
    "grass_pollen": "Low",
    "tree_pollen": "Moderate",
    "weed_pollen": "Low",
    "sleep_minutes_lag": 420,
    "total_steps_lag": 6500,
    "is_flare_up": 0
  }'
```

**Windows (PowerShell)**

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health

$body = @{
  temperature = 12.5
  temperature_min = 8.0
  temperature_max = 15.0
  pressure = 1012.0
  humidity = 72.0
  wind_speed = 3.5
  wind_deg = 210.0
  aqi = 45.0
  co = 0.2
  no = 5.0
  no2 = 12.0
  o3 = 30.0
  so2 = 2.0
  pm2_5 = 18.0
  pm10 = 25.0
  nh3 = 0.5
  grass_pollen = "Low"
  tree_pollen = "Moderate"
  weed_pollen = "Low"
  sleep_minutes_lag = 420
  total_steps_lag = 6500
  is_flare_up = 0
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict/classifier `
  -ContentType "application/json" -Body $body
```

Add `?include_advice=true` for Claude-generated advice (requires `ANTHROPIC_API_KEY` in `.env`).

### GINA cold start (`POST /predict`)

Simpler inputs for new users without full AAMOS feature history.

## Repo layout

| Path | Role |
|------|------|
| `model/risk_engine.py` | GINA + App cold-start rules |
| `model/inference.py` | Classifier + GINA routing |
| `model/feature_engineering.py` | Shared data preparation helpers |
| `model/model.py` | XGBoost model helpers |
| `model/train.py` | Population and personalized training routines |
| `model/inference_new.py` | Notebook-friendly inference helpers |
| `model/artifacts/flare_classifier.joblib` | Trained global classifier (local) |
| `api/` | FastAPI legacy `/predict/*` + `/v1` product APIs |
| `db/` | PostgreSQL models and session management |
| `docker-compose.yml` | Local PostgreSQL 16 for development |
| `tests/` | Pytest suite (auth, check-ins, forecast, advice) |
| `model/data/` | AAMOS raw CSVs (local, gitignored) |
| `docs/ELENA_HANDOFF.md` | What Elena exports for deploy |
| `docs/API.md` | Backend API spec for frontend + new endpoints |
| `docs/ENV_API_DESIGN.md` | Environment fetch design (OpenWeather / pollen) |
| `notebooks/Asthma_Prediction_Model.ipynb` | Research notebook rebuilt to use the shared modules |
| `../Asthma_binary.ipynb` | Elena's binary + Edge notebook (Elena branch) |

## Cold start

New users without full sensor/environment history can use **POST /predict** (App GINA). Users with complete daily features should use **POST /predict/classifier**.
