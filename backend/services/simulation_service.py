"""Run the full forward analysis for a design document and shape it for a client.

One call gives ballistics + structure + thermal + assembly metrics + a downsampled
time series + a merged, de-duplicated warning list with a single ``is_safe`` /
``export_locked`` verdict (Sections 5.8, 5.6, 5.7).
"""

from __future__ import annotations

import numpy as np

from core.ballistics import BallisticsResult, simulate
from core.structure import analyse_structure
from core.thermal import analyse_thermal
from core.warnings import Level, dedupe, has_blocking
from services.design_service import MotorContext, build_motor


def _series_dict(res: BallisticsResult) -> dict:
    return {
        "time_s": res.time.tolist(),
        "chamber_pressure_bar": (res.chamber_pressure / 1e5).tolist(),
        "chamber_pressure_no_erosion_bar": (res.chamber_pressure_no_erosion / 1e5).tolist(),
        "thrust_n": res.thrust.tolist(),
        "burn_rate_mm_s": (res.burn_rate * 1e3).tolist(),
        "kn": res.kn.tolist(),
        "burn_area_mm2": (res.burn_area * 1e6).tolist(),
        "throat_area_mm2": (res.throat_area * 1e6).tolist(),
        "port_area_mm2": (res.port_area * 1e6).tolist(),
        "mass_flow_kg_s": res.mass_flow.tolist(),
        "cumulative_impulse_ns": res.cumulative_impulse.tolist(),
        "propellant_mass_g": (res.propellant_mass * 1e3).tolist(),
        "web_mm": (res.web * 1e3).tolist(),
    }


def run_ballistics(ctx: MotorContext) -> BallisticsResult:
    """The raw ballistics result at full resolution (used by export + report)."""
    chamber_volume = ctx.assembly.free_volume(0.0) + ctx.grain.initial_volume()
    return simulate(
        ctx.grain, ctx.propellant, ctx.nozzle,
        ambient_pressure=ctx.ambient_pressure,
        chamber_volume=chamber_volume,
        meop_pa=ctx.meop_pa,
    )


def analyse(ctx: MotorContext, ballistics: BallisticsResult) -> dict:
    """Structure + thermal + assembly + merged verdict for a computed ballistics run."""
    s = ballistics.summary
    meop_pa = ctx.meop_pa or s["peak_pressure_no_erosion_bar"] * 1e5

    structure = analyse_structure(
        ctx.assembly, s["peak_pressure_no_erosion_bar"] * 1e5,
        print_method=ctx.print_method,
        bolt_diameter=ctx.bolt_diameter,
        bolt_shear_strength=ctx.bolt_shear_strength,
    )
    thermal = analyse_thermal(ctx.assembly, ctx.propellant.flame_temperature, s["burn_time"])

    warnings = dedupe(
        list(ballistics.warnings)
        + ctx.assembly.validate_fit()
        + structure.warnings
        + thermal.warnings
        + ctx.grain.validate()
    )
    is_safe = structure.is_safe and thermal.is_safe and not has_blocking(warnings)

    web_bt = ctx.grain.web_thickness()
    return {
        "summary": {
            **s,
            "motor_mass_kg": ctx.assembly.total_mass(0.0),
            "inert_mass_kg": ctx.assembly.inert_mass(),
            "mass_ratio": (ctx.assembly.total_mass(0.0) / max(ctx.assembly.inert_mass(), 1e-9)),
            "total_length_mm": ctx.assembly.total_length() * 1e3,
            "cg_initial_mm": ctx.assembly.center_of_gravity(0.0) * 1e3,
            "cg_burnout_mm": ctx.assembly.center_of_gravity(web_bt) * 1e3,
            "meop_bar": meop_pa / 1e5,
            "fos": structure.wall.fos,
        },
        "structure": structure.to_dict(),
        "thermal": thermal.to_dict(),
        "assembly": {
            "parts": [
                {
                    "name": p.name, "material_id": p.material_id,
                    "x_start_mm": p.x_start * 1e3, "x_end_mm": p.x_end * 1e3,
                    "outer_diameter_mm": p.outer_diameter * 1e3,
                    "inner_diameter_mm": p.inner_diameter * 1e3,
                    "mass_g": p.mass * 1e3,
                }
                for p in ctx.assembly.compute_layout(0.0)
            ],
            "bom": ctx.assembly.bill_of_materials(0.0),
            "fit_warnings": [w.to_dict() for w in ctx.assembly.validate_fit()],
            "free_volume_cm3": ctx.assembly.free_volume(0.0) * 1e6,
            "lstar_mm": ctx.assembly.characteristic_length() * 1e3,
        },
        "warnings": [w.to_dict() for w in warnings],
        "is_safe": is_safe,
        "export_locked": has_blocking(warnings) or not is_safe,
        "max_warning_level": max(
            (w.level for w in warnings), key=lambda lv: {Level.INFO: 0, Level.WARNING: 1,
                                                        Level.DANGER: 2}[lv],
            default=Level.INFO,
        ).value,
    }


def run_simulation(design: dict, *, downsample: int = 500) -> dict:
    """Full forward result for the API / CLI: analysis + a downsampled series."""
    ctx = build_motor(design)
    ballistics = run_ballistics(ctx)
    out = analyse(ctx, ballistics)
    ds = ballistics.downsampled(downsample)
    out["series"] = _series_dict(ds)
    out["grain_cross_section_svg"] = ctx.grain.cross_section_svg(0.0)
    out["engine_version"] = "0.3.0"
    return out


def web_to_time(ballistics: BallisticsResult, web_fraction: float) -> dict:
    """Snapshot at a given fraction of the total web (for the grain slider)."""
    frac = min(max(web_fraction, 0.0), 1.0)
    idx = int(np.searchsorted(ballistics.web, frac * ballistics.web.max()))
    idx = min(idx, ballistics.web.size - 1)
    return {
        "time_s": float(ballistics.time[idx]),
        "kn": float(ballistics.kn[idx]),
        "chamber_pressure_bar": float(ballistics.chamber_pressure[idx] / 1e5),
        "thrust_n": float(ballistics.thrust[idx]),
        "web_mm": float(ballistics.web[idx] * 1e3),
    }
