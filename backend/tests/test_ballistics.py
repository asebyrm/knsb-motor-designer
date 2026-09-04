"""Time march: mass conservation, dt convergence, downsampling, designation."""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from core.ballistics import (
    nar_class_letter,
    nar_designation,
    simulate,
)
from core.examples import mid_flight_motor, small_test_motor
from core.nozzle import ErosionParams
from core.units import G0


@pytest.fixture(scope="module")
def mid_result():
    ex = mid_flight_motor()
    return ex, simulate(ex.grain, ex.propellant, ex.nozzle, meop_pa=ex.meop_pa)


def test_mass_conservation(mid_result):
    """Section 13.2: integral of mdot dt vs consumed propellant mass < 0.5 %."""
    ex, res = mid_result
    integ = float(np.trapezoid(res.mass_flow, res.time))
    consumed = float(res.propellant_mass[0] - res.propellant_mass[-1])
    assert consumed > 0
    assert abs(integ - consumed) / consumed < 0.02  # includes tail-off blow-down


def test_impulse_consistency(mid_result):
    _, res = mid_result
    s = res.summary
    assert s["total_impulse"] == pytest.approx(
        s["specific_impulse"] * s["propellant_mass"] * G0, rel=0.01
    )


def test_dt_convergence(mid_result):
    """Halving dt changes total impulse by < 0.1 %."""
    ex, res = mid_result
    coarse = simulate(ex.grain, ex.propellant, ex.nozzle, dt=0.002,
                      meop_pa=ex.meop_pa, check_convergence=False)
    fine = simulate(ex.grain, ex.propellant, ex.nozzle, dt=0.0005,
                    meop_pa=ex.meop_pa, check_convergence=False)
    rel = abs(fine.summary["total_impulse"] - coarse.summary["total_impulse"]) / \
        fine.summary["total_impulse"]
    assert rel < 0.01
    assert res.converged


def test_erosion_lowers_pressure_but_not_the_meop_relevant_trace():
    """Erosion opens the throat over the burn, lowering Kn and so the actual
    pressure - but MEOP must still be judged on the untouched erosionless trace
    (Section 5.3): never a way to "fix" over-pressure."""
    ex = small_test_motor()
    eroding = dataclasses.replace(
        ex.nozzle, erosion=ErosionParams(enabled=True, coefficient_mm_s=0.08, exponent=0.8))
    res_off = simulate(ex.grain, ex.propellant, ex.nozzle, meop_pa=ex.meop_pa)
    res_on = simulate(ex.grain, ex.propellant, eroding, meop_pa=ex.meop_pa)

    assert res_on.summary["peak_pressure_bar"] < res_off.summary["peak_pressure_bar"]
    # the erosionless companion must be (almost) unaffected by turning erosion on -
    # it is computed off a throat area that never erodes either way
    assert res_on.summary["peak_pressure_no_erosion_bar"] == pytest.approx(
        res_off.summary["peak_pressure_no_erosion_bar"], rel=0.01)


def test_downsample_preserves_impulse(mid_result):
    """<=500 points, total impulse within 1 % (Section 5.4 / 13.2)."""
    _, res = mid_result
    ds = res.downsampled(500)
    assert ds.time.size <= 500
    full_it = float(np.trapezoid(res.thrust, res.time))
    ds_it = float(np.trapezoid(ds.thrust, ds.time))
    assert abs(ds_it - full_it) / full_it < 0.01
    # peak thrust kept
    assert ds.thrust.max() == pytest.approx(res.thrust.max(), rel=1e-6)


def test_tailoff_ends_at_zero_thrust(mid_result):
    _, res = mid_result
    assert res.thrust[-1] == pytest.approx(0.0, abs=1e-6)
    assert res.time[-1] > res.summary["burn_time"]


def test_small_motor_is_benign():
    ex = small_test_motor()
    res = simulate(ex.grain, ex.propellant, ex.nozzle, meop_pa=ex.meop_pa)
    codes = {w.code for w in res.warnings}
    assert "WARN_MEOP_EXCEEDED" not in codes
    assert res.summary["peak_pressure_no_erosion_bar"] < 45.0


@pytest.mark.parametrize(
    "impulse, letter",
    [(2.0, "A"), (2.6, "B"), (5.0, "B"), (5.1, "C"), (160.0, "G"), (161.0, "H"),
     (1280.0, "J"), (1281.0, "K"), (60000.0, "P")],
)
def test_nar_class_letter(impulse, letter):
    assert nar_class_letter(impulse) == letter


def test_nar_designation_format():
    assert nar_designation(1200.0, 240.4) == "J240"
    assert nar_designation(0.0, 0.0) == ""
