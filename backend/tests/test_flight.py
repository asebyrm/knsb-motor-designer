"""1-DOF flight: ISA atmosphere, RK4 integration sanity."""

from __future__ import annotations

import pytest

from core.ballistics import simulate
from core.examples import mid_flight_motor, small_test_motor
from core.flight import FlightInput, air_density, isa_atmosphere, simulate_flight


def test_isa_sea_level():
    t, p, rho = isa_atmosphere(0.0)
    assert t == pytest.approx(288.15)
    assert p == pytest.approx(101_325.0, rel=1e-6)
    assert rho == pytest.approx(1.225, rel=1e-3)


def test_isa_density_drops_with_altitude():
    assert air_density(3000.0) < air_density(0.0)
    assert air_density(0.0) == pytest.approx(1.225, rel=1e-3)


@pytest.fixture(scope="module")
def small_ballistics():
    ex = small_test_motor()
    return simulate(ex.grain, ex.propellant, ex.nozzle, meop_pa=ex.meop_pa)


def test_flight_reaches_apogee_and_returns_sane_numbers(small_ballistics):
    res = simulate_flight(small_ballistics, FlightInput(dry_mass=1.2, body_diameter=0.05))
    assert res.apogee > 0
    assert res.burnout_altitude < res.apogee
    assert res.max_velocity >= res.rail_exit_velocity > 0
    assert res.time_to_apogee > 0


def test_heavier_rocket_flies_lower(small_ballistics):
    light = simulate_flight(small_ballistics, FlightInput(dry_mass=1.0, body_diameter=0.05))
    heavy = simulate_flight(small_ballistics, FlightInput(dry_mass=4.0, body_diameter=0.05))
    assert heavy.apogee < light.apogee


def test_more_drag_flies_lower(small_ballistics):
    slick = simulate_flight(small_ballistics,
                            FlightInput(dry_mass=1.5, body_diameter=0.05, drag_coefficient=0.4))
    draggy = simulate_flight(small_ballistics,
                             FlightInput(dry_mass=1.5, body_diameter=0.05, drag_coefficient=0.9))
    assert draggy.apogee < slick.apogee


def test_rail_exit_velocity_recorded(small_ballistics):
    res = simulate_flight(small_ballistics,
                          FlightInput(dry_mass=1.5, body_diameter=0.05, rail_length=3.0))
    assert 0 < res.rail_exit_velocity < res.max_velocity


def test_mid_motor_flight_runs():
    ex = mid_flight_motor()
    b = simulate(ex.grain, ex.propellant, ex.nozzle, meop_pa=ex.meop_pa)
    res = simulate_flight(b, FlightInput(dry_mass=6.0, body_diameter=0.10))
    assert res.apogee > 100
    assert res.max_mach > 0
