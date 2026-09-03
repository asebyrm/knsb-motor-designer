"""Canonical example motors, including the Section 13.1 regression reference.

These build ``core`` objects directly so the CLI and the test-suite share one
definition. The JSON design library under ``data/examples/`` is generated from these
(see ``scripts/gen_examples.py``).
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

from core.grains.base import GrainGeometry
from core.grains.bates import BatesGrain, suggest_neutral_segment_length
from core.grains.tubular import TubularGrain
from core.nozzle import ErosionParams, Nozzle
from core.propellant import Propellant, load_propellant


@dataclass
class ExampleMotor:
    key: str
    name: str
    grain: GrainGeometry
    propellant: Propellant
    nozzle: Nozzle
    ambient_pressure: float = 101_325.0
    chamber_volume: float | None = None
    meop_pa: float | None = None
    note: str = ""


def reference_case() -> ExampleMotor:
    """Section 13.1 reference: KNSB, internal-burning tube, erosion OFF.

    Inputs fixed by the spec table:
        rho = 1840 kg/m^3, c* = 910.93 m/s, gamma = 1.1251, eta_c* = Phi = 1.0
        design pressure 10 bar, target thrust 300 N at t=0, Cf = 1.2744, Isp = 118.4 s
        J = A_p / A_t = 4

    Derived (must match within 2 %):
        A_t = F / (Cf * p_c) = 300 / (1.2744 * 1e6) = 235 mm^2  -> r_t0 = 8.65 mm
        r_p0 = sqrt(J * A_t / pi) = 17.3 mm
        L   = K_n(10 bar) * A_t / (2*pi*r_p0) ~ 147 mm

    D_o = 85.8 mm is chosen so the (correctly) progressive tube peaks at ~22 bar,
    matching the İTÜ PARS report. The expected outcome is deliberately UNSAFE: the
    test proves ``WARN_MEOP_EXCEEDED`` fires, it does not "fix" the motor.
    """
    base = load_propellant("knsb")
    prop = dataclasses.replace(
        base,
        density_ideal=1840.0,
        density_factor=1.0,
        c_star_ideal=910.93,
        c_star_efficiency=1.0,
        gamma=1.1251,
    )

    a_t = 235e-6
    r_t0 = math.sqrt(a_t / math.pi)
    r_p0 = math.sqrt(4.0 * a_t / math.pi)
    length = 0.14721  # m, from K_n(10 bar) closed form (see docstring)

    grain = TubularGrain(outer_diameter=0.0858, core_diameter=2.0 * r_p0, length=length)
    nozzle = Nozzle(
        throat_diameter=2.0 * r_t0,
        expansion_ratio=4.0,
        divergence_half_angle_deg=15.0,
        efficiency=0.95,
        erosion=ErosionParams(enabled=False),
    )
    return ExampleMotor(
        key="reference",
        name="İTÜ PARS reference tube (Section 13.1)",
        grain=grain,
        propellant=prop,
        nozzle=nozzle,
        meop_pa=15e5,
        note="Deliberately unsafe: progressive tube, peak ~22 bar > 15 bar MEOP.",
    )


def small_test_motor() -> ExampleMotor:
    """A small, benign single-segment BATES 'H' motor for quick UI exploration."""
    prop = load_propellant("knsb")
    d_o = 0.038
    d = 0.014
    l_s = suggest_neutral_segment_length(d_o, d)
    grain = BatesGrain(d_o, d, l_s, segment_count=1)
    nozzle = Nozzle(throat_diameter=0.0085, expansion_ratio=4.5)
    return ExampleMotor("small", "Small test motor (BATES, ~H)", grain, prop, nozzle,
                        meop_pa=45e5, note="Neutral single-segment BATES.")


def mid_flight_motor() -> ExampleMotor:
    """Mid-size 3-segment BATES flight motor, roughly a 'J'."""
    prop = load_propellant("knsb")
    d_o = 0.054
    d = 0.020
    l_s = suggest_neutral_segment_length(d_o, d)
    grain = BatesGrain(d_o, d, l_s, segment_count=3, segment_spacing=0.003)
    nozzle = Nozzle(throat_diameter=0.0135, expansion_ratio=5.0)
    return ExampleMotor("mid", "Mid flight motor (3x BATES, ~J)", grain, prop, nozzle,
                        meop_pa=70e5, note="Three neutral BATES segments.")


def unsafe_example() -> ExampleMotor:
    """Intentionally unsafe: tiny throat + large grain -> over-pressure, low J."""
    prop = load_propellant("knsb")
    grain = BatesGrain(0.060, 0.012, 0.20, segment_count=4)
    nozzle = Nozzle(throat_diameter=0.008, expansion_ratio=3.0)
    return ExampleMotor("unsafe", "Intentionally unsafe motor", grain, prop, nozzle,
                        meop_pa=60e5, note="Over-pressured, erosive; export must lock.")


ALL_EXAMPLES = {
    "reference": reference_case,
    "small": small_test_motor,
    "mid": mid_flight_motor,
    "unsafe": unsafe_example,
}


def load_example(key: str) -> ExampleMotor:
    if key not in ALL_EXAMPLES:
        raise KeyError(f"unknown example {key!r}; have {sorted(ALL_EXAMPLES)}")
    return ALL_EXAMPLES[key]()
