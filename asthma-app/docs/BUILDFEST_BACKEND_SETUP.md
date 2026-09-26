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
