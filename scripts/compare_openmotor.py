#!/usr/bin/env python3
"""Cross-check this engine against openMotor (github.com/reilleya/openMotor).

Fills the comparison table in docs/VALIDATION.md §2 (acceptance criterion 10).

openMotor's ``motorlib`` is used headless. It needs its Cython extension built:

    git clone --depth 1 https://github.com/reilleya/openMotor
    cd openMotor && pip install numpy scipy scikit-fmm scikit-image matplotlib ezdxf pyyaml cython
    python setup.py build_ext --inplace

then run this script with ``PYTHONPATH=<path-to-openMotor>``.

openMotor has **no c* efficiency knob** in the propellant model — it derives c* from
gamma / T / M. This engine runs at ``c*_eff = 0.95 * c*_ideal``. So we report two
openMotor rows per motor:
  * "default"  — openMotor's thermochemical c* (~911 m/s), the honest out-of-the-box run;
  * "c*-matched" — combustion temperature scaled by 0.95^2 so openMotor's c* equals
    this engine's effective 865 m/s, isolating the remaining method differences
    (ignition transient, exponential tail-off).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "backend"))

from core.examples import mid_flight_motor, small_test_motor

try:
    from motorlib.grains import BatesGrain
    from motorlib.motor import Motor
    from motorlib.propellant import Propellant
except ImportError:  # pragma: no cover
    sys.exit(
        "motorlib not importable — clone openMotor, build its extension and set "
        "PYTHONPATH. See this file's docstring."
    )

# KNSB piecewise Saint-Robert table, r_b[mm/s] = a * (p_c[MPa])^n
KNSB_TABLE = [
    (0.103, 0.807, 10.71, 0.625),
    (0.807, 1.50, 8.763, -0.314),
    (1.50, 3.79, 7.852, -0.013),
    (3.79, 7.03, 3.907, 0.535),
    (7.03, 10.67, 9.653, 0.064),
]
GAMMA, T_FLAME, MOLAR_MASS = 1.1251, 1600.0, 39.9
DENSITY = 1841.0 * 0.95  # 1748.9 kg/m^3
CSTAR_EFF_TARGET = 910.93 * 0.95  # 865.38 m/s (this engine)


def a_si(a_table: float, n: float) -> float:
    """Table 'a' (mm/s, MPa) -> openMotor 'a' (m/s, Pa)."""
    return a_table * (1e-6 ** n) / 1000.0


def build_propellant(temp: float) -> Propellant:
    tabs = []
    for pmin_mpa, pmax_mpa, a, n in KNSB_TABLE:
        tabs.append({
            "minPressure": pmin_mpa * 1e6,
            "maxPressure": pmax_mpa * 1e6,
            "a": a_si(a, n),
            "n": n,
            "k": GAMMA,
            "t": temp,
            "m": MOLAR_MASS,
        })
    return Propellant({"name": "KNSB (this repo)", "density": DENSITY, "tabs": tabs})


def build_motor(temp: float, *, d_o, d_core, l_seg, n_seg, d_throat, eps) -> Motor:
    m = Motor()
    m.propellant = build_propellant(temp)
    for _ in range(n_seg):
        g = BatesGrain()
        g.setProperties({
            "diameter": d_o,
            "length": l_seg,
            "coreDiameter": d_core,
            "inhibitedEnds": "Neither",
        })
        m.grains.append(g)
    m.nozzle.setProperties({
        "throat": d_throat,
        "exit": d_throat * math.sqrt(eps),
        "efficiency": 0.95,
        "divAngle": 15,
        "convAngle": 45,
        "throatLength": 0.5 * d_throat,
        "slagCoeff": 0,
        "erosionCoeff": 0,
    })
    m.config.setProperties({
        "maxPressure": 7e6,
        "maxMassFlux": 1e4,
        "maxMachNumber": 80,
        "minPortThroat": 1,
        "flowSeparationWarnPercent": 0.05,
        "burnoutWebThres": 2.54e-5,
        "burnoutThrustThres": 0.1,
        "timestep": 0.001,
        "ambPressure": 101325.0,
        "mapDim": 750,
        "sepPressureRatio": 0.4,
    })
    return m


def cstar_matched_temp(motor_default: Motor) -> float:
    """T that makes openMotor's c* equal this engine's effective c*."""
    c_default = motor_default.propellant.getCStar(2e6)
    return T_FLAME * (CSTAR_EFF_TARGET / c_default) ** 2


def run(m: Motor) -> dict:
    r = m.runSimulation()
    peak_force = r.channels["force"].getMax()
    return {
        "It": r.getImpulse(),
        "Favg": r.getAverageForce(),
        "Fpk": peak_force,
        "ppk_bar": r.getMaxPressure() / 1e5,
        "tb": r.getBurnTime(),
        "Isp": r.getISP(),
        "mp_g": r.getPropellantMass(0) * 1000.0,
        "desig": r.getDesignation(),
        "alerts": [a.description for a in r.alerts],
    }


def this_engine(factory) -> dict:
    from core.ballistics import simulate

    ex = factory()
    s = simulate(ex.grain, ex.propellant, ex.nozzle,
                 ambient_pressure=ex.ambient_pressure, meop_pa=ex.meop_pa).summary
    return {
        "It": s["total_impulse"], "Favg": s["average_thrust"], "Fpk": s["peak_thrust"],
        "ppk_bar": s["peak_pressure_no_erosion_bar"], "tb": s["burn_time"],
        "Isp": s["specific_impulse"], "mp_g": s["propellant_mass"] * 1000.0,
        "desig": s["designation"],
    }


MOTORS = {
    "Small BATES (Ø38, 1 seg)": {
        "d_o": 0.038, "d_core": 0.014, "l_seg": 0.064, "n_seg": 1,
        "d_throat": 0.0085, "eps": 4.5, "factory": small_test_motor,
    },
    "Mid 3xBATES (Ø54)": {
        "d_o": 0.054, "d_core": 0.020, "l_seg": 0.091, "n_seg": 3,
        "d_throat": 0.0135, "eps": 5.0, "factory": mid_flight_motor,
    },
}


def dev(a: float, b: float) -> str:
    return f"{(a - b) / b * 100:+.1f}%"


def main() -> None:
    for name, cfg in MOTORS.items():
        factory = cfg.pop("factory")
        mine = this_engine(factory)
        m_def = build_motor(T_FLAME, **cfg)
        om_def = run(m_def)
        t_match = cstar_matched_temp(m_def)
        om_match = run(build_motor(t_match, **cfg))

        print(f"\n### {name}")
        print(f"openMotor c* (default) = {m_def.propellant.getCStar(2e6):.1f} m/s ; "
              f"c*-matched run uses T = {t_match:.0f} K")
        hdr = f"{'metric':16s} {'this engine':>13s} {'oM default':>13s} {'Δ':>8s} " \
              f"{'oM c*-match':>13s} {'Δ':>8s}"
        print(hdr)
        for key, label, unit in [
            ("It", "total impulse", "N·s"), ("Favg", "avg thrust", "N"),
            ("Fpk", "peak thrust", "N"), ("ppk_bar", "peak pressure", "bar"),
            ("tb", "burn time", "s"), ("Isp", "Isp", "s"), ("mp_g", "propellant", "g"),
        ]:
            print(f"{label:16s} {mine[key]:13.2f} {om_def[key]:13.2f} "
                  f"{dev(om_def[key], mine[key]):>8s} {om_match[key]:13.2f} "
                  f"{dev(om_match[key], mine[key]):>8s}   {unit}")
        print(f"designation      {mine['desig']:>13s} {om_def['desig']:>13s} "
              f"{'':8s} {om_match['desig']:>13s}")
        if om_def["alerts"]:
            print("openMotor alerts:", "; ".join(sorted(set(om_def["alerts"]))))


if __name__ == "__main__":
    main()
