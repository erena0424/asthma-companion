# Mirror Lake — API Reference

**Version:** 1.0  
**Base URL:** `http://127.0.0.1:8000` (local)  
**Audience:** Frontend and mobile clients  
**Last updated:** 2026-07-03

Interactive docs: [`/docs`](http://127.0.0.1:8000/docs) (Swagger UI)

---

## Overview

Mirror Lake predicts **tomorrow's asthma flare risk** and returns **personalized advice**. Product flows use the **`/v1`** routes below. All user data (check-ins, wearables, forecasts) is stored in PostgreSQL and scoped to the authenticated user.

### Implementation status

| Area | Status |
|------|--------|
| Auth & user profile | **Shipped** |
| Daily check-ins & inhaler logging | **Shipped** |
| Wearable daily sync | **Shipped** |
| Environment data (`/v1/env/daily`) | **Shipped** |
| Google Calendar (OAuth + structured events → LLM) | **Shipped** |
| Forecast + bundled advice | **Shipped** |
| Advice regeneration (`/v1/advice`) | **Shipped** |
| Chat Q&A (`/v1/chat`) | **Shipped** (same Copilot graph; does not persist Home advice) |
| Legacy `/predict/*` routes | **Shipped** (research / fallback; product uses `/v1/forecast`) |
| **Edge AI** (per-user on-device model) | **Not implemented** — future phase |
| Frontend integration | **Partial** — auth, setup, home/stats forecast cards, calendar OAuth + month view, check-ins, chat wired; inhaler button + wearables UI still open |

### Typical daily flow

1. User logs in → store JWT.
2. Optional: sync yesterday's Health data → `POST /v1/wearables/daily`.
3. User taps rescue inhaler and/or logs symptoms → `POST /v1/check-ins/inhaler/puff` and/or `POST /v1/check-ins`.
4. Home screen → `POST /v1/forecast` with GPS → risk + advice.
5. Optional: refresh advice only → `POST /v1/advice`.

```mermaid
sequenceDiagram
    participant App
    participant API
    participant DB

    App->>API: POST /v1/auth/login
    API-->>App: access_token

    App->>API: POST /v1/wearables/daily (optional)
    App->>API: POST /v1/check-ins/inhaler/puff
    App->>API: POST /v1/check-ins

    App->>API: POST /v1/forecast { lat, lon }
    API->>DB: check-in, wearables, history
    API-->>App: flare_probability, risk_level, advice
```

---

## Authentication

All `/v1/*` routes except `/v1/auth/*` and `GET /v1/env/daily` require a JWT (Bearer token).

### Register

`POST /v1/auth/register` → **201**

**Request body**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `email` | string | yes | Unique, lowercased server-side |
| `password` | string | yes | Min 8 characters |
| `name` | string | no | |
| `date_of_birth` | string (`YYYY-MM-DD`) | no | |
| `emergency_contact` | string | no | |
| `preferred_reminder` | string | no | e.g. `"08:00"` |
| `contact_method` | string | no | e.g. `"Email"` |
| `preferred_environment` | string | no | |
| `care_goal` | string | no | |
| `accessibility_needs` | string | no | |
| `trigger_preferences` | string[] | no | e.g. `["Pollen", "Exercise"]` |
| `trigger_sensitivities` | object | no | Keys → float 0–1, e.g. `{ "pollen": 0.8 }` |

**Response**

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

**Errors:** `409 EMAIL_EXISTS`

---

### Login

`POST /v1/auth/login` → **200**

```json
{ "email": "user@example.com", "password": "..." }
```

**Response:** same as register.

**Errors:** `401 INVALID_CREDENTIALS`

---

### Refresh token

`POST /v1/auth/refresh` → **200**

```json
{ "access_token": "<current or expired jwt>" }
```

Returns a new `access_token` if the subject is still valid.

---

### Using the token

```http
Authorization: Bearer <access_token>
```

---

## User profile

### Get profile

`GET /v1/users/me` → **200**

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "Elena M.",
  "profile_image_url": "https://res.cloudinary.com/demo/image/upload/v1/profile.jpg",
  "date_of_birth": "1998-03-15",
  "emergency_contact": "Alex M. — 555-0100",
  "preferred_reminder": "08:00",
  "contact_method": "Email",
  "preferred_environment": "Low-pollen mornings",
  "care_goal": "Keep symptoms stable during exercise",
  "accessibility_needs": "Large text and clear contrast",
  "trigger_preferences": ["Pollen", "Exercise", "Cold air"],
  "trigger_sensitivities": { "pollen": 0.8, "exercise": 0.7 }
}
```

| Field | Notes |
|-------|--------|
| `profile_image_url` | Optional HTTPS URL (e.g. Cloudinary `secure_url`). Frontend uploads to Cloudinary; backend only stores the URL. |

### Update profile

`PATCH /v1/users/me` → **200**

Send only fields to change (same shape as register profile fields). Returns updated profile.

Example — save a Cloudinary avatar URL:

```json
{
  "profile_image_url": "https://res.cloudinary.com/xxxxx/image/upload/v123/profile.jpg"
}
```

No separate profile-image endpoint is required; use `PATCH /v1/users/me`.

---

## Check-ins

One row per user per calendar day. Inhaler counts live on the same row.

### Upsert symptoms

`POST /v1/check-ins` → **201**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `date` | string (`YYYY-MM-DD`) | today | |
| `daily_day_symp` | boolean | `false` | Daytime symptoms |
| `daily_night_symp` | boolean | `false` | Night symptoms |
| `daily_limit_activity` | boolean | `false` | Activity limited by asthma |
| `notes` | string | null | Free text |
| `triggers` | string[] | null | e.g. `["Pollen", "Exercise"]` |
| `calendar_event` | string | null | Upcoming activity for advice context, e.g. `"Outdoor soccer tomorrow"` |

**Does not set inhaler puffs** — use inhaler endpoints below.

**Response:** check-in object (see [Check-in object](#check-in-object)), plus:

| Field | Type | Description |
|-------|------|-------------|
| `forecast_refreshed` | boolean | `true` when today's or yesterday's symptoms changed an existing ML forecast |
| `forecast` | object \| omitted | Compact updated prediction (`risk_level`, `flare_probability`, `contributing_factors`, dates) when refreshed |

When a forecast already exists for that check-in day (`Forecast.date`), the API re-runs the classifier (not the LLM). Advice is cleared and backfilled on the next `POST /v1/forecasts/today` / Home load. Older days than yesterday do not refresh a prediction.

---

### List check-ins

`GET /v1/check-ins?from=YYYY-MM-DD&to=YYYY-MM-DD` → **200**

```json
{ "items": [ /* check-in objects */ ] }
```

---

### Today's check-in

`GET /v1/check-ins/today` → **200**

Returns today's row, creating an empty one if needed.

---

### Check-in object

```json
{
  "id": "uuid",
  "date": "2026-07-03",
  "daily_day_symp": false,
  "daily_night_symp": true,
  "daily_limit_activity": false,
  "symptoms_logged": true,
  "puffs_today": 2,
  "symptom_burden_score": 2,
  "notes": null,
  "triggers": ["Pollen"],
  "calendar_event": "Morning run tomorrow",
  "is_flare_up": 0,
  "is_flare_up_threshold": false
}
```

| Field | Meaning |
|-------|---------|
| `symptoms_logged` | User submitted `POST /v1/check-ins` for this day |
| `symptom_burden_score` | Non-clinical 0–5 trend score: one point per symptom flag, plus 0 points for 0 puffs, 1 for 1–2 puffs, or 2 for 3+ puffs |
| `is_flare_up_threshold` | `puffs_today >= 3` |
| `is_flare_up` | Model label: threshold **or** all three symptom flags true |

---

## Rescue inhaler

Two endpoints update the same daily `puffs_today` total.

### Quick log (+1 puff)

`POST /v1/check-ins/inhaler/puff` → **200**

**Request** (optional body):

```json
{
  "date": "2026-07-03",
  "recorded_at": "2026-07-03T14:32:00Z"
}
```

**Response**

```json
{
  "date": "2026-07-03",
  "puffs_today": 2,
  "event_id": "uuid",
  "is_flare_up_threshold": false,
  "message": "Logged 1 puff. Today's total: 2.",
  "forecast_refreshed": false
}
```

Same `forecast_refreshed` / `forecast` fields as symptom upsert when today/yesterday already has a stored prediction.
---

### Set daily total manually

`PUT /v1/check-ins/inhaler` → **200**

```json
{ "date": "2026-07-03", "puffs_today": 4 }
```

| Field | Constraints |
|-------|-------------|
| `puffs_today` | integer, `0`–`50` |

**Response**

```json
{
  "date": "2026-07-03",
  "puffs_today": 4,
  "source": "manual",
  "is_flare_up_threshold": true
}
```

---

## Wearables (Health app sync)

Client reads HealthKit / Health Connect on device, aggregates one day, and POSTs to the server.

`POST /v1/wearables/daily` → **201**

| Field | Type | Description |
|-------|------|-------------|
| `date` | string (`YYYY-MM-DD`) | **Required** — usually yesterday |
| `sleep_minutes` | integer | Optional |
| `total_steps` | integer | Optional |
| `sedentary_minutes` | integer | Optional |
| `running_minutes` | integer | Optional |
| `avg_hr` | number | Optional average heart rate |

```json
{
  "date": "2026-07-02",
  "sleep_minutes": 390,
  "total_steps": 6200,
  "sedentary_minutes": 480,
  "running_minutes": 15,
  "avg_hr": 71
}
```

Upserts by `(user, date)`. Omitted fields are stored as `null`. Forecast uses **yesterday's** row as classifier lag features.

There is no `GET` wearables endpoint in v1; keep local display state or re-sync as needed.

---

## Environment data

`GET /v1/env/daily` → **200**  
**Auth:** not required

| Query | Required | Description |
|-------|----------|-------------|
| `lat` | yes | WGS84 latitude, −90…90 |
| `lon` | yes | WGS84 longitude, −180…180 |
| `date` | no | `YYYY-MM-DD`, default today |
| `provider` | no | `openweather` (production) or `openmeteo` (dev). Default from server `ENV_PROVIDER`. |

**Response**

```json
{
  "date": "2026-07-03",
  "lat": 42.36,
  "lon": -71.06,
  "provider": "openweather",
  "features": {
    "temperature": 24.1,
    "temperature_min": 18.0,
    "temperature_max": 28.0,
    "pressure": 1012.0,
    "humidity": 55.0,
    "wind_speed": 3.0,
    "wind_deg": 180.0,
    "aqi": 2,
    "co": 200.0,
    "no": 1.0,
    "no2": 10.0,
    "o3": 40.0,
    "so2": 2.0,
    "pm2_5": 12.0,
    "pm10": 18.0,
    "nh3": 1.0,
    "grass_pollen": "Low",
    "tree_pollen": "Moderate",
    "weed_pollen": "Low"
  },
  "missing": [],
  "cached": false
}
```

**`features`** always includes 19 keys (see [ENV_API_DESIGN.md](./ENV_API_DESIGN.md)). Pollen values are `Low` | `Moderate` | `High` | `Very High`. **`missing`** lists columns the provider could not supply.

**Errors:** `400` invalid provider; `502` provider failure

---

## Forecast (Home screen)

Primary product endpoint: tomorrow's risk + LLM advice.

`POST /v1/forecast` → **200**

### Prerequisites

Today's check-in must be **complete**:

- `POST /v1/check-ins` (symptoms logged), **or**
- at least one `POST /v1/check-ins/inhaler/puff`

Otherwise → `400 CHECK_IN_REQUIRED`.

### Request

```json
{
  "lat": 42.36,
  "lon": -71.06,
  "date": "2026-07-03",
  "llm_provider": "gemini",
  "advice_type": "daily"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `lat`, `lon` | yes | Device GPS |
| `date` | no | Anchor date (default today); forecast is for **anchor + 1 day** |
| `llm_provider` | no | `"claude"` or `"gemini"` (default from server config) |
| `advice_type` | no | Patient advice mode (default `"daily"`). Allowed: `"daily"`, `"emergency"`, `"action_plan"`, `"air_quality"`, `"wildfire"`, `"adherence"`, `"exercise"` |

### Response

```json
{
  "date": "2026-07-03",
  "forecast_for": "2026-07-04",
  "prediction_mode": "classifier",
  "flare_probability": 0.68,
  "predicted_flare_tomorrow": true,
  "risk_level": "Medium",
  "contributing_factors": [
    "High tree pollen",
    "Night symptoms today",
    "Rescue inhaler used twice"
  ],
  "top_features": ["is_flare_up", "humidity", "pm2_5"],
  "cold_start": false,
  "missing_features": [],
  "warnings": [],
  "advice": {
    "summary": "...",
    "sections": [
      { "title": "Before tomorrow's activity", "body": "..." },
      { "title": "During activity", "body": "..." }
    ],
    "disclaimer": "This information is for educational purposes only...",
    "llm_provider": "gemini",
    "knowledge_sources_used": ["local_knowledge", "user_history"]
  },
  "data_quality": {
    "unavailable_context": ["wearables", "calendar"],
    "missing_fields": [],
    "imputed_fields": [],
    "warnings": []
  }
}
```

| Field | Description |
|-------|-------------|
| `risk_level` | `"Low"` \| `"Medium"` \| `"High"` |
| `contributing_factors` | Human-readable list for UI chips |
| `advice` | Bundled Copilot advice for Home, or `null` when all LLM providers fail (ML forecast is still returned) |
| `warnings` | Classifier warnings plus advice/outage notes (e.g. advice temporarily unavailable) |
| `data_quality` | `{ unavailable_context, missing_fields, imputed_fields, warnings }` — e.g. `wearables` / `calendar` when absent |

**Errors**

| HTTP | Code | When |
|------|------|------|
| 400 | `CHECK_IN_REQUIRED` | No check-in / puff today |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT |
| 502 | `ENV_PROVIDER_ERROR` | Weather/pollen fetch failed |
| 503 | `CLASSIFIER_UNAVAILABLE` | Model artifact missing |

LLM advice failure does **not** fail the forecast: HTTP stays **200**, `advice` is `null`, and a message is added to `warnings` / `data_quality.warnings`.

Result is persisted in PostgreSQL for advice regeneration.

---

## Advice regeneration

Re-run the LLM advice pipeline **without** re-running the classifier. Requires a prior forecast for the same date.

**Check-in is optional.** Advice can still use the cached risk score, stored environment (AQI, pollen, etc.), history, and medical knowledge — e.g. recommend a mask when air quality is poor even if today's symptoms were never logged. Missing check-in is reported in `data_quality.unavailable_context` and `warnings`; the API does **not** invent “no symptoms.”

`POST /v1/advice` → **200**

```json
{
  "date": "2026-07-03",
  "llm_provider": "gemini",
  "advice_type": "air_quality"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `date` | no | Anchor date (default today) |
| `llm_provider` | no | `"claude"` or `"gemini"` (default from server config) |
| `advice_type` | no | Same patient modes as forecast (default `"daily"`) |

**Response**

```json
{
  "date": "2026-07-03",
  "forecast_for": "2026-07-04",
  "risk_level": "Medium",
  "flare_probability": 0.68,
  "contributing_factors": ["Elevated air quality index"],
  "advice": { /* same shape as forecast.advice; may be null if LLM providers fail */ },
  "warnings": [
    "Generated without today's symptom check-in; advice is based on the cached forecast, environment, and medical knowledge."
  ],
  "data_quality": {
    "unavailable_context": ["check_in", "calendar"],
    "missing_fields": [],
    "imputed_fields": [],
    "warnings": ["..."]
  }
}
```

**Errors:** `404 FORECAST_NOT_FOUND` if `POST /v1/forecast` was not run for that date. Advice LLM outages return **200** with `advice: null` and a warning (stored ML forecast is unchanged).

Manual `calendar_event` on a check-in is passed into the Copilot calendar node (`source: "manual"`).

Structured events from Google Calendar, `POST /v1/calendar/manual-events`, or `calendar_events` on forecast are loaded into LangGraph via `StructuredCalendarProvider` for **tomorrow** (the forecast target day), including title, time, location, and description.

---

## Chat (Copilot Q&A)

Answer a user **message** using the same LangGraph Copilot as daily advice (forecast, calendar, env, episode memory, medical knowledge). Requires a prior forecast for the date.

**Does not overwrite** the Home-card `Forecast.advice` row (`persist=false`). Durable personalization comes from medical/episode memory (check-ins, forecasts, calendar), not chat logs. Future conversation memory, streaming, or citations should extend `/v1/chat` only — not `/v1/advice`.

`POST /v1/chat` → **200**

```json
{
  "message": "Should I run outside with this pollen?",
  "date": "2026-07-03",
  "llm_provider": "gemini"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `message` | yes | User question or statement (1–1000 chars) |
| `date` | no | Forecast anchor date (default today) |
| `llm_provider` | no | `"claude"` or `"gemini"` |

**Response:** same shape as `POST /v1/advice` (`advice`, `warnings`, `risk_level`, `data_quality`, …). The UI typically shows `advice.summary`.

**Errors:**

- `404 FORECAST_NOT_FOUND` — no cached forecast; complete a check-in and generate a prediction first
- `400` — empty/whitespace `message`

LLM outages return **200** with `advice: null` and a warning (same as advice regen).

---

## Health check

`GET /health` → **200**  
**Auth:** not required

```json
{
  "status": "ok",
  "classifier_loaded": true,
  "any_model_available": true,
  "database": {
    "status": "ok",
    "connected": true,
    "url_host": "localhost:5432/mirror_lake"
  },
  "training": {
    "missing_data_strategy": "xgb_native_nan",
    "peakflow": "not_used",
    "nullable_api_fields": [
      "sleep_minutes_lag",
      "sedentary_minutes_lag",
      "running_minutes_lag",
      "total_steps_lag",
      "avg_hr_lag",
      "temp_diff_tomorrow",
      "is_flare_up"
    ]
  }
}
```

`status` is `"degraded"` when the database is unreachable. Auth and forecast routes need `database.connected: true`.

---

## Legacy prediction routes

For research and cold-start fallback. **Product UI should use `POST /v1/forecast`.**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/predict/classifier` | Full XGBoost classifier; send env + optional wearable lags |
| `POST` | `/predict` | GINA rules for new users with minimal history |

Both support optional `?include_advice=true` (legacy Claude interpreter). See `/docs` for request schemas.

**Important:** Send JSON `null` for unknown sensor fields — do **not** use `0` for missing data.

---

## Client integration notes

### Calendar

Backend can connect a user's Google Calendar (read-only OAuth) and automatically fetch **tomorrow's** events when running `POST /v1/forecast`.

| Step | Endpoint |
|------|----------|
| Status | `GET /v1/calendar/status` |
| Start OAuth | `GET /v1/calendar/connect` → open `auth_url` |
| Google redirect | `GET /v1/calendar/callback` (stores refresh token) |
| Preview events | `GET /v1/calendar/events?date=YYYY-MM-DD` **or** `?from=&to=` (inclusive range, max 62 days; preferred for month grids) |
| Disconnect | `DELETE /v1/calendar/disconnect` |

Setup details: [CALENDAR.md](./CALENDAR.md).

Dev without Google: `POST /v1/calendar/manual-events`, or pass `calendar_events` on forecast. Legacy string still works on check-in:

```json
{ "calendar_event": "Outdoor soccer tomorrow" }
```

### Location

Send `lat` / `lon` from device GPS on forecast (and env if needed). The server fetches weather and pollen for that point.

### Error format

```json
{
  "detail": "Human-readable message",
  "code": "CHECK_IN_REQUIRED"
}
```

Validation errors (`400`) may include an `errors` array (Pydantic).

| Code | HTTP | Meaning |
|------|------|---------|
| `VALIDATION_ERROR` | 400 | Invalid request body or query |
| `CHECK_IN_REQUIRED` | 400 | Forecast without today's check-in |
| `UNAUTHORIZED` | 401 | Missing or bad JWT |
| `INVALID_CREDENTIALS` | 401 | Login failed |
| `USER_NOT_FOUND` | 404 | Token subject not in DB |
| `FORECAST_NOT_FOUND` | 404 | No forecast for advice regeneration |
| `EMAIL_EXISTS` | 409 | Register with existing email |
| `ENV_PROVIDER_ERROR` | 502 | Environment API failure |
| `CLASSIFIER_UNAVAILABLE` | 503 | Model file missing |

LLM provider outages on `/v1/forecast`, `/v1/advice`, and `/v1/chat` do not use a dedicated error code: the response stays **200** with `advice: null` and a warning string.

---

## Endpoint index

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | No | Service health |
| `GET` | `/v1/env/daily` | No | Environment features for lat/lon |
| `POST` | `/v1/auth/register` | No | Create account |
| `POST` | `/v1/auth/login` | No | Sign in |
| `POST` | `/v1/auth/refresh` | No | Refresh JWT |
| `GET` | `/v1/users/me` | Yes | Get profile |
| `PATCH` | `/v1/users/me` | Yes | Update profile |
| `POST` | `/v1/check-ins` | Yes | Upsert symptoms |
| `GET` | `/v1/check-ins` | Yes | List history |
| `GET` | `/v1/check-ins/today` | Yes | Today's check-in |
| `POST` | `/v1/check-ins/inhaler/puff` | Yes | Log +1 puff |
| `PUT` | `/v1/check-ins/inhaler` | Yes | Set puff total |
| `POST` | `/v1/wearables/daily` | Yes | Sync Health aggregates |
| `GET` | `/v1/calendar/status` | Yes | Google Calendar connection status |
| `GET` | `/v1/calendar/connect` | Yes | Start Google OAuth |
| `GET` | `/v1/calendar/events` | Yes | Preview events for a day (`date`) or range (`from`/`to`) |
| `POST` | `/v1/calendar/manual-events` | Yes | Dev: store structured events |
| `DELETE` | `/v1/calendar/disconnect` | Yes | Disconnect Google Calendar |
| `POST` | `/v1/forecast` | Yes | Tomorrow risk + advice (+ auto calendar) |
| `GET` | `/v1/forecasts` | Yes | Forecast history |
| `POST` | `/v1/forecasts/today` | Yes | Get-or-create `{ today, tomorrow }` for home/stats (runs ML/advice if missing) |
| `GET` | `/v1/forecasts/today` | Yes | Read-only peek at stored card predictions (no ML/LLM) |
| `POST` | `/v1/advice` | Yes | Regenerate daily advice (persists to forecast) |
| `POST` | `/v1/chat` | Yes | Copilot Q&A over cached forecast (does not overwrite Home advice) |
| `POST` | `/predict/classifier` | No | Legacy classifier |
| `POST` | `/predict` | No | Legacy GINA cold start |

---

## Roadmap (not in v1)

| Feature | Notes |
|---------|-------|
| **Edge AI** | Per-user on-device model training and routing |
| `GET /v1/wearables/daily` | History read-back |
| Peak flow (PEF) | Out of scope for classifier |

---

## Related documentation

- [ENV_API_DESIGN.md](./ENV_API_DESIGN.md) — environment column definitions and providers
- [CALENDAR.md](./CALENDAR.md) — Google Calendar OAuth setup
- [README.md](../README.md) — local setup, Docker, tests

## BuildFest confirmed support context

All routes below require `Authorization: Bearer <access_token>` from existing
login. Ownership always comes from the authenticated subject. Missing, invalid
or expired JWT: 401 `UNAUTHORIZED`; deleted-account token: 404 `USER_NOT_FOUND`.
Validation: 400 `{detail:"Validation error",code:"VALIDATION_ERROR",errors:[...]}`.
Persistence failures remain server errors; clients must not mark failed saves as saved.

### Existing profile: GET/PATCH `/v1/users/me`

PATCH example:
```json
{"emergency_contacts":[{"id":"demo-contact","firstName":"Demo","lastName":"Contact","phone":"+1 555 010 0123","email":null}],"care_goal":"Make time for breaks","accessibility_needs":"Larger text"}
```
Returns full existing profile, including canonical contact array, legacy contact
string, care_goal and accessibility_needs. Fields retain their existing meanings;
they are user-entered support information, not a clinical plan or inferred style.
Omitted fields remain unchanged, null retains legacy no-op behavior. Empty strings
clear personal text. `emergency_contacts: []` clears both array and legacy string.
PATCH contacts now require a nonblank first/last name (each max 100), phone max 40
with 7–15 digits and ordinary `+ ()-.` punctuation; id max 128, email max 254.
Unknown contact properties are rejected. This validates shape, not reachability.
Historical email-only records still load; writing email-only contacts is rejected.
Support text PATCH values are capped at 1000. Summary cannot be written through
profile PATCH or registration. No contact messages/calls are sent by the backend.

### Latest approved summary: `/v1/users/me/support-memory`

GET returns `{"summary":null}` until explicitly saved. PUT creates or replaces
ONE latest summary; correction requires renewed explicit approval:
```json
{"text":"I prefer a short pause before reflecting.","approved":true,"check_in_date":"2026-09-26"}
```
Only literal boolean true qualifies; missing/false/1/strings fail validation.
`text` is trimmed, nonblank and max 500 characters. `check_in_date` is optional
ISO date (default null), user-reported metadata, not a foreign key; no daily
check-in is required or created. Extra fields (including user_id) are rejected.
200 response (GET uses the same shape):
```json
{"summary":{"text":"I prefer a short pause before reflecting.","check_in_date":"2026-09-26","saved_at":"2026-09-26T15:00:00+00:00","source":"user-reported"}}
```
Timestamp is server-generated UTC on each approval. Source means user report,
not independently verified medical information. Editing check-ins never refreshes
this reviewed snapshot. DELETE returns 204 with no body, including if already
empty; subsequent GET returns null. No automatic extraction, chat logging,
embeddings, LLM calls or copies into profile/episode history are performed.
Deletion clears this application field, not external database backups.

### Daily reflection: POST `/v1/check-ins?refresh_forecast=false`

```json
{"date":"2026-09-26","daily_day_symp":false,"daily_night_symp":false,"daily_limit_activity":false}
```
Returns 201 with existing check-in fields plus `forecast_refreshed:false`.
Same-day writes update one existing row. Send each boolean only after answering.
Optional existing notes are persisted if explicitly provided; never send raw chat.
This POST does not save a support summary. With flag omitted, legacy forecast
refresh remains enabled. This flow displays no legacy risk/burden assessment.

## Supportive companion demo (additive)

`POST /v1/companion/chat` uses existing Bearer JWT authentication. Legacy `/v1/chat`
and forecast endpoints remain unchanged. No client user ID or provider override.

Request:
```json
{"message":"I have a busy day ahead.","include_saved_context":true}
```
`message`: trimmed nonblank string, max 1000 characters. `include_saved_context`:
strict boolean, default false. Extra fields are rejected. This flag is request-only;
it does not change profile, summary storage or consent settings.

Response (200):
```json
{
  "message":"That sounds like a full day. What would feel most useful right now?",
  "generation_status":"generated",
  "forecast":{"status":"unavailable","data":null},
  "context_sources":["reported_profile","approved_summary"],
  "persona_version":"companion-v2"
}
```
Illustrative message only; generated text varies. `generation_status` is `generated`
or `fallback`; provider timeout/error/invalid output returns predefined nonclinical
fallback text with 200. `context_sources` lists inputs supplied, not proof that
specific statements were grounded in them.

When present `forecast.data` contains `date`, `forecast_for`, `generated_at`
(nullable ISO timestamp), `risk_level` (nullable), `flare_probability` (nullable),
and at most five stored `contributing_factors`. Values come unchanged from the
current user's latest stored forecast with run date no later than server-local today.
`status` is `stale` if its target date is before server-local today, `current` if equal,
or `future` if later. This is date relevance, not model accuracy or medical safety.
Missing forecast is `unavailable`, not an error; no forecast is regenerated.
The frontend must render dates/status with forecast values, including stale state;
this endpoint neither supplies an acute assessment nor determines urgency.

The selected configured `LLM_PROVIDER` and existing model settings are reused.
There is no automatic cross-provider fallback. An outer 20-second deadline bounds
waiting (SDK cancellation behavior depends on the existing provider client).
No contacts, names or email addresses are selected for model context. By default
only the user's message and dated stored forecast are sent. When the flag is true,
current `care_goal`, `accessibility_needs`, `trigger_preferences`,
`preferred_environment`, and the latest approved summary's text/date/save timestamp/
source are also sent. Re-read on every call; corrected/deleted summaries cannot
be recalled from an internal chat archive because none is created here.

Frontend integration must explain that enabling saved context sends these fields
to the configured AI provider. Approval to store a summary is not approval to send
it; leave the flag false until that choice is made. Message text may itself contain
private information. Backend does not persist prompts/replies or create episodes;
provider retention is governed by its settings/terms, not a zero-retention claim.
Use fictitious demo data. No new vendor, embedding, external calendar retrieval,
new table, conversation storage or migration is introduced.

Errors: 400 `VALIDATION_ERROR` with shared validation errors; 401
`UNAUTHORIZED` for missing/invalid/expired authentication (existing auth contract).
A valid token whose user no longer exists returns 404 `USER_NOT_FOUND`.
Database failures are errors, not fabricated successful replies. No help action,
zone, questionnaire, dispatch, notification or treatment instruction is returned.
Output length/schema and bounded medication patterns are validated, but these
checks and persona instructions do not prove every generated response safe.

`persona` is optional `warm` (default), `calm`, or `direct`; response echoes it.
Each maps to a fixed server-side tone fragment under identical safety instructions.
No arbitrary system prompt is accepted. Invalid persona is 400.
`generation_status` also includes `context_changed`: if selected saved context
changes during generation, discard the generated reply and return static fallback;
frontend may offer retry. Already-sent provider input cannot be retracted. Backend
checks immediately before return; it cannot recall a reply already delivered.
The chat sends up to four recent successful exchanges (8 alternating user/assistant
messages, 1200 characters each, 6000 total), kept only in React memory. No full chat
is saved to the database or browser storage. Static greetings, errors, fallback replies and
unanswered messages are excluded. Clear Chat, account changes and saved-context
opt-in changes reset eligible history; late replies are discarded. An opaque
per-process context token binds history to the current authenticated user, opt-in,
profile/summary and forecast. A missing/mismatched token discards history but still
answers the current message. Corrections/deletions, forecast changes and server
restart can reset continuity; different workers may also reset it. Current server
context overrides historical model statements. Already displayed text is not
retroactively erased by edits elsewhere. No technical forecast/status boilerplate
is appended to bubbles; structured forecast metadata remains in the API and the
model includes dates/uncertainty when relevant. This is bounded conversational
continuity, not durable automatic memory. Saved approved summaries remain the
separate optional cross-visit feature.

Request optional `history` defaults to `[]`: objects with only `role` (`user` or
`assistant`) and nonblank `content`. Complete alternating pairs starting with
`user` are required. Unknown fields/roles, odd counts, more than 8 items, content
above 1200 characters, or total content above 6000 characters return 400.
Optional `context_token` is null or a string of at most 64 characters. Return the
last response token with the next history request. Response adds `context_token`
(opaque string for generated replies, null on fallback/context change) and
`history_accepted` (boolean). Treat all client history as untrusted data, never
system instructions. The token is context binding, not proof a submitted transcript
is authentic; authenticated clients control their own submitted text.

Date relevance follows existing server-local `date.today()` convention; it may
differ from a user's timezone. The persona/version are informational, not storage.

## Forecast-led opening for the video demo

Opening the visible floating chat or full chat page calls authenticated
`POST /v1/companion/opening` once per in-memory conversation, using the selected
tone and current saved-context opt-in. A hidden/collapsed chat makes no opening
request. Navigation/re-render does not generate another greeting. Clear Chat
cancels pending output and leaves a neutral greeting; it does not immediately
call the model again. Account changes reset this state. A failed opening shows
a natural greeting with an explicit retry button; there is no automatic retry loop.

The existing companion provider receives current cached forecast facts and
instructions for 2–3 conversational sentences, retaining relevant dates and
uncertainty without article titles or technical status boilerplate. No forecast
calculation or advice-page behavior changes. Missing forecast can yield a simple
greeting. Output quality still needs a live model/demo rehearsal.

A successfully generated opening is held separately in React memory and sent as
bounded, untrusted `opening_message` background on follow-ups, with the same
context token checks as recent exchanges. It is not a user-authored message,
approved memory or saved transcript. Clear/account/opt-in changes remove it;
a rejected context revision or fallback also removes it from subsequent requests.

Opening request body: `{"persona":"warm","include_saved_context":false}`.
Both fields are optional with these defaults. No message/history/user ID is
accepted; extra fields and invalid tone/boolean return the existing 400 validation
response. Authentication/errors match `/chat`. Response has the same fields as
`/chat`: `message`, `generation_status`, `forecast`, `context_sources`,
`context_token`, `history_accepted`, `persona_version`, `persona`.
On provider/schema failure, `generation_status: "fallback"`, null context token
and predefined `Hello! What's on your mind today?` are returned.
Saved-context changes during generation return `context_changed` with that same
neutral greeting. Neither failure means a forecast was generated or refreshed.

`POST /chat` additionally accepts nullable `opening_message` (default null,
maximum 1200 characters). It is passed to the model only with a valid current
`context_token`; otherwise it is discarded with history. It never becomes a
system instruction. No additional database writes or provider are introduced.


### Saved calendar plans in companion context

With `include_saved_context:true`, `/v1/companion/opening` and `/v1/companion/chat`
also read the current user's existing today/tomorrow calendar fields from
`check_ins`. No external calendar fetch occurs. `context_sources` includes
`saved_calendar_plans` only when selected entries exist. No response fields or
request defaults change. No health/check-in fields accompany this calendar read.

At most three plan titles per date (200 characters each) are sent: the existing
free-text `calendar_event` uses its saved row date; structured `calendar_events`
require an explicit matching date or all-day start date. Ambiguous timed dates
are omitted. The two-day window uses server-local dates; user timezone is unknown.
Plans are untrusted user-reported intentions, not attendance or medical guidance.
Their dates are separate from the forecast target date. Missing plans are unknown.

Selected plans are bound into `context_token`. Changing or clearing a selected
plan invalidates previous history/opening; a concurrent change returns
`generation_status: "context_changed"` with neutral fallback, as with other
saved context. This does not retroactively remove previously displayed bubbles.
