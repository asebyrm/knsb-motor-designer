"""Registration, login, refresh-token rotation, logout (Section 8)."""

from __future__ import annotations

import datetime as _dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from api.deps import (
    client_ip,
    get_current_user,
    get_db,
    get_user_from_refresh_cookie,
    rate_limit,
)
from api.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app_config import get_settings
from models.entities import AuditLog, Design, User
from services.auth_service import (
    PasswordPolicyError,
    create_access_token,
    create_refresh_token,
    hash_password,
    needs_rehash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
_settings = get_settings()


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, username=u.username, role=u.role,
                   locale=u.locale, email_verified=u.email_verified)


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "refresh_token", token, httponly=True, secure=_settings.cookie_secure,
        samesite="lax", max_age=_settings.refresh_token_days * 86400,
        domain=_settings.cookie_domain, path="/api/auth",
    )


def _audit(db: Session, user_id: str | None, action: str, ip: str, target: str = "") -> None:
    db.add(AuditLog(user_id=user_id, action=action, ip=ip, target=target))
    db.commit()


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, request: Request, response: Response,
             db: Session = Depends(get_db)):
    exists = db.scalar(select(User).where(
        or_(User.email == req.email.lower(), User.username == req.username)))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "email or username already registered")
    try:
        pw_hash = hash_password(req.password)
    except PasswordPolicyError as exc:
        raise HTTPException(422, str(exc)) from exc

    is_first = db.scalar(select(User).limit(1)) is None
    user = User(
        email=req.email.lower(), username=req.username, password_hash=pw_hash,
        locale=req.locale, role="admin" if is_first else "user",
        email_verified=not _settings.email_verification_enabled,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _audit(db, user.id, "register", client_ip(request))

    jti = uuid.uuid4().hex
    _set_refresh_cookie(response, create_refresh_token(user.id, jti))
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        expires_in=_settings.access_token_minutes * 60,
        user=_user_out(user),
    )


@router.post("/login", response_model=TokenResponse,
             dependencies=[Depends(rate_limit("login", _settings.rate_limit_login_per_min))])
def login(req: LoginRequest, request: Request, response: Response,
          db: Session = Depends(get_db)):
    ident = req.email_or_username.strip().lower()
    user = db.scalar(select(User).where(
        or_(User.email == ident, User.username == req.email_or_username.strip())))
    if not user or not verify_password(req.password, user.password_hash):
        _audit(db, user.id if user else None, "login_failed", client_ip(request))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account is suspended")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(req.password)
    user.last_login = _dt.datetime.now(tz=_dt.UTC)
    user.last_seen = user.last_login
    db.add(user)
    db.commit()
    _audit(db, user.id, "login", client_ip(request))

    jti = uuid.uuid4().hex
    _set_refresh_cookie(response, create_refresh_token(user.id, jti))
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        expires_in=_settings.access_token_minutes * 60,
        user=_user_out(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(response: Response, pair=Depends(get_user_from_refresh_cookie),
            db: Session = Depends(get_db)):
    user, _payload = pair
    jti = uuid.uuid4().hex  # rotate
    _set_refresh_cookie(response, create_refresh_token(user.id, jti))
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        expires_in=_settings.access_token_minutes * 60,
        user=_user_out(user),
    )


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie("refresh_token", path="/api/auth", domain=_settings.cookie_domain)
    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.post("/adopt-design", response_model=dict)
def adopt_design(payload: dict, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """Move an anonymous (localStorage) design onto the account after login (Section 8)."""
    cfg = payload.get("config_json") or payload
    d = Design(owner_id=user.id, name=payload.get("name", "Imported design"),
               description=payload.get("description", ""), config_json=cfg,
               visibility="private", schema_version=int(cfg.get("schema_version", 1)))
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id, "name": d.name}
