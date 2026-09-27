# Tomorrow's existing-web-app implementation plan

## Authorized supportive companion extension — current demo scope

The latest demo request adds a warm, context-aware companion and a dated stored
forecast within that interaction. This supersedes the earlier exclusion of LLM
integration/forecast from the companion path below. Breathing-help backend work
and any questionnaire are deferred until time permits; none is implemented by
this extension. Existing trusted-contact support remains available through the
existing profile API. No new clinical rules or emergency claims are introduced.

Implemented backend: additive authenticated `POST /v1/companion/chat`, reusing
existing provider SDK configuration, JWT/DB and cached forecast models. Existing
`/v1/chat` and forecast generation remain unchanged. The existing chat UI now
calls the new companion endpoint. No new
schema or dependencies. Friendly, calm, concise persona is shared by this new
endpoint's prompt; persona alone is not continuity. Request-opt-in saved context
reads current user-confirmed profile fields and the latest approved summary.
No full chat storage, episode recall, inferred memories or contact data sent to AI.
Saving a summary and choosing to send saved context to the provider are distinct.

Forecast is structured alongside the reply with source/target dates and explicit
unavailable/stale/current/future state, based on server-local target-date relevance.
It is not an acute breathing assessment. Missing forecast does not block chat;
provider failure returns predefined nonclinical fallback. No automatic provider
failover, new medical advice, help action, dispatch or alert delivery is added.
See `asthma-app/docs/API.md` for exact requests, responses and integration notice.

Backend files: `asthma-app/api/companion.py`, `services/companion_service.py`
(under asthma-app), registration in `asthma-app/api/main.py`, and isolated
`asthma-app/tests_demo/test_companion.py`. Seven companion tests plus six existing
support tests pass with fake providers and disposable SQLite. This verifies
scoping, opt-in/correction/deletion, dates, no writes, validation and fallbacks;
it does not verify real model quality, clinical safety, live Postgres/provider
availability, browser integration or end-to-end demo operation.

The chat sends up to four recent successful exchanges (8 alternating user/assistant
messages, 1200 characters each, 6000 total), kept only in React memory. No full chat
is saved to the database or browser storage. Greeting, errors, fallback replies and
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

Verification: 15 isolated backend tests, 6 mounted chat tests and 17 existing
frontend tests; production build to /tmp. Mocked providers/disposable SQLite only;
no live provider, Postgres or browser verification. Mounted tests run via
`JSDOM_MODULE=/tmp/lobelia-ui-test-tools/node_modules/jsdom/lib/api.js node --test tests/companionChat.test.mjs`.
Peyton's supplied asset and real runtime rehearsal remain outstanding. Test a
fictitious approved summary across sessions, then correct/delete and repeat.
PR16 remains separate; its Profile changes are not included here.


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


Status: narrow backend implementation complete with six isolated tests passing;
frontend work pending. Work stays in this repository's `asthma-app/`, not a new
application/backend. Active scope is the opening section of `SPEC.md` and
`backend/SPEC.md`; historical full-mobile plans are not acceptance criteria.
No live migration, merge, deployment or real contact action performed.

## Evidence and smallest useful change

| Current source | What exists / intended reuse |
|---|---|
| `asthma-app/frontend/src/App.jsx:53`, `constants.js:3` | React HashRouter, guarded dashboard routes; reuse shell/auth. No help route found. |
| `components/pages/ProfilePage.jsx:309`, `helper-functions/profile.js:34` | Saved contact PATCH and profile GET; reuse API and contact management, verify runtime. |
| `components/input/EmergencyContactsManager.jsx:33`, `ContactModal.jsx:43` | Contact CRUD and field validation UI. Modal closes immediately after submit at line 61; adjust honest async save/error feedback. |
| `components/pages/ProfilePage.jsx:735`, `components/input/ContactCard.jsx:50` | Contact name/number display; no phone action. Adapt for user-initiated help access. |
| `components/pages/CalendarPage.jsx:180`, `helper-functions/checkIns.js:40` | Daily boolean/notes check-in POST. Reuse data meanings and helper, not forecast-success wording at CalendarPage line 207. |
| `api/users.py:86`, `db/models.py:47` | Existing auth-scoped profile/contact storage; no new contact table. |
| `api/users.py:56`, `db/models.py:51` | User-entered care_goal/accessibility_needs already persist; expose under their real meanings, not clinical instructions. New editor may be needed. |
| `api/check_ins.py:66`, `services/check_in_service.py:71` | Save exists, then forecast refresh follows. Add narrow opt-out; don't redesign legacy forecasts. |
| `components/pages/HomePage.jsx:86`, `helper-functions/askCopilot.js:4` | Forecast-led Home and cached-forecast chat are not the new companion flow; preserve elsewhere. |

Frontend paths in table without prefix are under `asthma-app/frontend/src/`;
API/DB/service paths are under `asthma-app/`. These are inspected code paths,
not proof of a running demo. No help screen, Peyton character integration,
contact delivery service or clinician-plan persistence was found.

## Demo contract

Use a fictitious signed-in demo account with existing onboarding completed.
Save one trusted contact, reload to prove persistence, and optionally save a care
goal/accessibility need. Enter the companion experience, complete the existing
three daily reflection fields plus optional note, and save. Show acknowledgment
without a risk score or zone. Open “I need help” without waiting for check-in,
forecast or AI; show canonical saved contacts and user-entered personal fields.
Select a phone action to open the device handler or copy/read the displayed
number. Stop before a real call in testing; opening a handler is not delivery.

Peyton's actual supplied character is a required visual asset for the completed
character demo. No such identified asset was found. Use an explicitly temporary
placeholder during wiring only; do not relabel lung/flower branding as Peyton's
work. Preserve LICENSE/font notices and agree Peyton's attribution on delivery.
No generated character replacement is part of this plan.

## Checkpoint 1 — Existing save path and personal information

**Owner:** frontend-dev; backend-dev only for narrowly demonstrated data issues.
**Dependency:** usable existing local API/database/demo account; no new auth.

Files: `ProfilePage.jsx`, `EmergencyContactsManager.jsx`, `ContactModal.jsx`,
`helper-functions/profile.js`; backend `api/users.py` / `api/user_schemas.py`
only if required by validation/clearing checks. Reuse stored `emergency_contacts`
array. Add care-goal/accessibility editors using existing API fields if needed.
Do not add a plan schema or repurpose those fields as medication instructions.

Keep modal open/disable duplicate submit until save resolves, or show equally
clear page-level pending/error state; do not close-and-imply-success on rejection.
Refresh from server response. Prefer canonical array over stale legacy string;
if clearing contacts leaves stale compatibility text, fix that narrowly and test.
Never silently fill a failed save with mock persistence.

Check: create/update/clear contact round-trip; failed save remains visibly unsaved;
reload after successful save; personal text round-trip; account scoping and empty
contact state. Existing backend user tests are references, not new proof.

## Checkpoint 2 — Character-guided reflection without forecast dependency

**Owner:** frontend-dev plus bounded backend-dev change.
**Dependency:** checkpoint 1 save path; Peyton asset can arrive during layout work.

Files: proposed `frontend/src/components/pages/CompanionPage.jsx` and local CSS,
optional small `components/CompanionCharacter.jsx`, `App.jsx`, `constants.js`,
`DashboardLayout.jsx`; existing `helper-functions/checkIns.js`. Place the supplied
asset in the existing asset structure with provenance recorded. Add a focused
route/entry without replacing old Home/calendar/statistics implementation.

Guide one input at a time using ordinary supportive, non-diagnostic reflection.
Collect all three existing daily booleans intentionally; unanswered is not a
silent false. Optional notes can express feelings, but are not structured mood
history. Explain same-day update semantics. Reuse saveCheckIn; on this route pass
proposed `refresh_forecast=false` query option. `api/check_ins.py` adds that flag
(default true preserves old consumers), skips forecast work when false and keeps
compatible response. This opt-out requires no schema migration; the approved
summary extension adds the one nullable column described above. Do not display old burden/flare/risk
fields here. Character text can be predefined; no LLM integration needed.

Check: actual answers map correctly; no auto-submitted unanswered values; save
success/error and repeat-day update; new opt-out invokes no forecast/LLM; existing
default behavior remains unchanged. Test keyboard/focus/reduced-motion and narrow
viewport; character image has appropriate alt/text alternative. Help entry stays
available throughout and does not wait for animation.

## Checkpoint 3 — Help access and full rehearsal

**Owner:** frontend-dev; no new contact-dispatch backend.
**Dependency:** saved-profile data from checkpoint 1. Can proceed alongside 2.

Files: proposed `frontend/src/components/pages/HelpPage.jsx` and local CSS;
`App.jsx`, `constants.js`, `DashboardLayout.jsx`, companion entry and existing
profile helper/context. Read canonical contacts and personal fields; display
user-authored text verbatim under truthful headings. No data is sent to AI.

Provide explicit user-initiated `tel:` action only for a valid usable number,
and visible/manual-copy number for unsupported desktop/device behavior. No auto
call/message or claim of contact notification. No “help is coming” state. Handle
no contact with a profile-edit path, failed load with retry and an honest status,
expired auth with the existing sign-in flow. Do not falsely promise contact access
when authentication/network has prevented loading. In-session last-loaded values,
if used, must be tied to the same account and clearly marked; clear on sign-out.

Rehearse save → reload → character-guided check-in → direct help access on the
actual target browser/device. Verify help can open before completing check-in,
no forecast/LLM/weather wait, contact unchanged, no unintended real call and
clear empty/error/unsupported-device states. No claim of attack detection,
monitoring, dispatch or delivered alerts. If clinical wording is later added,
review it separately; do not improvise advice to fill a missing clinician plan.

## Validation and execution limits

Current inspection was read-only before these documentation edits. Attempted
`node --test src/helper-functions/forecastDisplayLogic.test.js` in frontend:
failed because `node` is not available in this execution environment. This test
is legacy forecast-display coverage, not help/contact evidence even if it passes.
No app/browser/server/DB/provider was started, and no integration behavior is
certified. Runtime setup is the first implementation check, not assumed complete.

Root package scripts delegate frontend to `asthma-app/frontend`. Build writes
tracked `frontend/docs`; inspect output changes before accepting a build.
Do not run root `deploy`/`done`: they push/publish. `backend-api` currently calls
a Windows-specific Python path; use a verified appropriate existing interpreter
or run script, not an assumed wrapper. Existing backend tests require a dedicated
test database and can recreate tables; never target a user's database.

Each checkpoint should be a small reviewable PR when implementation is requested,
with changed files and checks; dependent work can stack. Keep existing credits
and unrelated code intact. No automatic merge/deploy or infrastructure expansion.

## Inputs and time cuts

Required to finish actual demo: Peyton's asset + attribution, a working existing
runtime/account/database, and target demonstration device/browser for contact
handoff. These do not block documentation or page wiring. Use fictitious data.
No four-week sprint or feature-platform build is needed.

If time is tight: static character, three existing fields plus optional note,
one saved contact, two small routes. Drop animation/chat/automatic-memory/environment,
notifications and new clinical plan storage. Do not drop honest save/error states
or misrepresent a placeholder/phone handoff as a completed capability.
