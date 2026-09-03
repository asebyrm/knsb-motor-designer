"""Thermal: mandatory liner, semi-infinite soak estimate, burn-through."""

from __future__ import annotations

import pytest

from core.assembly import BulkheadSpec, CaseSpec, LinerSpec, MotorAssembly
from core.grains.bates import BatesGrain
from core.materials import load_case_material, load_liner_material
from core.nozzle import Nozzle
from core.propellant import load_propellant
from core.thermal import analyse_thermal, semi_infinite_surface_temperature


def _assembly(liner_thickness: float | None):
    prop = load_propellant("knsb")
    cm = load_case_material("pa12")
    liner = None
    if liner_thickness is not None:
        liner = LinerSpec(load_liner_material("kraft_phenolic"), liner_thickness)
    return MotorAssembly(
        grain=BatesGrain(0.04, 0.016, 0.09, segment_count=2),
        propellant=prop,
        nozzle=Nozzle(throat_diameter=0.011, expansion_ratio=4.0),
        case=CaseSpec(cm, 0.05, 0.004),
        bulkhead=BulkheadSpec(cm, 0.010),
        liner=liner,
    )


def test_no_liner_is_unsafe():
    res = analyse_thermal(_assembly(None), 1600.0, 2.0)
    assert res.liner_present is False
    assert res.is_safe is False
    assert "WARN_NO_LINER" in {w.code for w in res.warnings}


def test_erfc_solution_limits():
    # x = 0 -> surface sees full flame temperature
    at_surface = semi_infinite_surface_temperature(0.0, 3.0, 1e-7, 1600.0, 293.0)
    assert at_surface == pytest.approx(1600.0)
    # deep / short time -> stays at initial
    deep = semi_infinite_surface_temperature(0.05, 0.1, 1e-7, 1600.0, 293.0)
    assert deep == pytest.approx(293.0, abs=1.0)


def test_thin_liner_burns_through_and_flags():
    res = analyse_thermal(_assembly(0.0005), 1600.0, 6.0)   # 0.5 mm, 6 s burn
    codes = {w.code for w in res.warnings}
    assert res.ablation_depth > 0.0005
    assert "WARN_THERMAL_LIMIT" in codes
    assert res.is_safe is False


def test_reasonable_liner_ok_for_short_burn():
    res = analyse_thermal(_assembly(0.003), 1600.0, 2.0)
    assert res.is_safe is True
    assert res.case_inner_surface_temp < res.case_max_service_temp


def test_recommended_thickness_grows_for_long_burns():
    a = _assembly(0.003)
    short = analyse_thermal(a, 1600.0, 2.0).recommended_liner_thickness
    long = analyse_thermal(a, 1600.0, 5.0).recommended_liner_thickness
    assert long > short
