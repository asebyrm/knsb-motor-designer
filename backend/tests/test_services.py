"""Service layer: design round-trip, forward simulation shape, safety verdict."""

from __future__ import annotations

import pytest

from services.design_service import build_motor, motor_to_design
from services.simulation_service import run_simulation

DESIGN = {
    "name": "svc", "prefix": "PARS", "designer": "asb",
    "propellant": {"id": "knsb", "c_star_efficiency": 0.93},
    "grain": {"type": "bates", "outer_diameter": 0.045, "core_diameter": 0.018,
              "segment_length": 0.08, "segment_count": 3, "segment_spacing": 0.003},
    "nozzle": {"throat_diameter": 0.0115, "expansion_ratio": 5.0, "throat_length": 0.006},
    "case": {"material_id": "pa12", "inner_diameter": 0.052, "wall_thickness": 0.005,
             "print_method": "sls"},
    "liner": {"material_id": "kraft_phenolic", "thickness": 0.003},
    "bulkhead": {"material_id": "pa12", "thickness": 0.010},
    "meop_bar": 45,
}


def test_design_document_round_trips():
    ctx = build_motor(DESIGN)
    again = motor_to_design(ctx)
    ctx2 = build_motor(again)
    assert ctx2.grain.to_dict() == ctx.grain.to_dict()
    assert ctx2.propellant.c_star_efficiency == pytest.approx(0.93)
    assert ctx2.nozzle.throat_diameter == pytest.approx(ctx.nozzle.throat_diameter)


def test_run_simulation_shape():
    out = run_simulation(DESIGN)
    for key in ("summary", "structure", "thermal", "assembly", "warnings",
                "is_safe", "export_locked", "series", "grain_cross_section_svg"):
        assert key in out
    s = out["summary"]
    for key in ("total_impulse", "average_thrust", "peak_thrust", "burn_time",
                "specific_impulse", "designation", "fos", "motor_mass_kg",
                "total_length_mm", "cg_initial_mm", "mass_ratio"):
        assert key in s
    assert len(out["series"]["time_s"]) <= 500
    assert out["series"]["thrust_n"][-1] == pytest.approx(0.0, abs=1e-6)


def test_safety_verdict_consistent():
    out = run_simulation(DESIGN)
    assert out["is_safe"] == (not out["export_locked"])
    # a design with a wafer-thin PLA wall must be locked
    bad = {**DESIGN, "case": {**DESIGN["case"], "material_id": "pla",
                              "wall_thickness": 0.0012, "print_method": "fdm"},
           "meop_bar": 20}
    out_bad = run_simulation(bad)
    assert out_bad["export_locked"] is True
    assert any(w["code"] == "WARN_LOW_FOS" for w in out_bad["warnings"])


def test_grain_slider_snapshot():
    from services.design_service import build_motor
    from services.simulation_service import run_ballistics, web_to_time

    ctx = build_motor(DESIGN)
    b = run_ballistics(ctx)
    mid = web_to_time(b, 0.5)
    assert mid["web_mm"] > 0
    assert mid["chamber_pressure_bar"] > 0
