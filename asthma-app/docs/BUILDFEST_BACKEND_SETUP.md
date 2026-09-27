# Backend continuity setup and checks

Use the existing backend environment/dependencies and Postgres database. No new
service/provider/package is required. Before starting the updated API, apply the
additive Alembic migration to the intended development database from `asthma-app`:

```sh
python -m alembic upgrade head
```

Verify DATABASE_URL and DATABASE_URL_DIRECT point at that intended development
database before executing. The new head `e2f3a4b5c6d7` follows `d1e2f3a4b5c6`
and adds only nullable `users.support_memory` JSONB; old users start without a
summary. Existing schema history still requires pgvector for legacy episodes;
the new feature never uses vectors. Downgrade removes saved summaries, so do not
use it as a routine test. No migration has been applied by this implementation.

Start through the existing documented uvicorn entry after migration. Legacy app
startup still has its existing environment/model dependencies. This change does
not certify full startup or bypass authentication.

Safe focused verification from `asthma-app` with an installed requirements env:
```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests_demo -v
```

This suite deliberately does not load `tests/conftest.py`: that legacy fixture
can create/drop Postgres tables. It overrides environment before imports,
disables dotenv, uses disposable in-memory SQLite and test-only JSON type
substitution, real JWT authentication, and new DB sessions on each request.
Only the legacy forecast function is stubbed; disabled flow verifies no call,
legacy default verifies one call. It uses the shared production validation error
handler (400), including custom validator serialization. It verifies persistence
across sessions, correction/deletion, two-user isolation, explicit approval,
profile validation/contact clearing and check-in upsert. It does not prove
Postgres migration execution, disk restart, full server startup, browser behavior,
clinical safety or provider integrations. No live DB/provider is contacted.

Verification completed: six isolated tests passed. Offline PostgreSQL Alembic
SQL generation from d1e2f3a4b5c6 to e2f3a4b5c6d7 also passed, producing only
the nullable JSONB column addition and revision update. No live DDL was executed.

## Checkpoint 1 frontend checks

Profile now edits contacts, care goals and accessibility needs through the existing
API. Summary controls, character/check-in flow and help route are later work.

From asthma-app/frontend with Node and existing dependencies installed:

```sh
npm test
npm install --prefix /tmp/lobelia-ui-test-tools --no-audit --no-fund --ignore-scripts jsdom@26
JSDOM_MODULE=/tmp/lobelia-ui-test-tools/node_modules/jsdom/lib/api.js node --test tests/profileSupport.test.mjs
npm run build -- --outDir /tmp/lobelia-profile-support-build
```

The DOM dependency is temporary; application dependencies and the existing lockfile
are unchanged. Vite loads real components without environment files; fetch is
mocked and no API/database/provider is contacted. Five DOM tests and 17 existing
helper tests passed; the build passed with a bundle-size warning. DOM checks cover
pending/rejected contact saves, retry, add/delete/clear, personal text edits and
canonical GET after remount. They do not validate browser layout, focus behavior,
real authentication or database persistence.

For live verification, sign in with a fictitious account, edit a contact and both
personal fields, reload, then correct/clear and reload again. Temporarily block
PATCH in browser developer tools to verify the draft stays visible on failure
and retry works. No real call/message action belongs to this checkpoint.
