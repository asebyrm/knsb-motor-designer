"""Shared FastAPI dependencies: DB session, auth, rate limiting."""

from __future__ import annotations

from collections.abc import Iterator

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app_config import get_settings
from models.base import SessionLocal
from models.entities import User
from services.auth_service import decode_token
from services.infra import rate_limiter


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Current user or ``None`` - anonymous access is allowed everywhere (Section 8)."""
    token = _bearer(request)
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type="access")
    except jwt.PyJWTError:
        return None
    user = db.get(User, payload.get("sub"))
    if user and user.is_active:
        return user
    return None


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    return user


def admin_required(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    return user


def rate_limit(bucket: str, per_minute: int):
    """Dependency factory: 429 when the IP exceeds ``per_minute`` for ``bucket``.

    ``per_minute`` here is the fallback; the live value from settings wins so tests
    (and ops) can retune limits without restarting import-time state.
    """
    _live = {
        "login": "rate_limit_login_per_min",
        "sim": "rate_limit_sim_per_min",
        "mission": "rate_limit_mission_per_min",
    }

    def _dep(request: Request) -> None:
        limit = getattr(get_settings(), _live.get(bucket, ""), per_minute) or per_minute
        key = f"{bucket}:{client_ip(request)}"
        if not rate_limiter.allow(key, limit):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                f"rate limit exceeded for {bucket}")

    return _dep


def get_user_from_refresh_cookie(
    request: Request, db: Session = Depends(get_db)
) -> tuple[User, dict]:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no refresh token")
    try:
        payload = decode_token(token, expected_type="refresh")
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token") from exc
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return user, payload


def touch_last_seen(user: User | None, db: Session) -> None:
    if user is None:
        return
    import datetime as _dt

    user.last_seen = _dt.datetime.now(tz=_dt.UTC)
    db.add(user)
    db.commit()


__all__ = [
    "get_db", "client_ip", "get_optional_user", "get_current_user", "admin_required",
    "rate_limit", "get_user_from_refresh_cookie", "touch_last_seen", "select",
]
