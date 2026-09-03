"""Mission-solver orchestration: submit a job, poll it, never block the event loop.

A request returns a ``job_id`` immediately; the client polls ``GET /api/jobs/{id}``.
The heavy ``solve_mission`` runs in the ProcessPoolExecutor (Section 12.2).
"""

from __future__ import annotations

import asyncio
import logging

from app_config import get_settings
from services.executors import solve_mission_async
from services.infra import JobStore, job_store

log = logging.getLogger("mission")

_ALLOWED_KEYS = {
    "dry_mass", "body_diameter", "target_apogee", "drag_coefficient", "rail_length",
    "launch_altitude", "max_accel_g", "min_rail_exit_velocity", "case_inner_diameter",
    "case_wall_thickness", "case_material_id", "print_method", "liner_material_id",
    "liner_thickness", "bulkhead_thickness", "propellant_id", "meop_bar",
    "ambient_pressure", "time_budget_s",
}


def sanitise_payload(raw: dict) -> dict:
    """Keep only known MissionInput fields; clamp the time budget to the configured max."""
    payload = {k: v for k, v in raw.items() if k in _ALLOWED_KEYS}
    s = get_settings()
    payload["time_budget_s"] = min(float(payload.get("time_budget_s", 30.0)),
                                   float(s.mission_timeout_s) - 5.0)
    return payload


async def _run(job_id: str, payload: dict, store: JobStore) -> None:
    store.mark_running(job_id)
    try:
        s = get_settings()
        result = await solve_mission_async(payload, timeout=s.mission_timeout_s)
        store.mark_done(job_id, result)
    except TimeoutError:
        store.mark_failed(job_id, "solver exceeded the time limit")
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("mission job %s failed", job_id)
        store.mark_failed(job_id, f"{type(exc).__name__}: {exc}")


def submit_mission(raw_payload: dict, *, store: JobStore | None = None) -> str:
    """Create a job and schedule it. Returns the job id at once."""
    store = store or job_store
    payload = sanitise_payload(raw_payload)
    job_id = store.create(payload)
    asyncio.get_running_loop().create_task(_run(job_id, payload, store))
    return job_id


def job_status(job_id: str, *, store: JobStore | None = None) -> dict | None:
    store = store or job_store
    job = store.get(job_id)
    if job is None:
        return None
    return {
        "job_id": job.id,
        "status": job.status,
        "result": job.result,
        "error": job.error,
    }
