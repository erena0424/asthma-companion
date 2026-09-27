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

## How the AI Companion Works

The backend assembles relevant context, sends it to the configured LLM, and validates the structured reply before returning a short conversational message to the frontend.

- **Model providers:** Google Gemini or Anthropic Claude, selected through `LLM_PROVIDER`.
- **Personal context:** Saved profile information, upcoming saved calendar plans, and an explicitly approved check-in summary can inform the conversation when saved context is enabled.
- **Forecast context:** The companion can reference an existing stored forecast with its date and uncertainty; it does not generate or recalculate the forecast itself.
- **Conversation continuity:** A bounded recent conversation history supports follow-up replies. Chatting does not automatically save a new long-term summary.
- **Fallback behavior:** If generation fails or times out, the service returns a simple fallback message.

The LLM is prompted to provide supportive conversation without diagnosis, urgency classification, or medication instructions. Saved contacts remain available through the separate support flow.

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

```bash
git clone https://github.com/erena0424/lobelia-asthma-companion.git
cd lobelia-asthma-companion
```

For the LLM companion implementation, switch to its development branch:

```bash
git switch feature/companion-demo-backend
```

### Backend

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

Open http://127.0.0.1:8000/docs for interactive API docs.

### Frontend

In a separate terminal, from the repository root:

```bash
cd asthma-app/frontend
npm install
npm run dev
```

Open the local URL printed in the terminal.


## Development Status

This project is an **in-progress BuildFest demo**. The `feature/companion-demo-backend` branch includes LLM-powered chat and opening-message endpoints, contextual reply generation, and configurable conversational tones. The default branch currently documents a narrower contact, reflection, and support flow.

This README describes the companion direction, including that branch's AI functionality. Implementation in source does not establish that the complete demo has been deployed or rehearsed. See the [implementation plan](IMPLEMENTATION_PLAN.md) and [backend setup guide](asthma-app/docs/BUILDFEST_BACKEND_SETUP.md) on the branch you are using for integration and verification details.

## Inspiration & Credits

This project builds on [Lobelia](https://github.com/Lobelia-Mirror-Lake/Lobelia) and its exploration of everyday asthma self-management, narrowing the BuildFest experience to approachable reflection and access to personal support information.

Existing code, asset, and font credits are retained. Companion character attribution should be confirmed when the supplied artwork is integrated.

## Disclaimer

This is a demonstration prototype, not a medical device or a substitute for professional medical advice or an asthma action plan. It does not diagnose or assess asthma attacks, provide treatment instructions, continuously monitor users, or dispatch emergency help.

## License

Released under the [MIT License](LICENSE). Existing copyright notices and separate asset and font licenses continue to apply.



