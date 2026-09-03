"""Propellant model: unit-conversion trap, piecewise law, equilibrium solver."""

from __future__ import annotations

import math

import pytest

from core.propellant import PressureSolveMethod, load_propellant


def test_burn_rate_unit_conversion_at_1_mpa(knsb):
    """Section 13.2: r_b(1 MPa) must equal the table value.

    1 MPa lies in row 2 (0.807-1.50 MPa): a = 8.763, n = -0.314.
    r_b = 8.763 * 1.0**-0.314 = 8.763 mm/s = 0.008763 m/s.
    A Pa/MPa mix-up would be off by ~10**(6*0.314) ~ 74x.
    """
    r_b = knsb.burn_rate(1_000_000.0)  # 1 MPa in Pa
    assert r_b == pytest.approx(0.008763, rel=1e-4)


@pytest.mark.parametrize(
    "p_mpa, row_a, row_n",
    [
        (0.5, 10.71, 0.625),
        (1.0, 8.763, -0.314),
        (2.0, 7.852, -0.013),
        (5.0, 3.907, 0.535),
        (9.0, 9.653, 0.064),
    ],
)
def test_burn_rate_picks_correct_piecewise_row(knsb, p_mpa, row_a, row_n):
    expected = row_a * p_mpa**row_n / 1000.0
    assert knsb.burn_rate(p_mpa * 1e6) == pytest.approx(expected, rel=1e-9)


def test_burn_rate_extrapolation_flagged(knsb):
    assert knsb.is_extrapolated(0.05e6)
    assert knsb.is_extrapolated(12.0e6)
    assert not knsb.is_extrapolated(5.0e6)


def test_a_si_round_trips_with_table_form(knsb):
    row = knsb.burn_rate_ranges[0]
    p_pa = 0.4e6
    assert row.a_si() * p_pa**row.n == pytest.approx(row.burn_rate(p_pa), rel=1e-12)


def test_equilibrium_pressure_in_negative_n_band(knsb):
    """A K_n that balances inside the 0.807-1.50 MPa (negative-n) band.

    Section 13.2: the solver must select the self-consistent root, not an
    out-of-band closed-form artefact.
    """
    # sweep K_n, find one whose solution lands in the negative-n band
    hit = None
    for k_n in [x / 2 for x in range(20, 400)]:
        sol = knsb.solve_equilibrium_pressure(k_n)
        if 0.807e6 <= sol.pressure_pa <= 1.50e6:
            hit = sol
            break
    assert hit is not None
    assert hit.method in (
        PressureSolveMethod.PIECEWISE_CLOSED_FORM,
        PressureSolveMethod.BRENT,
    )
    # residual must actually be ~zero there
    assert knsb._residual(hit.pressure_pa, k_n) == pytest.approx(0.0, abs=hit.pressure_pa * 1e-3)


def test_equilibrium_pressure_monotonic_trend(knsb):
    """Higher Klemmung -> higher chamber pressure (globally, across bands)."""
    p_low = knsb.solve_equilibrium_pressure(150).pressure_pa
    p_high = knsb.solve_equilibrium_pressure(350).pressure_pa
    assert p_high > p_low > 0


def test_c_star_theoretical_close_to_declared(knsb):
    """Sanity: declared c*_ideal should be within a few % of the thermochem value."""
    assert knsb.c_star_theoretical() == pytest.approx(knsb.c_star_ideal, rel=0.15)


def test_loader_by_id_and_by_stem():
    a = load_propellant("knsb")
    b = load_propellant("knsb_fine")
    assert a.id == b.id == "knsb_fine"
    assert math.isclose(a.density, 1841 * 0.95)
