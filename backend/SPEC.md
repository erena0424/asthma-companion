# Backend adaptation for the current web demo

## Authorized continuity extension (current implementation contract)

This extension supersedes earlier no-schema and future-memory exclusions below.
Reuse explicit profile `care_goal` and `accessibility_needs` edits as support
preferences; no inferred preferences. Add only nullable `users.support_memory`
JSONB for ONE latest optional short user-approved check-in summary (text up to
500 characters, optional user-reported check-in date, server UTC saved_at, source user-reported).
No raw chat saving, automatic extraction, clinical inference, vector or provider
integration. This is user-authored text, never a verified clinical conclusion.

Authenticated GET `/v1/users/me/support-memory` returns `{summary: object|null}`.
PUT on that path requires `text` and explicit boolean `approved: true`;
`check_in_date` is optional user-reported date metadata, never ownership proof.
Reject extra fields. Saving a summary never creates or changes a daily check-in.
PATCH contact writes require nonblank names (max 100 each) and phone max 40
with 7–15 digits/ordinary punctuation; reject unknown contact fields. Legacy
reads remain tolerant. Personal text PATCH fields max 1000; empty string clears. PUT replaces the prior summary and
updates timestamp; DELETE clears durably and returns 204. No client user ID.
Summary is independent reviewed text: editing source check-in does not regenerate
it; view/correct/delete use these endpoints. No background copies or regeneration.
Profile contacts array clears legacy contact text when emptied. Existing daily
POST gains `refresh_forecast=false` opt-out, default true unchanged. New flow
uses false and sends no raw reflection notes unless deliberately saved as the
existing daily note. Summary approval is a separate explicit action after review; daily save is not required.

Migration adds one nullable column in the existing Postgres database. Tests use
isolated SQLite with test-only type compilation and fresh sessions, never legacy
fixtures or configured databases; Postgres migration runtime remains a separate
operational check. API reference documents payloads, errors and migration setup.


## Active contract

Use the existing `asthma-app/api`, `services`, `db` and React client in this repo.
`backend/` currently contains this document, not a new running server. No new
backend, database platform or auth system is required; the sole schema addition
is one nullable continuity column for the smallest
contact → guided reflection → help-access story. Preserve existing routes and
the historical proposal below; this section takes precedence for tomorrow.

## What source inspection established

| Existing component | Reuse decision and constraint |
|---|---|
| `asthma-app/api/main.py:105` router registration; `db/database.py:21` sessions | REUSE existing server/session infrastructure; runtime/DB connection not verified. Do not point tests at an unknown database. |
| `db/models.py:47`, `api/users.py:86`, `api/users.py:91` | REUSE contact JSONB and authenticated GET/PATCH `/v1/users/me`. Canonical `emergency_contacts` array holds id/name/phone/email; frontend label may say trusted contact without schema rename. |
| `api/user_schemas.py:11`, `api/users.py:65` | ADAPT only if validation or clearing requires it. Existing fields are optional and null writes are ignored; do not promise validation absent code/tests. Clearing array must not surface stale legacy `emergency_contact` text. |
| `db/models.py:51`, `api/users.py:56` | REUSE user-entered `care_goal` and `accessibility_needs` as personal information with their existing meanings. Not clinician instructions or a medical plan. |
| `api/check_ins.py:29`, `services/check_in_service.py:71` | ADAPT existing daily boolean reflection/notes save. One row per user/date, not a new severity or mood model. Service commits before forecast refresh. |
| `api/check_ins.py:81`, `services/forecast_service.py:424` | ADAPT narrow opt-out for new companion requests so save does not wait on forecast work. Preserve legacy callers/defaults; no global forecast rewrite. |
| Existing forecasts/chat/episodes/providers | NOT NEEDED for this path. Preserve functionality elsewhere, but new help/check-in does not depend on them. |
| Saved clinician Action Plan, contact dispatch/delivery tracking | NOT FOUND as a ready backend capability; do not invent availability or build for tomorrow. |

Evidence is source-wiring, not a passing integration test. Existing
`tests/test_users_api.py:72` exercises contact round-trip intentions;
`tests/test_check_ins_api.py` covers old check-in behavior. Neither was run here.

## Minimal contracts and proposed changes

- Keep `GET/PATCH /v1/users/me` and authenticated user scoping. Save trusted
  contacts through the existing array, refresh from the returned server value,
  and load canonical array on help page. An empty list is empty, not stale legacy
  fallback. Display phone for manual use; no backend contact/send action.
- Load saved `care_goal` and `accessibility_needs` alongside contacts. Add simple
  editors for those already-supported fields only if absent in the current UI;
  empty strings can clear them under existing PATCH behavior. Do not overload
  them with generated clinical content or store a fabricated Action Plan.
- Keep check-in daily semantics and existing boolean fields/optional notes.
  Questions must actually collect each submitted boolean; unanswered must not
  silently mean false. Optional free text can capture feelings in `notes` without
  pretending to be a separate structured mood history. Do not interpret or display
  `is_flare_up`, burden score or forecast as an assessment in this path; existing
  response fields may remain for compatibility.
- Proposed small additive change: `POST /v1/check-ins?refresh_forecast=false`
  skips optional forecast refresh for companion flow; default remains true for
  existing callers. Existing persisted payload stays compatible. Frontend helper
  passes the option explicitly. No classifier/LLM added. The opt-out needs no migration; continuity uses the
  single-column migration above.
- A failed DB write stays an error. Help must not wait for save completion or an
  LLM; user can navigate there immediately. Do not claim offline persistence.

## Verification and operational limits

Implementation must verify contact save/load/clear, failed-save honesty, cross-user
access protection, preserved personal text and reflection saved with forecast
refresh disabled. Assert disabled requests never invoke forecast/LLM; old default
behavior remains covered. Check-in response compatibility does not establish
clinical safety. Source tests currently require dedicated Postgres/pgvector for
the legacy schema; never run destructive fixtures against a real account DB.

Root `package.json` delegates frontend to `asthma-app/frontend`; its deploy/done
scripts publish/push and must not be used as validation. `scripts/backend.py`
currently assumes Windows `.venv/Scripts/python.exe`; do not assume it runs on
this machine. Select an existing suitable interpreter/dev command during build
without rewriting environment setup unless required. Node was unavailable for
this audit's attempted pure test. No server, credentials or external services
were exercised. Merge/deploy and actual contact actions are outside this update.

---

# Historical backend proposal — not tomorrow's build contract

Preserved original planning below. Its new-backend architecture, wider entities
and LLM/context scope do not override the narrow adaptation above.

<details>
<summary>Original broader proposal (historical, not active scope)</summary>

# Asthma Companion — BuildFest Backend Spec

## 1. Backend Goal

Build the simplest reliable backend necessary to support the BuildFest
Asthma Companion described in `../SPEC.md`.

This is a hackathon backend.

Prioritize:

1. working end-to-end functionality
2. fast frontend integration
3. reliable demo behavior
4. simple code
5. easy iteration

Do NOT optimize for production-scale architecture.

Avoid unnecessary:
- abstraction layers
- microservices
- complex dependency injection
- queues unless clearly needed
- multi-agent systems
- complicated authentication
- infrastructure work that does not improve the demo

---

# 2. Relationship to Existing Lobelia

This BuildFest application is a new prototype and product direction built on
prior Lobelia work.

BuildFest rules permit reuse of existing code where appropriate.

The existing Lobelia codebase SHOULD be inspected before implementing backend
functionality from scratch.

Reuse or adapt existing code when it is:
- already working
- understood
- relevant to the BuildFest requirements
- faster to adapt than rebuild
- unlikely to introduce unnecessary complexity

Potentially reusable areas include:

- FastAPI application setup
- database configuration and models
- Neon/PostgreSQL integration
- environmental API integrations
- weather retrieval
- AQI retrieval
- pollen retrieval
- LLM provider integration
- structured LLM output patterns
- profile/context handling
- existing asthma knowledge and medical sources
- prompts or guardrails that remain relevant
- utility functions
- testing infrastructure

Do NOT rebuild functionality merely for the sake of making the BuildFest
codebase independent.

However, reuse should be selective.

Do NOT automatically carry over:
- architecture that is unnecessary for this prototype
- complex RAG pipelines
- LangGraph/multi-agent workflows
- provider fallback systems
- vector databases
- authentication complexity
- ML risk-prediction infrastructure
- other dependencies that do not support the BuildFest demo

If an existing Lobelia component is useful but unnecessarily complex, prefer
extracting or simplifying the relevant portion.

The goal is:

REUSE WORKING FOUNDATIONS
+
BUILD NEW BUILDfest EXPERIENCES
+
REMOVE UNNECESSARY COMPLEXITY

Do not modify the original Lobelia implementation destructively. Preserve the
existing project while adapting/reusing code for the BuildFest application.

---

# 3. Backend Responsibilities

The backend primarily owns:

## Persistent data
- profile
- asthma-related profile information
- healthcare contact
- Asthma Action Plan
- calendar events
- check-ins
- companion conversation data if needed
- generated proactive companion messages

## Context
- retrieving relevant user information
- retrieving upcoming events
- retrieving recent check-ins
- retrieving/normalizing environmental information
- selecting relevant context for companion tasks

## Companion
- contextual chat
- daily briefing generation
- event-specific companion-message generation
- check-in response generation

## Environmental information
Initially:
- weather

If time permits:
- AQI
- pollen

## Proactive support
- generating daily briefing content
- generating event-specific content
- generating notification-ready content and timing metadata

The frontend may handle actual local notification scheduling.

---

# 4. Backend Does NOT Own

For this prototype, backend should NOT be responsible for:

- visual UI
- navigation
- symptom slider behavior
- emergency questionnaire progression
- Emergency / Red / Yellow / Green classification
- deciding whether the user medically requires emergency care
- phone deep links
- Maps deep links
- ML asthma-risk prediction

The asthma-state classifier is deterministic application logic implemented
outside the LLM.

Do not create an LLM endpoint that performs medical triage.

---

# 5. Core Architecture

Keep the architecture simple.

Conceptually:

Database / Stored Data
        |
        +-- Profile
        +-- Action Plan
        +-- Events
        +-- Check-ins
        +-- Optional conversation history
        |
        v
Context Builder
        |
        +-- Profile context
        +-- Recent check-in context
        +-- Event context
        +-- Environmental context
        +-- Relevant conversation context
        |
        v
Companion Service
        |
        +-- Chat
        +-- Daily Briefing
        +-- Event Message
        +-- Check-In Response

Environmental APIs feed normalized information into the Context Builder.

Do NOT implement these conceptual pieces as separate services/processes unless
that actually simplifies development.

A few simple modules/functions are sufficient.

---

# 6. Context Builder

Create a reusable mechanism for assembling relevant context for companion
tasks.

The goal is NOT to send every piece of stored information to the LLM.

Provide only information relevant to the current task.

The context system must gracefully tolerate missing data.

Examples:

- no recent check-in → continue without it
- no weather → continue without weather
- no upcoming events → chat still works
- no registered triggers → do not invent triggers
- no Action Plan → do not invent one

## Potential context sources

### Profile
- name
- known asthma triggers
- relevant asthma preferences/information

### Recent check-in
- mood
- shortness of breath
- cough
- wheezing
- chest tightness
- optional note
- timestamp

### Events
- today's events
- near-future events
- event being analyzed

### Environment
- current/forecast weather
- AQI if implemented
- pollen if implemented

### Conversation
- recent relevant messages if conversation persistence is implemented

---

# 7. Profile

Persist a single demo user's profile initially unless authentication is
implemented later.

Potential fields:

- id
- name
- knownTriggers[]
- usesReliever
- usesNebulizer
- usesPeakFlow
- peakFlowPersonalBest
- doctorName
- doctorPhone
- location
- notification preferences

Location should be sufficient for environmental lookup.

Do not build sophisticated location infrastructure for the hackathon.

Profile must support retrieval and updating.

---

# 8. Asthma Action Plan

Persist clinician-provided Action Plan information separately from generated
companion content.

Minimum fields:

- userId
- greenInstructions
- yellowInstructions
- redInstructions
- emergencyInstructions

These values are USER/CLINICIAN-PROVIDED DATA.

The LLM must NEVER rewrite, summarize in a way that changes meaning, or invent
these instructions.

The frontend can retrieve the plan and display the appropriate section after
its deterministic asthma-state classification.

The backend does NOT determine which zone applies.

---

# 9. Events

Support:

- create
- retrieve
- edit
- delete

Minimum event fields:

- id
- userId
- title
- description
- location
- startTime
- endTime

Optional/generated fields may include:

- companionMessage
- asthmaContext
- generatedAt
- intendedNotificationTime

Events should be retrievable by a useful time range so the frontend can
support Today/Day/Month views without separate APIs for each visual view.

Do not create separate backend concepts for Today, Day, Week, and Month unless
there is a real need.

---

# 10. Event-Specific Companion Messages

The companion can generate short messages for upcoming events.

Inputs may include:

- event information
- known triggers
- recent symptoms
- environmental context relevant to the event

Possible output:

- whether the event appears contextually relevant
- short companion message
- optional reason/context metadata
- generation timestamp
- intended notification time

Example:

Event:
Chemistry Lab

Known trigger:
Strong scents

Output:
> Chemistry lab is coming up. Since strong scents can bother your breathing,
> it may be worth preparing before you go. Good luck with lab!

Do NOT force asthma advice onto every event.

If there is no asthma-relevant concern, the companion may provide simple
encouragement or no proactive message.

Generated event messages should generally be cached/stored.

Opening the Today screen should NOT require a fresh LLM call for every event.

Regeneration can occur when useful, for example:
- event changes significantly
- environmental context becomes more relevant
- message is stale

Keep regeneration logic simple for the hackathon.

---

# 11. Check-Ins

Persist check-ins containing:

- id
- userId
- timestamp
- mood
- shortnessOfBreath
- cough
- wheezing
- chestTightness
- optionalNote

Symptom severity values should match the frontend's agreed representation.

Creating a check-in may also generate a SHORT supportive companion response.

Example behavior:

1. Save check-in.
2. Build relevant context.
3. Ask companion for a short response.
4. Return/store the response.

The companion response may acknowledge:
- mood
- symptoms
- optional note

It must NOT:
- diagnose
- assign Green/Yellow/Red/Emergency
- provide invented medication instructions

Check-in persistence must succeed even if LLM generation fails.

Provide fallback behavior if companion generation fails.

---

# 12. Environment Service

Environmental information is contextual input, not a medical classifier.

## Initial priority

Implement WEATHER first.

If easy/time permits:
- AQI
- pollen

Before building new integrations, inspect the existing Lobelia project for
working environmental-provider code that can be safely reused or simplified.

## Normalize provider responses

Do NOT pass large raw third-party API responses directly to the companion.

Normalize environmental information into a small internal structure.

Potential fields:

- location
- timestamp
- temperature
- feelsLike
- condition
- precipitation
- humidity
- AQI
- pollen

Not all fields are required.

The internal model should tolerate unavailable fields.

## Forecast relevance

For event-specific messages, use environmental information reasonably close
to the event time when available.

For daily briefings, use today's relevant conditions/forecast.

Do not build sophisticated forecast matching if it threatens hackathon scope.

## Medical interpretation

Do not invent environmental medical thresholds.

If deterministic thresholds are used for AQI, pollen, temperature, etc.,
they must come from an appropriate validated source or previously validated
Lobelia knowledge.

Otherwise, provide the environmental facts as context without pretending a
precise medical threshold exists.

---

# 13. Daily Briefing

Generate one daily companion briefing.

Potential context:

- today's weather
- AQI if available
- pollen if available
- known triggers
- recent symptoms/check-in
- today's activities

The briefing should synthesize relevant information rather than list raw API
values.

Example:

> Morning! It's going to be pretty cold this afternoon. Since cold air tends
> to bother your breathing, keep that in mind when you're heading out.

If nothing noteworthy is present:

> Good morning! Hope you have a good day today.

The briefing should be:

- short
- supportive
- relevant
- suitable for both the Today screen and a notification

Generate/cache it rather than requiring repeated generation whenever Today is
opened.

For the hackathon, it is acceptable to generate the daily briefing:
- on first request that day, OR
- through a simple explicit generation mechanism

A production scheduler is NOT required.

---

# 14. Companion Chat

The frontend should be able to send a user's message to the companion.

The backend should assemble relevant context rather than requiring frontend
to send the entire profile/calendar/environment state.

Potential chat context:

- profile
- known triggers
- latest/recent check-in
- today's/upcoming events
- current environmental context
- recent conversation

Do not blindly include everything.

Select reasonably relevant/current context.

## Safety behavior

The companion is NOT a medical triage agent.

If a message suggests acute breathing difficulty, the product should direct
the user toward the deterministic "I'm having trouble breathing" feature.

Where useful, companion output may contain both:

- display message
- structured UI action

Example conceptual action:

OPEN_BREATHING_FLOW

This allows frontend to show/open the deterministic safety flow.

Do not let the LLM itself decide an asthma zone.

---

# 15. Companion Output Structure

Prefer structured LLM outputs where they improve reliability.

For example, contextual event generation might conceptually return:

- relevant: boolean
- message: string
- reason: optional short string

Chat may conceptually return:

- message
- suggestedAction

Possible suggested actions should be narrowly defined.

For MVP:

- NONE
- OPEN_BREATHING_FLOW

Do not expose arbitrary model-generated commands to the frontend.

Validate model output before using it.

---

# 16. LLM System Behavior

The companion should be:

- supportive
- calm
- concise
- warm
- context-aware
- nonjudgmental

Avoid repetitive generic encouragement.

The LLM MAY:

- generate conversational responses
- acknowledge mood
- provide encouragement
- produce daily briefing language
- produce event-specific contextual messages
- explain non-safety-critical contextual information

The LLM MUST NOT:

- diagnose
- classify Emergency/Red/Yellow/Green
- determine medical triage
- invent medication
- invent dosage
- invent number of puffs
- invent nebulizer instructions
- invent steroid instructions
- modify the user's Action Plan
- contradict deterministic safety logic

If unsure, the model should be conservative.

---

# 17. Proactive Companion / Notification Content

The backend should support two proactive message types.

## DAILY_BRIEFING

Associated with:
- a date
- generated message
- generatedAt
- intendedSendTime if used

## EVENT_REMINDER

Associated with:
- event
- generated message
- generatedAt
- intendedSendTime

The backend does NOT need production push infrastructure for P0.

It may provide notification-ready content to the mobile application, which can
schedule local notifications.

Do not let notification infrastructure block core feature development.

---

# 18. Persistence Strategy

Use the simplest persistence approach that integrates quickly with the chosen
backend stack.

For the hackathon:

- a single seeded/demo user is acceptable
- authentication is not required unless it becomes trivial
- data models should leave room for userId without requiring full auth

Persist at minimum:

- profile
- Action Plan
- events
- check-ins

Persist/generated-cache if useful:

- daily briefing
- event companion messages
- conversation history

Do not build production-scale migrations/infrastructure unless required by the
chosen technology.

---

# 19. API Design Principles

Exact endpoints do not need to be predetermined before implementation.

Design APIs around actual frontend requirements as they become concrete.

Likely backend capabilities include:

- retrieve/update profile
- retrieve/update Action Plan
- create/read/update/delete events
- retrieve/create check-ins
- retrieve/generate daily briefing
- retrieve/generate upcoming event messages
- send companion chat message

Prefer a small API surface.

Avoid:
- separate endpoints for every UI screen
- endpoints that duplicate simple frontend logic
- endpoints for Emergency/Red/Yellow/Green classification

When endpoints are established, document their request/response schemas so
frontend can integrate reliably.

---

# 20. Failure Behavior

The application must degrade gracefully.

## LLM failure

If LLM generation fails:

- persisted operations must still succeed
- return/use a safe short fallback where appropriate
- do not break Today/check-in/calendar

## Environmental API failure

If weather/AQI/pollen retrieval fails:

- omit unavailable context
- companion still works from profile/events/check-ins
- do not fabricate environmental information

## Missing profile information

Do not infer unknown triggers, medications, doctors, or Action Plan content.

## Database failure

Return a clear application error rather than silently fabricating success.

---

# 21. Demo Seed Data

Prepare a deterministic demo user.

Suggested profile:

Name:
Elena or generic demo name

Known triggers:
- strong scents/chemicals
- cold air
- pollen

Healthcare:
- sample clinic/doctor information

Action Plan:
- clearly labeled sample clinician-provided instructions for Green/Yellow/Red
  states

Calendar:
- Chemistry Lab
- class/presentation
- social event

Recent check-in:
- enough data to demonstrate contextual companion behavior

Do not use real private health/contact information in public demo seed data.

---

# 22. Testing Priorities

Do not aim for exhaustive production test coverage.

Prioritize tests for behavior that could break the demo or safety boundary.

At minimum verify:

- event CRUD works
- check-in persistence works
- profile update/retrieval works
- Action Plan update/retrieval works
- context builder tolerates missing sources
- LLM failure does not break persistence
- environmental API failure degrades gracefully
- companion cannot directly modify Action Plan data
- structured companion output is validated
- chat can return OPEN_BREATHING_FLOW when appropriate

Safety-critical frontend classification should be tested separately by the
frontend implementation.

---

# 23. Development Order

Recommended order:

## Phase 0 — Reuse Audit

Before writing substantial new backend code:

1. Inspect the existing Lobelia backend.
2. Identify reusable components for:
   - FastAPI/server setup
   - database/persistence
   - environmental providers
   - LLM integration
   - profile/context handling
   - medical knowledge
3. Classify each relevant component as:
   - REUSE AS-IS
   - ADAPT
   - REBUILD SIMPLY
   - NOT NEEDED
4. Prefer reuse/adaptation when it saves meaningful implementation time.
5. Do not refactor the original Lobelia project unnecessarily.

Produce a short reuse plan before beginning substantial implementation.

## Phase 1 — BuildFest Foundation

Using the reuse plan:

- establish the BuildFest backend
- reuse/adapt existing infrastructure where beneficial
- remove unnecessary dependencies
- establish persistence
- seed demo data
- verify the backend runs independently enough for reliable development

## Phase 2 — Core Data
- Profile
- Action Plan
- Events
- Check-ins

Get frontend integration working as early as possible.

## Phase 3 — Context + Companion
- basic context builder
- companion provider
- contextual chat
- check-in response
- event-message generation

## Phase 4 — Environment
- weather integration
- normalized EnvironmentContext
- include weather in daily/event/chat context

## Phase 5 — Proactive Experience
- daily briefing
- event reminder content
- notification timing metadata

## Phase 6 — Stretch
- AQI
- pollen
- richer context selection
- conversation persistence
- additional notification behavior

Do NOT wait until every backend feature is complete before integrating with
frontend.

---

# 24. Coding-Agent Instructions

When using Codex or another coding agent:

1. Read `SPEC.md` and this file before substantial implementation.
2. Inspect existing code before editing.
3. Existing Lobelia code may be inspected, copied, reused, or adapted when
   BuildFest rules permit and doing so saves development time.
4. Before implementing a substantial capability from scratch, check whether
   Lobelia already contains a working implementation.
5. Do not destructively modify existing Lobelia functionality unless
   explicitly instructed.
6. Prefer:
   reuse > small adaptation > simple new implementation
   when reuse actually reduces complexity.
7. Do NOT reuse code merely because it exists. Avoid importing unnecessary
   architecture or dependencies into the BuildFest prototype.
8. Clearly distinguish reused/adapted code from newly implemented BuildFest
   functionality when documenting the project.
9. Do not modify frontend code unless explicitly asked.
10. Flag medical uncertainty rather than inventing behavior.
11. Preserve working functionality while adding features.
12. Commit/checkpoint frequently when appropriate.

---

# 25. Core Backend Principle

The backend is not primarily:

> CRUD plus an LLM endpoint.

Its main role is to provide the companion with the RIGHT CONTEXT at the RIGHT
TIME.

Conceptually:

PROFILE ───────────────┐
CHECK-INS ─────────────┤
EVENTS ────────────────┤
ENVIRONMENT ───────────┤
CONVERSATION ──────────┘
          |
          v
    CONTEXT BUILDER
          |
    ┌─────┼──────────────┐
    v     v              v
   CHAT  DAILY       EVENT-SPECIFIC
         BRIEFING    SUPPORT

Safety-critical asthma classification remains deterministic and outside the
LLM.

</details>
