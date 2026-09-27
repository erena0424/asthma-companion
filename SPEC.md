# Lobelia Asthma Companion — Tomorrow's Web Demo

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


## Current scope and precedence

This section is the active product direction. Adapt the existing React web app
and FastAPI backend in `asthma-app/`; do not start a replacement application or
assume a new backend is necessary. The earlier mobile/full-companion proposal
is preserved verbatim below as historical context, not tomorrow's acceptance
criteria. See `IMPLEMENTATION_PLAN.md` and `backend/SPEC.md` for the small build.
The backend portion is being implemented separately from the planned character
and help-screen frontend. Completion and verification are recorded in
`IMPLEMENTATION_PLAN.md`; page descriptions are not claims of a live UI.

## Who it helps and why

Target: adults living with asthma who want approachable everyday reflection and
quick access to a trusted person's details and their own support information.
Problem hypothesis: those details can be scattered or inconvenient to locate
when someone wants support. Intended benefit: fewer steps to find them and a
friendlier check-in. No improvement in health outcomes has been established.

Business hypothesis, unvalidated: a consumer-first companion may eventually
support optional paid personalization while basic access to saved support stays
free. First validate usefulness, repeat use, trust and willingness to pay; no
pricing or clinic demand is established. Clinic sponsorship is a later hypothesis.
No sales, outreach or monetization infrastructure belongs in tomorrow's demo.

## One small demonstration

1. In the existing profile experience, save a trusted contact's name and phone.
   Show a real successful save, then reload and retrieve that same contact.
2. Peyton's supplied character guides a short voluntary check-in. Use existing
   daily reflection fields and optional notes, without scoring/classification.
   Confirm saving only after the existing API acknowledges success.
3. Open an always-visible “I need help” entry in the companion area. Immediately
   show saved trusted contacts and the user's own care goal/accessibility needs
   as personal support information, with clear empty/error states.
4. A user-selected contact action opens the device's phone handler when supported;
   also display the number for manual use. This does not prove a call connected,
   a contact was notified or anyone responded. No automated message is sent.

The check-in must not gate the help screen. Help retrieval must not wait for
LLM, weather, forecast or character animation. No contact data is sent to an LLM.
On failed save show unsaved/retry status; never pretend data persisted. On failed
load distinguish unavailable from no saved contact. If a same-account in-session
last-loaded value is shown, label it as such; do not claim tested offline access.

## P0, later and boundaries

P0: reuse contact save/retrieval; supplied character and accessible text-guided
reflection; a simple help page with saved personal information; visible loading,
empty, failure and saved states; narrow integration verification on target device.
Keep existing auth/routing/layout and other working features intact. Hide legacy
forecast/risk content from this new companion/help path rather than presenting
it as acute assessment. Existing routes are not evidence of new capabilities.

Later: richer animation, mood model/history, automatic conversation memory, environment,
calendar enhancements or clinician-plan storage. Do not build these to complete
tomorrow's story. No emergency-zone questionnaire or clinical classification is
required by this revised demo.

This companion does not detect attacks, monitor the user continuously, dispatch
help or guarantee delivered alerts. Do not imply those capabilities. It provides
user-requested access to saved information and supportive reflection. It must not
generate medication/dose instructions or treatment plans. Any future displayed
clinician plan must be supplied by the user/clinician and preserved verbatim;
no such dedicated plan model was found in the inspected source.

## Limited continuity for the demo

Reuse the authenticated profile for user-confirmed care goals, accessibility
needs and trusted contacts, keeping those fields under their existing meanings.
Add one optional short user-approved check-in summary per user, labeled
`user-reported` with its observation date and server save timestamp. The user
can view it, explicitly approve a correction/replacement, or delete it. A later
session may retrieve this background context; current corrections take priority.
Saving the summary is a separate explicit action, never a side effect of chat
or a check-in. No full conversation is retained and no diagnosis, medication,
trigger or treatment instruction is inferred. The summary is not an instruction
to the character or verified medical guidance. No vector or memory service is
needed. Saving or deleting this summary does not create or erase an independent
legacy check-in record; the frontend must distinguish those actions.

Demonstrate two authenticated sessions: save user-confirmed support information
and an approved summary in the first, retrieve the same context in the second,
then correct/delete and verify the old summary is no longer returned. Also
verify a second user cannot retrieve or mutate it. Character rendering and the
optional-save/view/correct/delete controls remain frontend integration work.

## Character, assets and credit

Use the character supplied or identified by Peyton; confirm its creator and
attribution rather than assuming authorship. Do not use a generated replacement
or an existing logo relabeled as that character.
The inspected repo contains lung/flower and Lobelia logo assets, but no asset
identified as Peyton's character. Obtain the asset/path and attribution wording
before declaring character integration complete. Layout/wiring can proceed with
an explicitly temporary placeholder; remove it for the completed character demo.
Preserve existing asset credits, font licenses and the root MIT LICENSE
(Copyright 2026 ychang326); do not infer authorship of uncredited images.

## Evidence and acceptance

Static source inspection verified contact/profile and check-in request wiring;
it did not establish live server/database, current browser behavior or working
phone handoff. No help route or Peyton character integration was found. A safe
existing pure frontend test was attempted, but `node` was unavailable in this
execution environment; no tests passed or live behavior is claimed here.

Acceptance: save/reload contact, preserve own support information, complete and
save a non-diagnostic reflection, reach help directly, render correct saved
contact with user-initiated device handoff and honest unsupported-device behavior.
Test absent contact, failed save/load, keyboard navigation, narrow viewport and
no LLM/forecast call dependency in this path. Do not contact a real person during
QA; use fictitious records and stop before initiating a real call.

---

# Historical proposal — superseded for tomorrow's demo

The following original specification is preserved for provenance and possible
future exploration. Its mobile architecture, clinical classification, memory,
calendar and generated guidance scope are not current implementation instructions.

<details>
<summary>Original broader proposal (historical, not active scope)</summary>

# Asthma Companion — BuildFest Product Spec

## 1. Product Overview

We are building a mobile asthma companion focused on the day-to-day and
emotional experience of living with asthma.

Instead of giving users one generic asthma recommendation per day, the app
supports them throughout their day using:

1. A cute, supportive asthma companion
2. A daily environmental briefing
3. Context-aware support around upcoming activities
4. Mood + asthma symptom check-ins
5. Calendar and daily planning
6. Companion chat that understands the user's current context
7. A structured "I'm having trouble breathing" safety flow
8. The user's saved Asthma Action Plan and healthcare contacts

The companion connects these features together.

The product should feel supportive, personal, and calm rather than like a
clinical dashboard.

---

# 2. Core Product Concept

The companion should understand relevant context about the user's day.

Depending on what data is available, this may include:

- asthma profile
- known triggers
- recent symptoms/check-ins
- emotional mood
- today's and upcoming activities
- weather
- air quality
- pollen
- recent conversation

This context powers three primary companion interactions:

## A. Daily Briefing

Once per day, the companion summarizes relevant environmental conditions and
anything the user may want to keep in mind.

Example:

> Morning! It's going to be pretty cold this afternoon. Since cold air tends
> to bother your breathing, keep that in mind when you're heading out.

If there is nothing particularly concerning, the companion can simply provide
a friendly short greeting.

## B. Event-Specific Support

Before relevant upcoming activities, the companion can provide asthma-related
preparation advice or encouragement.

Example:

Upcoming event:
> Chemistry Lab — 2:30 PM

Known trigger:
> Strong scents

Companion:
> Chemistry lab is coming up. Since strong scents can bother your breathing,
> it may be worth making sure the asthma supplies you normally use are
> accessible. Good luck with lab!

Not every event requires an asthma warning or notification.

## C. Contextual Chat

Users can talk directly to the companion.

The companion should already understand relevant current context instead of
requiring the user to repeatedly explain their day.

Example:

User:
> I'm kind of nervous about lab today.

The companion may already know:
- Chemistry Lab is at 2:30 PM
- strong scents are a registered trigger
- the user's recent check-in
- today's environmental conditions

These three experiences should share the same underlying user/context data
rather than behaving like unrelated AI features.

---

# 3. Core Demo Story

Optimize development around one polished demo rather than implementing every
possible feature.

Example:

1. User opens the app in the morning.
2. Companion provides today's greeting/environmental briefing.
3. Today's schedule shows upcoming activities.
4. Chemistry Lab has relevant asthma context because scents/chemicals are a
   known trigger.
5. Companion provides a short message associated with the event.
6. User completes a mood + asthma check-in.
7. Companion responds supportively.
8. User talks briefly with the companion, which understands today's context.
9. Later, user taps "I'm having trouble breathing."
10. App performs immediate danger-sign screening.
11. If no danger signs exist, app performs a structured asthma assessment.
12. Deterministic rules classify the situation.
13. App immediately surfaces the appropriate saved Asthma Action Plan
    instructions and contact options.

Critical parts of this demo should not depend on an unpredictable live LLM
response.

---

# 4. Scope

## P0 — Must Work

- Today/Home
- companion
- today's events
- daily briefing
- event-specific companion messages
- mood + asthma check-in
- basic Day calendar
- create/edit/delete events
- contextual companion chat
- "I'm having trouble breathing" flow
- deterministic Emergency / Red / Yellow / Green classification
- saved Asthma Action Plan
- saved healthcare contact
- basic persistence

## P1 — If Time Permits

- actual scheduled mobile notifications
- simple check-in history
- Month calendar
- weather integration
- AQI integration
- pollen integration
- nearest-ER Maps integration
- richer companion animation

The companion architecture should tolerate missing environmental sources.

For example, if pollen is not implemented, the companion should still work
using profile + events + check-ins + weather.

## P2 — Do Not Prioritize

- ML asthma-risk prediction
- Google/Apple Calendar synchronization
- sophisticated analytics
- complex RAG
- multi-agent architecture
- complex authentication
- production-scale infrastructure
- fully featured Week calendar
- Action Plan PDF/OCR import

---

# 5. Main Navigation

Expected primary navigation:

- Today
- Calendar
- Check-ins
- Chat
- Profile

Exact visual implementation is owned by frontend/design and may change.

"I'm having trouble breathing" should be prominently accessible and should not
be buried in chat or settings.

---

# 6. Companion Personality & UX

The companion is a central element of the product.

It should feel:

- warm
- supportive
- concise
- calm
- personal
- cute without feeling childish

The companion may:

- greet the user
- provide the daily briefing
- react to check-ins
- acknowledge emotional mood
- provide event-specific support
- provide encouragement
- chat with the user

Avoid excessive repetitive encouragement such as repeatedly saying
"You've got this."

The companion may acknowledge mental/emotional health in a subtle way.

Example:

> How are you feeling today?
> Anything you want to talk about? I'm here.

Medical/safety screens should prioritize clarity and low cognitive load over
the companion's personality.

---

# 7. Today / Home

Today is the primary screen and should receive high visual priority.

It should contain:

- companion greeting / daily briefing
- today's schedule
- upcoming events
- contextual companion messages where relevant
- access to check-in
- prominent access to "I'm having trouble breathing"

Example:

### Morning companion briefing

> Morning! It's going to be cold and windy this afternoon. Since cold air is
> one of your triggers, keep that in mind when you're heading out.

### 2:30 PM — Chemistry Lab

> Strong scents can bother your breathing. It may be worth making sure your
> usual asthma supplies are accessible before lab. Good luck!

### 6:00 PM — Dinner with Maya

> Have fun tonight!

Do not force asthma advice onto every activity.

---

# 8. Calendar & Events

For the hackathon, the application has its own calendar.

External calendar synchronization is not required.

Users should be able to:

- create events
- view events
- edit events
- delete events

An event minimally contains:

- id
- title
- description (optional)
- start time
- end time
- location (optional)

The system may associate additional contextual information with an event:

- asthma relevance
- contextual companion message
- notification time
- relevant environmental context

## Views

Priority:

1. Today / Day
2. Month
3. Week only if time remains

Day view should resemble a familiar vertical mobile calendar.

---

# 9. Daily Environmental Briefing

The companion should be capable of producing one daily environmental update.

Potential context:

- weather
- temperature
- relevant weather conditions
- AQI
- pollen
- user asthma triggers
- recent symptoms
- today's activities

Environmental information should be normalized before being provided to the
companion.

The companion should NOT receive a large raw weather/API response and be
expected to determine everything itself.

Conceptually, environmental context might contain:

- temperature
- feels-like temperature
- weather condition
- precipitation
- humidity
- AQI
- pollen level

Relevant environmental conditions may then be related to known user triggers.

Do not invent medical thresholds for environmental danger.

Environmental sources can be added incrementally.

Weather should be prioritized over AQI/pollen if time is limited.

---

# 10. Event-Specific Companion Messages

The system should be capable of generating contextual messages for upcoming
events.

Relevant context may include:

- event
- profile
- known asthma triggers
- latest/recent check-in
- environmental conditions around the event

The output should be short enough for a mobile card or notification.

The system should distinguish between:

### Asthma-relevant event

Example:

> Chemistry lab is coming up. Since strong scents can bother your breathing,
> it may be worth preparing before you go.

### Non-asthma-relevant event

The companion may provide simple encouragement:

> Good luck with your presentation!

Not every event needs a proactive notification.

Generated messages may be cached so that opening Today does not require
waiting for an LLM every time.

---

# 11. Notifications

Notifications are intended to make the companion proactive.

Two primary notification types are envisioned:

## Daily briefing

Sent once per day.

Example:

> Morning! Pollen is high today, and you mentioned pollen is one of your
> triggers. Take care when you're outside today.

## Upcoming event

Sent before a relevant event.

Example:

> Chemistry lab in 30 minutes! Strong scents can be a trigger for you, so it
> may be worth preparing before you go.

For the hackathon, actual production push infrastructure is NOT required.

The backend may generate/store:

- message
- type
- associated event if applicable
- intended send time

The mobile application may schedule local notifications.

If notification infrastructure becomes time-consuming, demonstrate the
message-generation behavior without allowing notifications to block the core
demo.

---

# 12. Check-In

The normal check-in captures BOTH emotional state and asthma symptoms.

## Mood

Ask something similar to:

> How are you feeling?

Use a friendly visual scale/faces.

Mood means emotional/mental state, not asthma severity.

Optionally:

> Anything you want to talk about?

The companion may provide a short supportive response.

## Asthma symptoms

Collect at minimum:

- shortness of breath / difficulty breathing
- cough
- wheezing
- chest tightness

Use a consistent scale:

NONE → MILD → MODERATE → SEVERE

NONE should be on the LEFT.

Save check-ins for later context/history.

The normal check-in does not rely on an LLM to make medical classifications.

---

# 13. "I'm Having Trouble Breathing"

This is a safety-oriented flow.

It should be usable while someone is experiencing breathing difficulty.

Questions should generally be shown ONE AT A TIME.

Medical classification must be deterministic.

An LLM must NEVER determine:

- Emergency
- Red
- Yellow
- Green

Priority:

EMERGENCY > RED > YELLOW > GREEN

---

# 14. Emergency Screening

Screen for danger signs BEFORE performing the longer asthma assessment.

Ask one at a time.

At minimum:

1. Are you having trouble talking or walking because you are short of breath?
2. Do your lips or fingernails look blue, pale, or gray?
3. Are you confused or unusually drowsy?

If ANY danger sign is present:

- stop assessment immediately
- classify as EMERGENCY
- show emergency actions

Do not require completion of remaining questions.

## Emergency Result

Keep the screen extremely simple.

Primary actions:

- Call 911
- Find nearest ER

Saved clinician-provided emergency instructions may also be displayed, but
must not delay access to emergency help.

---

# 15. Non-Emergency Asthma Assessment

If no immediate danger signs exist, continue with structured assessment.

Collect:

- shortness of breath
- cough
- wheezing
- chest tightness

Also assess:

## Activity limitation

Conceptual answers:

- can perform normal activities
- can perform some but not all normal activities
- cannot perform normal activities

## Night waking

Ask whether asthma woke the user from sleep.

## Reliever use

Ask whether the user used their prescribed reliever for the current symptoms.

If yes, ask whether it helped.

Do not invent medication instructions.

## Peak flow

Only ask if the profile indicates that the user uses a peak-flow meter.

Interpret relative to personal best when available.

---

# 16. Asthma State Classification

Classification is deterministic application logic.

Do NOT:

- use an LLM
- use ML
- create an arbitrary weighted symptom score
- invent medical thresholds

Evaluate most severe → least severe.

## EMERGENCY

Any emergency danger sign → EMERGENCY.

## RED

Relevant criteria include:

- very short of breath / breathing is very difficult
- prescribed quick-relief treatment has not helped
- cannot perform usual activities
- symptoms remain the same or worsen after following Yellow-zone treatment
  when reassessment is required
- peak flow <50% personal best when used

Do not invent rules such as:

> three moderate symptoms = Red

## YELLOW

If Emergency/Red criteria are absent, relevant criteria include:

- cough
- wheezing
- chest tightness
- shortness of breath
- asthma waking user at night
- some limitation of normal activities
- peak flow approximately 50–79% personal best when used

## GREEN

If none of the above apply:

- no asthma symptoms
- normal activity
- peak flow >=80% personal best when used

A person entering specifically through "I'm having trouble breathing" will
rarely end in Green. This is expected.

---

# 17. Asthma Action Plan

Classification and medical instructions are separate.

First determine the state.

Then retrieve instructions.

## Saved clinician-provided plan

Allow users to register instructions for:

- Green
- Yellow
- Red
- emergency, if applicable

After classification, automatically display the relevant saved instructions.

Do not merely tell users:

> Check your Asthma Action Plan.

## No saved Action Plan

Provide only conservative, validated generic guidance.

Never invent:

- medication
- number of puffs
- nebulizer dose
- steroid dose
- medication frequency

Medication-specific instructions must come from saved clinician instructions
or separately validated static content.

---

# 18. Profile

Profile should minimally support information needed by other features.

Potential fields:

- name
- known asthma triggers
- uses prescribed reliever/rescue inhaler
- uses nebulizer
- uses peak-flow meter
- personal-best peak flow
- doctor/clinic name
- doctor/clinic phone
- location/environment preferences
- preferred notification settings

Profile also provides access to saved Asthma Action Plan information.

---

# 19. Companion Chat

Users can talk directly to the companion.

The user should not need to manually provide all relevant context with every
message.

Depending on availability, companion context may include:

- profile
- triggers
- recent check-in
- current mood
- today's/upcoming events
- environmental conditions
- recent conversation

The companion should use only context relevant to the conversation.

If the user reports acute breathing difficulty, the companion should direct
the user toward the deterministic "I'm having trouble breathing" flow rather
than independently conducting medical triage.

---

# 20. LLM Safety Boundary

The LLM MAY:

- generate daily briefing language
- generate event-specific messages
- provide encouragement
- respond conversationally
- acknowledge emotional context
- explain already-determined information

The LLM MUST NOT:

- classify Emergency / Red / Yellow / Green
- diagnose
- independently decide whether emergency care is medically necessary
- invent medication instructions
- invent medication doses
- alter saved Asthma Action Plan instructions
- override deterministic safety logic

Safety-critical actions must never depend on successful LLM generation.

---

# 21. Shared Data Concepts

Frontend and backend should share the same conceptual objects.

Exact API contracts may be defined during implementation.

## Profile

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
- notificationPreferences

## ActionPlan

- userId
- greenInstructions
- yellowInstructions
- redInstructions
- emergencyInstructions

## Event

- id
- userId
- title
- description
- location
- startTime
- endTime

Optional generated/context fields:

- companionMessage
- asthmaContext
- notificationTime

## CheckIn

- id
- userId
- timestamp
- mood
- shortnessOfBreath
- cough
- wheezing
- chestTightness
- optionalNote

## EnvironmentalContext

Potential fields:

- timestamp
- location
- temperature
- feelsLike
- condition
- precipitation
- humidity
- AQI
- pollen

Not every field must be implemented.

## ProactiveCompanionMessage

Potential fields:

- id
- type
- message
- associatedEventId (optional)
- generatedAt
- intendedSendTime

Possible types:

- DAILY_BRIEFING
- EVENT_REMINDER

---

# 22. Conceptual Context Architecture

The companion should use a shared context layer rather than each AI feature
independently assembling unrelated information.

Conceptually:

Profile ─────────────┐
Recent Check-In ─────┤
Events ──────────────┤
Environment ─────────┤ → Relevant User Context
Conversation ────────┘
                              |
               ┌──────────────┼──────────────┐
               ↓              ↓              ↓
             CHAT       DAILY BRIEFING   EVENT MESSAGE

Missing data sources must not break the system.

For example:

- no weather → companion still works
- no recent check-in → companion still works
- no events → chat still works

Only relevant context should be supplied for each task.

---

# 23. Frontend / Backend Responsibility

## Frontend / Local App

Primarily owns:

- visual design
- navigation
- question-by-question assessment UI
- deterministic Emergency/Red/Yellow/Green classification
- symptom controls
- displaying Action Plan instructions
- phone/Maps deep links
- local notification scheduling where appropriate

## Backend

Primarily owns:

- persistence
- profile
- events
- check-ins
- Action Plan storage
- healthcare contact storage
- environmental-data retrieval/normalization
- context compilation
- companion chat
- daily briefing generation
- event-specific message generation
- notification-message generation

Exact API endpoints will be defined during implementation rather than
prematurely fixed here.

---

# 24. Development Principles

This is a hackathon.

Prioritize:

1. polished working demo
2. user experience
3. reliability
4. clarity
5. development speed

Do not optimize for production-scale architecture.

Frontend may develop against mock data while backend is being built.

Integrate early.

Use AI coding tools heavily for implementation, but humans own:

- product decisions
- design decisions
- medical/safety decisions
- architecture boundaries

Do not allow coding agents to add unnecessary abstractions or infrastructure.

## Existing Code and Prior Work

This project builds on ideas and technical work from the previous Lobelia
project.

BuildFest rules permit reuse of existing code where appropriate. The team may
reuse or adapt existing Lobelia components, infrastructure, integrations, and
implementation patterns when doing so accelerates development.

However, the BuildFest project should demonstrate substantial new work and a
distinct product direction, including the mobile companion experience,
calendar/event-aware support, proactive interactions, mental/emotional
support, and structured breathing-help flow.

When reusing existing code:
- understand what is being reused
- adapt it intentionally to the new product
- avoid carrying over unnecessary complexity
- prioritize new BuildFest functionality and demo quality
---

# 25. Demo Reliability

Use predictable demo data.

Suggested demo profile:

- known scent/chemical trigger
- doctor/clinic saved
- clinician-provided sample Action Plan
- several calendar events
- Chemistry Lab as an upcoming event

The demo should remain usable if:

- LLM API fails
- environmental API fails
- network is slow

Use cached or seeded fallback companion content where needed.

---

# 26. Medical Safety

Medical behavior must be grounded in authoritative asthma guidance, including
sources such as:

- CDC asthma guidance / Asthma Action Plan
- NHLBI Asthma Action Plan
- GINA asthma guidance

Do not invent clinical thresholds.

If a medical rule is uncertain, flag it for review rather than guessing.

The prototype does not replace professional medical care.

---

# 27. Product Principle

This is NOT:

> An LLM that gives asthma advice.

It is:

> A supportive asthma companion that understands the user's day and
> environment, helps them manage asthma in context, supports the emotional
> side of living with asthma, and quickly surfaces structured personalized
> safety information when symptoms worsen.

When scope decisions are necessary, prioritize features that best demonstrate
this idea.

</details>
