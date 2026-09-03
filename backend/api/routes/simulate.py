"""Forward simulation + grain-slider snapshot (Sections 5, 10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_db, get_optional_user, rate_limit, touch_last_seen
from api.schemas import SimulateRequest
from app_config import get_settings
from services.executors import run_simulation_async

router = APIRouter(prefix="/simulate", tags=["simulation"])
_settings = get_settings()


@router.post("", dependencies=[Depends(rate_limit("sim", _settings.rate_limit_sim_per_min))])
async def simulate(req: SimulateRequest, db=Depends(get_db), user=Depends(get_optional_user)):
    touch_last_seen(user, db)
    try:
        return await run_simulation_async(
            req.design, downsample=req.downsample,
            timeout=_settings.simulation_timeout_s,
        )
    except TimeoutError:
        raise HTTPException(408, "simulation exceeded the time limit") from None
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, f"invalid design: {exc}") from exc
