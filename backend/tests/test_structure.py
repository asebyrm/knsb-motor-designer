"""Structure: thin/thick wall hoop stress, FoS gate, fastener sizing."""

from __future__ import annotations

import math

import pytest

from core.assembly import BulkheadSpec, CaseSpec, LinerSpec, MotorAssembly
from core.grains.bates import BatesGrain
from core.materials import PrintMethod, load_case_material, load_liner_material
from core.nozzle import Nozzle
from core.propellant import load_propellant
from core.structure import analyse_structure, analyse_wall, size_fasteners


def test_thin_wall_hoop_stress_matches_formula():
    mat = load_case_material("al6061_t6")
    p, r_i, t = 5.0e6, 0.030, 0.002       # t/r_i = 0.067 -> thin
    res = analyse_wall(p, r_i, t, mat, PrintMethod.MACHINED)
    assert res.model == "thin"
    assert res.sigma_hoop == pytest.approx(p * r_i / t)
    assert res.sigma_axial == pytest.approx(p * r_i / (2 * t))
    assert res.fos == pytest.approx(mat.tensile_strength / res.sigma_vm)


def test_switches_to_thick_wall_model():
    mat = load_case_material("pa12")
    res = analyse_wall(3.0e6, 0.020, 0.004, mat)   # t/r_i = 0.2 -> thick
    assert res.model == "thick"
    r_o = 0.024
    expect_hoop = 3.0e6 * (r_o**2 + 0.020**2) / (r_o**2 - 0.020**2)
    assert res.sigma_hoop == pytest.approx(expect_hoop, rel=1e-9)


def test_print_method_knockdown_applied():
    mat = load_case_material("petg")
    fdm = analyse_wall(2.0e6, 0.030, 0.003, mat, PrintMethod.FDM)
    sls = analyse_wall(2.0e6, 0.030, 0.003, mat, PrintMethod.SLS)
    assert sls.sigma_allow > fdm.sigma_allow      # 0.9 vs 0.5
    assert fdm.sigma_allow == pytest.approx(mat.tensile_strength * 0.5)


def test_low_fos_flags_unsafe_and_blocks():
    prop = load_propellant("knsb")
    cm = load_case_material("pla")
    lm = load_liner_material("kraft_phenolic")
    a = MotorAssembly(
        grain=BatesGrain(0.04, 0.016, 0.08, segment_count=2),
        propellant=prop,
        nozzle=Nozzle(throat_diameter=0.010, expansion_ratio=4.0),
        case=CaseSpec(cm, 0.05, 0.0015),          # very thin PLA wall
        bulkhead=BulkheadSpec(cm, 0.008),
        liner=LinerSpec(lm, 0.003),
    )
    res = analyse_structure(a, 60e5, print_method=PrintMethod.FDM)
    assert res.wall.fos < 2.0
    assert res.is_safe is False
    assert "WARN_LOW_FOS" in {w.code for w in res.warnings}


def test_fastener_count_scales_with_pressure():
    lo = size_fasteners(20e5, 0.03)
    hi = size_fasteners(80e5, 0.03)
    assert hi.min_count >= lo.min_count >= 2
    # cross-check against the closed form
    f_axial = 80e5 * math.pi * 0.03**2
    per_bolt = 200e6 * math.pi * 0.004**2 / 4
    assert hi.min_count == max(2, math.ceil(f_axial * 2.0 / per_bolt))
