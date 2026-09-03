"""Admin panel API (Section 8.1).

Level 1 (always on, DB-only): active users, totals, sim counts, job queue, exports.
Level 2 (optional): process CPU/RSS, pool queues, disk usage - JSON only, the panel
draws its own charts; a full Prometheus/Grafana stack is the opt-in Docker profile.
"""

from __future__ import annotations

import datetime as _dt
import os
import shutil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import admin_required, get_db
from app_config import get_settings
from models.entities import AuditLog, Design, ExportLog, MissionJob, SimulationResult, User
from services.executors import pool_stats
from services.infra import job_store

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_required)])
_settings = get_settings()


def _since(minutes: int) -> _dt.datetime:
    return _dt.datetime.now(tz=_dt.UTC) - _dt.timedelta(minutes=minutes)


@router.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    now = _dt.datetime.now(tz=_dt.UTC)
    day_ago = now - _dt.timedelta(days=1)
    week_ago = now - _dt.timedelta(days=7)

    active_5m = db.scalar(select(func.count(User.id)).where(User.last_seen >= _since(5))) or 0
    total_users = db.scalar(select(func.count(User.id))) or 0
    sims_today = db.scalar(select(func.count(SimulationResult.id))
                           .where(SimulationResult.created_at >= day_ago)) or 0
    sims_week = db.scalar(select(func.count(SimulationResult.id))
                          .where(SimulationResult.created_at >= week_ago)) or 0
    total_designs = db.scalar(select(func.count(Design.id))) or 0
    public_designs = db.scalar(select(func.count(Design.id))
                               .where(Design.visibility != "private")) or 0

    job_rows = db.execute(
        select(MissionJob.status, func.count(MissionJob.id)).group_by(MissionJob.status)
    ).all()
    jobs_db = {status: count for status, count in job_rows}

    exports_24h = db.execute(
        select(ExportLog.fmt, func.count(ExportLog.id))
        .where(ExportLog.created_at >= day_ago).group_by(ExportLog.fmt)
    ).all()

    return {
        "active_users_5m": active_5m,
        "total_users": total_users,
        "simulations_today": sims_today,
        "simulations_week": sims_week,
        "total_designs": total_designs,
        "public_designs": public_designs,
        "mission_jobs_db": jobs_db,
        "mission_jobs_memory": job_store.counts(),
        "exports_24h": {fmt: count for fmt, count in exports_24h},
        "generated_at": now.isoformat(),
    }


@router.get("/health")
def health() -> dict:
    """Level 2 - runtime health; panel renders gauges/lines from this JSON."""
    proc = _process_metrics()
    outputs = _settings.outputs_dir
    disk = shutil.disk_usage(outputs if os.path.isdir(outputs) else ".")
    outputs_bytes = _dir_size(outputs)
    disk_pct = disk.used / disk.total * 100.0
    return {
        "process": proc,
        "pools": pool_stats(),
        "disk": {
            "total_gb": round(disk.total / 1e9, 2),
            "used_pct": round(disk_pct, 1),
            "outputs_mb": round(outputs_bytes / 1e6, 2),
        },
        "alert_banner": disk_pct > 90.0 or job_store.counts().get("pending", 0) > 10,
    }


@router.get("/audit")
def audit(limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [{"action": r.action, "target": r.target, "ip": r.ip, "user_id": r.user_id,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/users")
def users(limit: int = 200, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(User).order_by(User.created_at.desc()).limit(limit)).all()
    return [{"id": u.id, "email": u.email, "username": u.username, "role": u.role,
             "is_active": u.is_active, "email_verified": u.email_verified,
             "last_login": u.last_login.isoformat() if u.last_login else None,
             "created_at": u.created_at.isoformat()} for u in rows]


@router.post("/users/{user_id}/suspend")
def suspend(user_id: str, active: bool = False, db: Session = Depends(get_db)) -> dict:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "not found")
    u.is_active = active
    db.add(u)
    db.commit()
    return {"id": u.id, "is_active": u.is_active}


def _process_metrics() -> dict:
    try:
        import resource

        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_mb = rss_kb / 1024 if os.uname().sysname != "Darwin" else rss_kb / 1e6
    except Exception:  # pragma: no cover
        rss_mb = 0.0
    try:
        load1, load5, load15 = os.getloadavg()
    except OSError:  # pragma: no cover - not on all platforms
        load1 = load5 = load15 = 0.0
    return {"rss_mb": round(rss_mb, 1), "load1": load1, "load5": load5, "load15": load15,
            "cpu_count": os.cpu_count()}


def _dir_size(path: str) -> int:
    total = 0
    if not os.path.isdir(path):
        return 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:  # pragma: no cover
                pass
    return total
