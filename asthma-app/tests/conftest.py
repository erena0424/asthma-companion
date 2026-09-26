"""Shared pytest fixtures for API integration tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure asthma-app root is importable (same as uvicorn --app-dir .)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault(
    "DATABASE_URL",
    os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/mirror_lake_test",
    ),
)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("EMBEDDING_PROVIDER", "stub")

from dotenv import load_dotenv

# Load API keys from .env without overriding test DATABASE_URL / JWT_SECRET above.
load_dotenv(_ROOT / ".env", override=False)

from collections.abc import Generator
from typing import Callable
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from api.main import app
from db.database import Base, get_db


def _ensure_test_database() -> str:
    url = os.environ["DATABASE_URL"]
    if not url.endswith("mirror_lake_test"):
        return url
    admin_url = url.rsplit("/", 1)[0] + "/postgres"
    try:
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'mirror_lake_test'")
            ).scalar()
            if not exists:
                conn.execute(text("CREATE DATABASE mirror_lake_test"))
        admin_engine.dispose()
    except Exception:
        pass
    return url


@pytest.fixture(scope="session")
def db_engine():
    _ensure_test_database()
    url = os.environ["DATABASE_URL"]
    if "mirror_lake_test" not in url and os.getenv("ALLOW_DROP_DB_FOR_TESTS") != "1":
        pytest.skip(f"Refusing to run destructive DB tests against non-test DATABASE_URL: {url}")
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not available for tests: {exc}")
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    except Exception as exc:
        pytest.skip(f"pgvector extension not available (use pgvector/pgvector:pg16 image): {exc}")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autocommit=False, autoflush=False)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    email = "testuser@example.com"
    password = "securepass123"
    register = client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "name": "Test User"},
    )
    assert register.status_code == 201, register.text
    token = register.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_env_fetch() -> Callable[..., AsyncMock]:
    async def _fetch_env_daily(*, lat: float, lon: float, day=None, provider=None):
        from datetime import date as date_cls

        return {
            "date": (day or date_cls.today()).isoformat(),
            "lat": lat,
            "lon": lon,
            "provider": provider or "openmeteo",
            "features": {
                "temperature": 20.0,
                "temperature_min": 15.0,
                "temperature_max": 25.0,
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
                "weed_pollen": "Low",
            },
            "missing": [],
            "cached": False,
        }

    return AsyncMock(side_effect=_fetch_env_daily)


@pytest.fixture
def mock_advice() -> Callable[..., AsyncMock]:
    async def _generate_advice(**kwargs):
        payload = {
            "summary": "Test advice summary.",
            "sections": [{"title": "Tonight", "body": "Rest and monitor symptoms."}],
            "disclaimer": "Educational only.",
            "llm_provider": kwargs.get("llm_provider") or "gemini",
            "knowledge_sources_used": ["GINA", "CDC", "user_history"],
        }
        if kwargs.get("return_warnings"):
            return payload, []
        return payload

    return AsyncMock(side_effect=_generate_advice)


def live_api_enabled() -> bool:
    return os.getenv("RUN_LIVE_API_TESTS", "").lower() in ("1", "true", "yes")


def env_key_set(name: str) -> bool:
    value = os.getenv(name, "").strip().strip('"').strip("'")
    if not value:
        return False
    placeholders = ("your_", "change_me", "key_here", "placeholder")
    return not any(p in value.lower() for p in placeholders)


@pytest.fixture
def require_live_api():
    if not live_api_enabled():
        pytest.skip("Live API tests disabled. Run: RUN_LIVE_API_TESTS=1 pytest -m live")
    yield
