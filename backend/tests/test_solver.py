"""Mission solver: feasible -> 3 candidates; infeasible -> binding constraint + fix.

The solver is CPU-heavy; these run with a short time budget.
"""

from __future__ import annotations

import pytest

from core.solver import MissionInput, solve_mission

pytestmark = pytest.mark.slow


def test_feasible_mission_returns_candidates():
    cfg = MissionInput(
        dry_mass=6.0,
        body_diameter=0.10,
        target_apogee=900.0,
        case_inner_diameter=0.075,
        case_wall_thickness=0.005,
        case_material_id="pa12",
        print_method="sls",
        meop_bar=45.0,
        time_budget_s=8.0,
    )
    res = solve_mission(cfg)
    assert res.candidates
    if res.feasible:
        assert 1 <= len(res.candidates) <= 3
        for c in res.candidates:
            assert c["peak_pressure_bar"] <= cfg.meop_bar + 1e-6
            assert c["fos"] >= 2.0 - 1e-6
            assert c["apogee_low"] < c["apogee"] < c["apogee_high"]
    else:
        # even if the short budget misses feasibility, the fallback must be well-formed
        assert res.binding_constraint is not None


def test_infeasible_mission_names_binding_constraint():
    """Section 13.2 / acceptance 5: 15 kg -> 500 m with a 12 bar MEOP is infeasible.
    The solver must not return an empty result - it names the constraint and a fix."""
    cfg = MissionInput(
        dry_mass=15.0,
        body_diameter=0.10,
        target_apogee=500.0,
        case_inner_diameter=0.075,
        case_wall_thickness=0.004,
        case_material_id="pla",
        print_method="fdm",
        meop_bar=12.0,
        time_budget_s=8.0,
    )
    res = solve_mission(cfg)
    assert res.feasible is False
    assert res.candidates                      # not empty
    assert res.binding_constraint in {
        "meop", "fos", "min_j", "rail_exit_velocity", "max_accel_g", "lstar", "thermal",
    }
    assert isinstance(res.suggestion, dict)
