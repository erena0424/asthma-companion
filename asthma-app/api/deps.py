"""FastAPI dependencies — database session and authenticated user."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.errors import APIError, api_error
from db.database import get_db
from db.models import User
from services.auth_service import safe_decode_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise api_error(401, "Missing or invalid authentication token", "UNAUTHORIZED")

    payload = safe_decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise api_error(401, "Invalid or expired token", "UNAUTHORIZED")

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        raise api_error(401, "Invalid token subject", "UNAUTHORIZED") from None

    user = db.get(User, user_id)
    if not user:
        raise api_error(404, "User not found", "USER_NOT_FOUND")
    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if credentials is None or not credentials.credentials:
        return None
    payload = safe_decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        return None
    return db.get(User, user_id)
