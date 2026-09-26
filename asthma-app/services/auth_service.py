"""JWT authentication and password hashing."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET or JWT_SECRET == "change_me_in_production":
    raise RuntimeError("JWT_SECRET must be set to a strong secret (do not use the placeholder).")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: str, extra: Optional[dict[str, Any]] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def safe_decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return decode_access_token(token)
    except JWTError:
        return None
