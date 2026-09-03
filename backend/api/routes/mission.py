"""Inverse design: submit a solver job, poll it (Sections 6, 12.2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_db, get_optional_user, rate_limit, touch_last_seen
from api.schemas import JobOut, MissionRequest
from app_config import get_settings
from services.mission_service import job_status, submit_mission

router = APIRouter(tags=["mission"])
_settings = get_settings()


@router.post("/mission", response_model=JobOut,
             dependencies=[Depends(rate_limit("mission", _settings.rate_limit_mission_per_min))])
async def start_mission(req: MissionRequest, db=Depends(get_db), user=Depends(get_optional_user)):
    touch_last_seen(user, db)
    job_id = submit_mission(req.model_dump())
    return JobOut(job_id=job_id, status="pending")


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: str):
    status = job_status(job_id)
    if status is None:
        raise HTTPException(404, "job not found")
    return JobOut(**status)
