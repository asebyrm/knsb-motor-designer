"""Build the :class:`MotorExportData` bundle and drive every writer.

Geometry + the thrust curve are computed once here; the ``.eng`` header mass comes
from ``assembly.bom_total_mass`` so it matches the BOM table byte-for-byte
(acceptance criterion 11). Danger-level warnings lock ``.eng`` / ``.rse`` unless the
caller passes ``accept_risk=True`` (Section 5.6).
"""

from __future__ import annotations

import datetime as _dt

import numpy as np

from core.ballistics import BallisticsResult
from core.export.drawing import render_dimensioned_svg
from core.export.eng import render_eng
from core.export.model import MotorExportData
from core.export.report import render_pdf
from core.export.rse import render_rse
from core.export.tabular import render_csv, render_json, render_nozzle_contour_csv
from services.design_service import MotorContext, build_motor, motor_to_design
from services.simulation_service import analyse, run_ballistics


class ExportLockedError(RuntimeError):
    """Raised when a danger-level design is exported without ``accept_risk=True``."""


def _mass_and_cg_series(
    ctx: MotorContext, ballistics: BallisticsResult
) -> tuple[np.ndarray, np.ndarray]:
    web_total = ctx.grain.web_thickness()
    webs = np.clip(ballistics.web, 0.0, web_total)
    mass = np.array([ctx.assembly.total_mass(float(w)) for w in webs])
    cg = np.array([ctx.assembly.center_of_gravity(float(w)) * 1e3 for w in webs])
    return mass, cg


def build_export_data(
    design: dict,
    *,
    ballistics: BallisticsResult | None = None,
    ctx: MotorContext | None = None,
) -> tuple[MotorExportData, BallisticsResult, MotorContext]:
    ctx = ctx or build_motor(design)
    ballistics = ballistics or run_ballistics(ctx)
    analysis = analyse(ctx, ballistics)
    s = ballistics.summary

    mass_series, cg_series = _mass_and_cg_series(ctx, ballistics)
    total_mass_kg = ctx.assembly.bom_total_mass(0.0)
    prop_mass_kg = float(ballistics.propellant_mass[0] - ballistics.propellant_mass[-1])

    designation = s["designation"]
    prefix = ctx.prefix.strip()
    display = f"{prefix}-{designation}" if prefix else designation

    data = MotorExportData(
        designation=designation,
        display_name=display,
        manufacturer=(prefix or "PARS")[:12],
        designer=ctx.designer,
        date_iso=_dt.date.today().isoformat(),
        propellant_name=ctx.propellant.name_en,
        case_diameter_mm=ctx.assembly.case.outer_diameter * 1e3,
        case_length_mm=ctx.assembly.total_length() * 1e3,
        delay="P",
        propellant_mass_kg=prop_mass_kg,
        total_mass_kg=total_mass_kg,
        time_s=ballistics.time,
        thrust_n=ballistics.thrust,
        total_mass_series_kg=mass_series,
        cg_series_mm=cg_series,
        total_impulse_ns=s["total_impulse"],
        average_thrust_n=s["average_thrust"],
        peak_thrust_n=s["peak_thrust"],
        burn_time_s=s["burn_time"],
        specific_impulse_s=s["specific_impulse"],
        throat_diameter_mm=ctx.nozzle.throat_diameter * 1e3,
        exit_diameter_mm=ctx.nozzle.exit_diameter * 1e3,
        isp_s=s["specific_impulse"],
        is_safe=analysis["is_safe"],
        warnings=analysis["warnings"],
        design_document=motor_to_design(ctx),
    )
    return data, ballistics, ctx


def _guard(data: MotorExportData, accept_risk: bool) -> None:
    if data.blocking_codes() and not accept_risk:
        raise ExportLockedError(
            "design has danger-level warnings; pass accept_risk=True to override: "
            + ", ".join(data.blocking_codes())
        )


def export_eng(design: dict, *, accept_risk: bool = False, **kw) -> str:
    data, *_ = build_export_data(design, **kw)
    _guard(data, accept_risk)
    return render_eng(data)


def export_rse(design: dict, *, accept_risk: bool = False, **kw) -> str:
    data, *_ = build_export_data(design, **kw)
    _guard(data, accept_risk)
    return render_rse(data)


def export_csv(design: dict, **kw) -> str:
    _, ballistics, _ = build_export_data(design, **kw)
    return render_csv(ballistics)


def export_json(design: dict, **kw) -> str:
    data, *_ = build_export_data(design, **kw)
    return render_json(data)


def export_pdf(design: dict, *, locale: str = "en", **kw) -> bytes:
    data, ballistics, ctx = build_export_data(design, **kw)
    rows = _input_rows(ctx)
    return render_pdf(data, ballistics, locale=locale, input_rows=rows)


def export_drawing_svg(design: dict, *, web: float = 0.0, **kw) -> str:
    ctx = kw.get("ctx") or build_motor(design)
    return render_dimensioned_svg(ctx.assembly, web=web)


def export_nozzle_contour_csv(design: dict, **kw) -> str:
    ctx = kw.get("ctx") or build_motor(design)
    return render_nozzle_contour_csv(ctx.nozzle)


def _input_rows(ctx: MotorContext) -> list[tuple[str, str]]:
    g = ctx.grain.to_dict()
    return [
        ("propellant", ctx.propellant.name_en),
        ("grain type", g.get("type", "")),
        ("grain outer diameter", f"{g.get('outer_diameter', 0) * 1e3:.1f} mm"),
        ("grain core diameter", f"{g.get('core_diameter', 0) * 1e3:.1f} mm"),
        ("segment length", f"{g.get('segment_length', g.get('length', 0)) * 1e3:.1f} mm"),
        ("segment count", str(g.get("segment_count", 1))),
        ("throat diameter", f"{ctx.nozzle.throat_diameter * 1e3:.2f} mm"),
        ("expansion ratio", f"{ctx.nozzle.expansion_ratio:.2f}"),
        ("case material", ctx.assembly.case.material.id),
        ("case inner diameter", f"{ctx.assembly.case.inner_diameter * 1e3:.1f} mm"),
        ("case wall thickness", f"{ctx.assembly.case.wall_thickness * 1e3:.2f} mm"),
        ("liner", ctx.assembly.liner.material.id if ctx.assembly.liner else "NONE"),
        ("MEOP", f"{ctx.meop_pa / 1e5:.1f} bar" if ctx.meop_pa else "n/a"),
    ]


ALL_FORMATS = {
    "eng": ("text/plain", export_eng),
    "rse": ("application/xml", export_rse),
    "csv": ("text/csv", export_csv),
    "json": ("application/json", export_json),
    "svg": ("image/svg+xml", export_drawing_svg),
    "nozzle_csv": ("text/csv", export_nozzle_contour_csv),
}
