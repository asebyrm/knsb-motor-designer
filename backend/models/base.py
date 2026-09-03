"""Declarative base + engine/session factory (pool sized from env, Section 12.2)."""

from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy import DateTime, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from app_config import get_settings


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return uuid.uuid4().hex


class UUIDMixin:
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)


class TimestampMixin:
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def make_engine(url: str | None = None):
    s = get_settings()
    url = url or s.database_url
    kwargs: dict = {"future": True, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        # allow use across threads (thread pool + test client)
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url or "mode=memory" in url:
            # one shared connection so every session sees the same in-memory DB
            kwargs["poolclass"] = StaticPool
    else:
        kwargs["pool_size"] = s.db_pool_size
        kwargs["max_overflow"] = s.db_max_overflow
    return create_engine(url, **kwargs)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def create_all() -> None:
    """Dev/test convenience; production uses Alembic migrations."""
    Base.metadata.create_all(bind=engine)
