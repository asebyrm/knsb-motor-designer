"""Section 13.1 regression test - MUST pass.

The reference motor is an internal-burning tube with erosion OFF. Its expected
behaviour is deliberately *unsafe*: a progressive tube climbs from the 10 bar design
point to ~22 bar and exceeds MEOP. The point of the test is that the code detects
this (``WARN_MEOP_EXCEEDED``); do NOT "fix" the motor, relax the MEOP check or turn
on erosion (Section 5.3 / 13.1).
"""

from __future__ import annotations

import pytest

from core.ballistics import simulate
from core.examples import reference_case
from core.warnings import Level


@pytest.fixture(scope="module")
def ref_result():
    ex = reference_case()
    return ex, simulate(ex.grain, ex.propellant, ex.nozzle,
                        ambient_pressure=ex.ambient_pressure, meop_pa=ex.meop_pa)


def test_geometry_inputs_match_report(ref_result):
    ex, _ = ref_result
    a_t = ex.nozzle.throat_area
    r_t0_mm = ex.nozzle.throat_diameter / 2.0 * 1000.0
    r_p0_mm = ex.grain.d / 2.0 * 1000.0
    l_mm = ex.grain.l * 1000.0

    assert a_t * 1e6 == pytest.approx(235.0, rel=0.02)      # mm^2
    assert r_t0_mm == pytest.approx(8.65, rel=0.02)
    assert r_p0_mm == pytest.approx(17.3, rel=0.02)
    assert l_mm == pytest.approx(147.0, rel=0.02)


def test_initial_pressure_near_design_point(ref_result):
    _, res = ref_result
    # first steady sample after the ignition transient

    steady = res.chamber_pressure_no_erosion[res.time >= 0.06]
    assert steady.size
    assert steady[0] / 1e5 == pytest.approx(10.0, rel=0.10)


def test_peak_pressure_about_22_bar(ref_result):
    _, res = ref_result
    assert res.summary["peak_pressure_no_erosion_bar"] == pytest.approx(22.0, rel=0.02)


def test_meop_exceeded_warning_is_raised(ref_result):
    _, res = ref_result
    codes = {w.code for w in res.warnings}
    assert "WARN_MEOP_EXCEEDED" in codes
    meop_w = next(w for w in res.warnings if w.code == "WARN_MEOP_EXCEEDED")
    assert meop_w.level == Level.DANGER


def test_progressive_geometry_warning_is_raised(ref_result):
    _, res = ref_result
    assert "WARN_PROGRESSIVE_GEOMETRY" in {w.code for w in res.warnings}


def test_specific_impulse_matches_report(ref_result):
    _, res = ref_result
    # report Isp = 118.4 s; allow the 2 % band the spec grants
    assert res.summary["specific_impulse"] == pytest.approx(118.4, rel=0.03)


def test_impulse_consistency(ref_result):
    """Section 13.2: I_t == Isp * m_p * g0 within 1 %."""
    _, res = ref_result
    s = res.summary
    from core.units import G0

    assert s["total_impulse"] == pytest.approx(
        s["specific_impulse"] * s["propellant_mass"] * G0, rel=0.01
    )


def test_erosion_stays_off(ref_result):
    ex, res = ref_result
    assert ex.nozzle.erosion.enabled is False
    # erosionless and eroded peak must be identical here
    assert res.summary["peak_pressure_bar"] == pytest.approx(
        res.summary["peak_pressure_no_erosion_bar"], rel=1e-6
    )


def test_dt_convergence_reached(ref_result):
    _, res = ref_result
    assert res.converged
    assert res.dt_used <= 0.001
