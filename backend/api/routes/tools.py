"""Small helper endpoints for the UI action buttons (Section 9.3)."""

from __future__ import annotations

from fastapi import APIRouter

from core.grains.bates import suggest_neutral_segment_length
from services.design_service import build_motor
from services.simulation_service import run_ballistics

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/neutral-length")
def neutral_length(outer_diameter: float, core_diameter: float) -> dict:
    """Segment length [m] that makes a BATES grain burn neutrally (Section 5.2)."""
    return {"segment_length": suggest_neutral_segment_length(outer_diameter, core_diameter)}


@router.post("/optimum-expansion")
def optimum_expansion(design: dict) -> dict:
    """Expansion ratio that fully expands to ambient at this motor's peak pressure."""
    ctx = build_motor(design)
    ball = run_ballistics(ctx)
    p_c = ball.summary["peak_pressure_no_erosion_bar"] * 1e5
    eps = ctx.nozzle.optimum_expansion_ratio(p_c, ctx.ambient_pressure, ctx.propellant.gamma)
    return {"expansion_ratio": round(eps, 3)}
