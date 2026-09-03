"""Password hashing (Argon2id) and JWT access/refresh tokens (Section 8)."""

from __future__ import annotations

import datetime as _dt

import jwt
from argon2 import PasswordHasher
from argon2 import exceptions as argon2_exc

from app_config import get_settings

_ph = PasswordHasher()  # argon2-cffi defaults to Argon2id

# a tiny embedded common-password list; extend via COMMON_PASSWORD_FILE if desired
_COMMON = {
    "password", "password1", "123456", "12345678", "123456789", "qwerty",
    "111111", "1234567890", "letmein", "iloveyou", "admin123", "welcome1",
    "rocketman", "aaaaaaaaaa", "password123", "knsbknsbkn",
}

MIN_PASSWORD_LENGTH = 10


class PasswordPolicyError(ValueError):
    pass


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    if password.lower() in _COMMON:
        raise PasswordPolicyError("password is too common")


def hash_password(password: str) -> str:
    validate_password(password)
    return _ph.hash(password)


_VERIFY_ERRORS = (
    argon2_exc.VerifyMismatchError,
    argon2_exc.InvalidHashError,
    argon2_exc.VerificationError,
)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _ph.verify(password_hash, password)
        return True
    except _VERIFY_ERRORS:
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _ph.check_needs_rehash(password_hash)
    except argon2_exc.InvalidHashError:
        return True


# --- JWT ----------------------------------------------------------------

_ALGO = "HS256"


def _now() -> _dt.datetime:
    return _dt.datetime.now(tz=_dt.UTC)


def _encode(claims: dict, expires: _dt.timedelta, token_type: str) -> str:
    s = get_settings()
    payload = {**claims, "type": token_type, "iat": _now(), "exp": _now() + expires}
    return jwt.encode(payload, s.resolved_secret_key(), algorithm=_ALGO)


def create_access_token(user_id: str, role: str) -> str:
    s = get_settings()
    return _encode({"sub": user_id, "role": role},
                   _dt.timedelta(minutes=s.access_token_minutes), "access")


def create_refresh_token(user_id: str, jti: str) -> str:
    s = get_settings()
    return _encode({"sub": user_id, "jti": jti},
                   _dt.timedelta(days=s.refresh_token_days), "refresh")


def decode_token(token: str, expected_type: str | None = None) -> dict:
    s = get_settings()
    payload = jwt.decode(token, s.resolved_secret_key(), algorithms=[_ALGO])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected {expected_type} token")
    return payload
