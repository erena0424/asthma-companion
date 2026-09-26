"""Database connectivity checks for /health."""

from __future__ import annotations

from sqlalchemy import text

from db.database import DATABASE_URL, engine


def check_db_status() -> dict:
    """Return database connectivity status without raising."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "connected": True,
            "url_host": _safe_host(DATABASE_URL),
        }
    except Exception as exc:
        return {
            "status": "error",
            "connected": False,
            "url_host": _safe_host(DATABASE_URL),
            "detail": type(exc).__name__,
        }


def _safe_host(url: str) -> str:
    """Expose host/db name only — never credentials."""
    try:
        # postgresql://user:pass@host:port/dbname
        without_scheme = url.split("://", 1)[-1]
        host_part = without_scheme.split("@", 1)[-1]
        return host_part.split("?")[0]
    except Exception:
        return "unknown"
