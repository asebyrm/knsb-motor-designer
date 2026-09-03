"""Simplified 1-DOF vertical flight prediction (Section 6.1).

This is NOT a flight simulator. It assumes vertical flight, constant drag
coefficient and still air. Real apogee typically scatters +/-15-25 %. It exists only
to close the loop for the mission solver (Section 6); serious work must export to
OpenRocket / RockSim.

    m(t) = m_dry + m_prop_remaining(t)
    D    = 0.5 * rho_air(h) * v^2 * Cd * A
    a    = (F(t) - D - m*g) / m

ISA troposphere (<= 11 km), RK4, dt = 0.01 s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from core.ballistics import BallisticsResult
from core.units import G0

# ISA constants
_T0 = 288.15          # K
_P0 = 101_325.0       # Pa
_L = 0.0065           # K/m lapse rate
_R_AIR = 287.058      # J/(kg*K)
_GAMMA_AIR = 1.4
_ISA_EXP = G0 / (_R_AIR * _L)   # ~5.2559


@dataclass
class FlightInput:
    dry_mass: float                # kg, rocket without the motor's propellant (incl. inert motor)
    body_diameter: float           # m
    drag_coefficient: float = 0.55
    rail_length: float = 2.0       # m
    launch_altitude: float = 0.0   # m ASL
    max_accel_g: float | None = None  # informational limit


@dataclass
class FlightResult:
    apogee: float                  # m AGL
    max_velocity: float            # m/s
    max_mach: float
    max_acceleration_g: float
    rail_exit_velocity: float      # m/s
    burnout_altitude: float        # m AGL
    burnout_velocity: float        # m/s
    time_to_apogee: float          # s
    time: np.ndarray
    altitude: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray

    def to_dict(self) -> dict:
        return {
            "apogee_m": self.apogee,
            "max_velocity_ms": self.max_velocity,
            "max_mach": self.max_mach,
            "max_acceleration_g": self.max_acceleration_g,
            "rail_exit_velocity_ms": self.rail_exit_velocity,
            "burnout_altitude_m": self.burnout_altitude,
            "burnout_velocity_ms": self.burnout_velocity,
            "time_to_apogee_s": self.time_to_apogee,
        }


def isa_atmosphere(altitude_m: float) -> tuple[float, float, float]:
    """(temperature K, pressure Pa, density kg/m^3) for the ISA troposphere."""
    h = min(max(altitude_m, 0.0), 11_000.0)
    t = _T0 - _L * h
    p = _P0 * (t / _T0) ** _ISA_EXP
    rho = p / (_R_AIR * t)
    return t, p, rho


def air_density(altitude_m: float) -> float:
    return isa_atmosphere(altitude_m)[2]


def speed_of_sound(altitude_m: float) -> float:
    t, _, _ = isa_atmosphere(altitude_m)
    return math.sqrt(_GAMMA_AIR * _R_AIR * t)


def simulate_flight(
    ballistics: BallisticsResult,
    params: FlightInput,
    *,
    dt: float = 0.01,
    t_max: float = 600.0,
) -> FlightResult:
    """Integrate vertical flight from lift-off to apogee."""
    t_curve = ballistics.time
    f_curve = ballistics.thrust
    m_prop_curve = ballistics.propellant_mass
    m_prop0 = float(m_prop_curve[0]) if m_prop_curve.size else 0.0
    t_end_thrust = float(t_curve[-1]) if t_curve.size else 0.0
    area = math.pi * (params.body_diameter / 2.0) ** 2
    cd = params.drag_coefficient
    base_alt = params.launch_altitude

    def thrust_at(tt: float) -> float:
        if tt <= 0 or tt >= t_end_thrust:
            return 0.0
        return float(np.interp(tt, t_curve, f_curve))

    def prop_mass_at(tt: float) -> float:
        if tt <= 0:
            return m_prop0
        if tt >= t_end_thrust:
            return float(m_prop_curve[-1])
        return float(np.interp(tt, t_curve, m_prop_curve))

    def accel(tt: float, h: float, v: float) -> float:
        m = params.dry_mass + prop_mass_at(tt)
        rho = air_density(base_alt + h)
        drag = 0.5 * rho * v * abs(v) * cd * area
        return (thrust_at(tt) - drag) / m - G0

    t = 0.0
    h = 0.0
    v = 0.0
    times, alts, vels, accs = [0.0], [0.0], [0.0], [accel(0.0, 0.0, 0.0)]
    rail_exit_v = 0.0
    rail_left = False
    max_v = 0.0
    max_a = accs[0]
    burnout_alt = 0.0
    burnout_v = 0.0
    recorded_burnout = False

    steps = 0
    while t < t_max and steps < int(t_max / dt):
        # RK4 on (h, v)
        k1v = accel(t, h, v)
        k1h = v
        k2v = accel(t + dt / 2, h + k1h * dt / 2, v + k1v * dt / 2)
        k2h = v + k1v * dt / 2
        k3v = accel(t + dt / 2, h + k2h * dt / 2, v + k2v * dt / 2)
        k3h = v + k2v * dt / 2
        k4v = accel(t + dt, h + k3h * dt, v + k3v * dt)
        k4h = v + k3v * dt

        v_new = v + dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        h_new = h + dt / 6 * (k1h + 2 * k2h + 2 * k3h + k4h)
        t += dt

        if not rail_left and h_new >= params.rail_length:
            rail_exit_v = v_new
            rail_left = True
        if not recorded_burnout and t >= t_end_thrust:
            burnout_alt, burnout_v = h_new, v_new
            recorded_burnout = True

        a_inst = accel(t, h_new, v_new)
        max_v = max(max_v, v_new)
        max_a = max(max_a, a_inst)

        h, v = h_new, v_new
        times.append(t)
        alts.append(h)
        vels.append(v)
        accs.append(a_inst)
        steps += 1

        if v <= 0.0 and t > t_end_thrust:
            break

    apogee = max(alts)
    t_apogee = times[int(np.argmax(alts))]
    mach = max(
        (vels[i] / speed_of_sound(base_alt + alts[i]) for i in range(len(vels))),
        default=0.0,
    )
    return FlightResult(
        apogee=apogee,
        max_velocity=max_v,
        max_mach=mach,
        max_acceleration_g=max_a / G0,
        rail_exit_velocity=rail_exit_v,
        burnout_altitude=burnout_alt,
        burnout_velocity=burnout_v,
        time_to_apogee=t_apogee,
        time=np.asarray(times),
        altitude=np.asarray(alts),
        velocity=np.asarray(vels),
        acceleration=np.asarray(accs),
    )
