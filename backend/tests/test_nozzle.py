"""Nozzle: thrust coefficient, expansion solving, separation, erosion."""

from __future__ import annotations

import math

import pytest

from core.nozzle import ErosionParams, Nozzle
from core.units import P_ATM_SEA_LEVEL

GAMMA = 1.1251


def test_exit_mach_grows_with_expansion_ratio():
    n1 = Nozzle(throat_diameter=0.02, expansion_ratio=2.0)
    n2 = Nozzle(throat_diameter=0.02, expansion_ratio=8.0)
    assert 1.0 < n1.exit_mach(GAMMA) < n2.exit_mach(GAMMA)


def test_cf_at_eps_one_is_near_unity():
    """At eps = 1 the throat is the exit: Cf is dominated by the pressure term and
    stays close to 1 for a sea-level motor (well below the ideal vacuum value)."""
    n = Nozzle(throat_diameter=0.02, expansion_ratio=1.0 + 1e-6, efficiency=1.0,
               divergence_half_angle_deg=0.0)
    cf = n.thrust_coefficient(2.0e6, P_ATM_SEA_LEVEL, GAMMA)
    assert 0.6 < cf < 1.5


def test_cf_increases_with_chamber_pressure():
    n = Nozzle(throat_diameter=0.02, expansion_ratio=4.0)
    lo = n.thrust_coefficient(1.0e6, P_ATM_SEA_LEVEL, GAMMA)
    hi = n.thrust_coefficient(5.0e6, P_ATM_SEA_LEVEL, GAMMA)
    assert hi > lo


def test_divergence_loss_15deg():
    n = Nozzle(throat_diameter=0.02, divergence_half_angle_deg=15.0)
    assert n.divergence_loss == pytest.approx((1 + math.cos(math.radians(15))) / 2)
    assert n.divergence_loss == pytest.approx(0.9830, abs=1e-3)


def test_optimum_expansion_ratio_makes_pe_equal_pa():
    n = Nozzle(throat_diameter=0.02, expansion_ratio=4.0)
    eps_opt = n.optimum_expansion_ratio(3.0e6, P_ATM_SEA_LEVEL, GAMMA)
    n.expansion_ratio = eps_opt
    assert n.exit_pressure(3.0e6, GAMMA) == pytest.approx(P_ATM_SEA_LEVEL, rel=0.02)


def test_flow_separation_flagged_when_overexpanded():
    """Big nozzle, low chamber pressure -> p_e < 0.4 p_a -> Summerfield warning."""
    n = Nozzle(throat_diameter=0.02, expansion_ratio=25.0)
    w = n.check_separation(1.0e6, P_ATM_SEA_LEVEL, GAMMA)
    assert w is not None and w.code == "WARN_FLOW_SEPARATION"
    # a sensible sea-level nozzle should not separate
    ok = Nozzle(throat_diameter=0.02, expansion_ratio=3.0)
    assert ok.check_separation(4.0e6, P_ATM_SEA_LEVEL, GAMMA) is None


def test_erosion_off_by_default_and_rate_zero():
    n = Nozzle(throat_diameter=0.02)
    assert n.erosion.enabled is False
    assert n.erosion_rate(5.0e6) == 0.0


def test_erosion_rate_and_unrealistic_warning():
    e = ErosionParams(enabled=True, coefficient_mm_s=0.05, exponent=0.8)
    # 5 MPa -> 0.05 * 5**0.8 mm/s -> m/s
    assert e.rate_m_s(5.0e6) == pytest.approx(0.05 * 5.0**0.8 / 1000.0, rel=1e-9)
    assert e.validate() == []
    bad = ErosionParams(enabled=True, coefficient_mm_s=1.6)
    assert bad.validate()[0].code == "WARN_UNREALISTIC_EROSION"


def test_eroded_throat_lowers_effective_expansion_ratio():
    """Only the throat erodes at a meaningful rate (Section 5.3); the exit is
    physically fixed, so a grown throat means a *smaller* effective expansion
    ratio (exit_area is fixed, throat_area grew) - not the nominal one."""
    n = Nozzle(throat_diameter=0.012, expansion_ratio=6.0)
    a_t0 = n.throat_area
    a_t_eroded = a_t0 * 1.44  # a throat radius grown 20%
    assert n.exit_area / a_t_eroded == pytest.approx(6.0 / 1.44)
    # thrust_coefficient must actually use that smaller ratio, not the nominal one
    cf_nominal = n.thrust_coefficient(3.0e6, P_ATM_SEA_LEVEL, GAMMA)
    cf_eroded = n.thrust_coefficient(3.0e6, P_ATM_SEA_LEVEL, GAMMA, throat_area=a_t_eroded)
    assert cf_eroded != pytest.approx(cf_nominal, rel=1e-6)
    # and it must match calling exit_pressure with that ratio directly
    p_e_direct = n.exit_pressure(3.0e6, GAMMA, expansion_ratio=n.exit_area / a_t_eroded)
    p_e_via_cf_path = n.exit_pressure(3.0e6, GAMMA, n.exit_area / a_t_eroded)
    assert p_e_direct == pytest.approx(p_e_via_cf_path)


def test_thrust_with_explicit_throat_area_matches_nominal_when_unchanged():
    """Passing throat_area == the nozzle's own nominal throat_area must reproduce
    exactly the no-argument call (this is the erosion-disabled / regression-test
    path: a_t stays == a_t0 for the whole burn, so nothing may change there)."""
    n = Nozzle(throat_diameter=0.012, expansion_ratio=5.0)
    f_default = n.thrust(3.0e6, P_ATM_SEA_LEVEL, GAMMA)
    f_explicit = n.thrust(3.0e6, P_ATM_SEA_LEVEL, GAMMA, throat_area=n.throat_area)
    assert f_explicit == pytest.approx(f_default, rel=1e-12)


def test_thrust_scales_with_eroded_throat_area():
    n = Nozzle(throat_diameter=0.012, expansion_ratio=5.0)
    a_t0 = n.throat_area
    f_nominal = n.thrust(3.0e6, P_ATM_SEA_LEVEL, GAMMA)
    f_eroded = n.thrust(3.0e6, P_ATM_SEA_LEVEL, GAMMA, throat_area=a_t0 * 1.2)
    # dominated by the larger throat area even though Cf itself also shifts
    assert f_eroded > f_nominal
