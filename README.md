# Lobelia-asthma-companion

**A small companion for everyday reflection and easier access to support.**

Lobelia Asthma Companion is a lightweight web app being developed for a **BuildFest demo**. It explores how a friendly, character-guided experience can help adults living with asthma check in with themselves and find their saved support information in fewer steps.

Built on the existing Lobelia application, this demo focuses on one simple journey:

**Save a trusted contact → Complete a guided check-in → Access support information.**

[Project scope](SPEC.md) · [Implementation plan](IMPLEMENTATION_PLAN.md) · [Backend design](backend/SPEC.md)

## The Demo

The planned experience brings together three moments:

- **Keep someone close.** Save a trusted contact’s name and phone number, then retrieve those details when needed.
- **Take a moment to reflect.** Follow a short, voluntary check-in with a companion character, simple prompts, and optional notes.
- **Find support quickly.** Open “I need help” to view saved contacts, personal care goals, and accessibility needs without completing a check-in first.

An optional, explicitly approved check-in summary can carry context into a later session. Users remain in control of viewing, replacing, or deleting that summary.

Contact actions open the device’s phone handler where supported; the number also remains visible for manual use. The app does not automatically send alerts or confirm that a call connected.

## Project Structure

```text
lobelia-asthma-companion/
├── asthma-app/                 # Existing application
│   ├── frontend/               # React + Vite frontend
│   ├── api/                    # FastAPI endpoints
│   ├── services/               # Backend business logic
│   ├── db/                     # Database models and support
│   └── docs/                   # API and setup documentation
├── backend/                    # Backend adaptation specifications
│   └── SPEC.md
├── SPEC.md                     # Active product scope
├── IMPLEMENTATION_PLAN.md      # Implementation and verification status
└── LICENSE
```

The frontend lives in `asthma-app/frontend/`. The demo reuses the existing backend inside `asthma-app/`; `backend/` currently holds the adaptation specification rather than a separate server.

## Tech Stack

- **Frontend:** React, Vite, Bootstrap
- **Backend:** Python, FastAPI
- **Database:** PostgreSQL, with Alembic migrations

The companion’s help flow is designed to retrieve saved information without waiting for AI chat, weather data, or risk forecasts.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/erena0424/lobelia-asthma-companion.git
cd lobelia-asthma-companion
```

### 2. Set up the backend

Follow the [application setup guide](asthma-app/README.md) to configure the Python environment, database, and environment variables. Then use the [BuildFest backend setup guide](asthma-app/docs/BUILDFEST_BACKEND_SETUP.md) for the required migration and verification steps before starting the API.

### 3. Start the frontend

In a separate terminal, from the repository root:

```bash
cd asthma-app/frontend
npm install
npm run dev
```

Open the local URL printed in the terminal. Saving and retrieving user data also requires the configured backend and application authentication.

## Development Status

This project is an **in-progress demo**. The backend continuity changes are implemented, and the repository records six passing isolated tests. Character integration, the help screen, and frontend summary controls still need integration and verification. A live database migration and a full end-to-end rehearsal have not yet been completed.

See the [implementation plan](IMPLEMENTATION_PLAN.md) for progress and the [backend checks](asthma-app/docs/BUILDFEST_BACKEND_SETUP.md) for verification details. Older proposals retained in the specifications describe historical ideas beyond the current demo scope.

## Disclaimer

This is a demonstration prototype, not a medical device or a substitute for professional medical advice or an asthma action plan. It does not diagnose or assess asthma attacks, provide treatment instructions, continuously monitor users, or dispatch emergency help.

## License

Released under the [MIT License](LICENSE). Existing copyright notices and separate asset and font licenses continue to apply.



