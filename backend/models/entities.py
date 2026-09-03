"""Domain tables (Section 8).

User, Design, SimulationResult, AuditLog per the spec, plus MissionJob (Section
12.2 job polling) and ExportLog (Section 8.1 admin stats).
"""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)  # user|admin
    locale: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[_dt.datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[_dt.datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    designs: Mapped[list[Design]] = relationship(back_populates="owner",
                                                   cascade="all, delete-orphan")


class Design(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "designs"

    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                                 index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    visibility: Mapped[str] = mapped_column(String(12), default="private", nullable=False)
    slug: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    fork_of_id: Mapped[str | None] = mapped_column(ForeignKey("designs.id", ondelete="SET NULL"))

    owner: Mapped[User | None] = relationship(back_populates="designs")
    simulations: Mapped[list[SimulationResult]] = relationship(
        back_populates="design", cascade="all, delete-orphan")


class SimulationResult(UUIDMixin, Base):
    __tablename__ = "simulation_results"

    design_id: Mapped[str] = mapped_column(ForeignKey("designs.id", ondelete="CASCADE"),
                                           index=True)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    timeseries_blob: Mapped[str] = mapped_column(Text, default="")
    engine_version: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)

    design: Mapped[Design] = relationship(back_populates="simulations")


class AuditLog(UUIDMixin, Base):
    __tablename__ = "audit_logs"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"),
                                                index=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    target: Mapped[str] = mapped_column(String(120), default="")
    ip: Mapped[str] = mapped_column(String(45), default="")
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)


class MissionJob(UUIDMixin, Base):
    __tablename__ = "mission_jobs"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True,
                                        nullable=False)  # pending|running|done|failed
    request_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    finished_at: Mapped[_dt.datetime | None] = mapped_column(DateTime(timezone=True))


class ExportLog(UUIDMixin, Base):
    __tablename__ = "export_logs"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    fmt: Mapped[str] = mapped_column(String(16), nullable=False)
    design_id: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)


Index("ix_designs_visibility_updated", Design.visibility, Design.updated_at)
