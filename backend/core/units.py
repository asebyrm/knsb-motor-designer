"""Physical constants and unit conversions.

The core engine works entirely in SI (m, kg, s, Pa, N, K). These helpers exist only
for the I/O layer (CLI, API request/response, export files, UI). Never call them from
inside the physics loop.

Conventions
-----------
``<unit>_to_si(x)``  converts a value expressed in ``<unit>`` to SI.
``si_to_<unit>(x)``  converts an SI value to ``<unit>``.
"""

from __future__ import annotations

import math

# --- fundamental constants -------------------------------------------------------

G0: float = 9.80665
"""Standard gravity [m/s^2]. Used for specific impulse: Isp = It / (m_p * G0)."""

R_UNIVERSAL: float = 8.314462618
"""Universal gas constant [J/(mol*K)]."""

P_ATM_SEA_LEVEL: float = 101_325.0
"""ISA sea-level static pressure [Pa]."""

T_ATM_SEA_LEVEL: float = 288.15
"""ISA sea-level temperature [K]."""

RHO_AIR_SEA_LEVEL: float = 1.225
"""ISA sea-level air density [kg/m^3]."""

# --- pressure ------------------------------------------------------------------

def bar_to_pa(x: float) -> float:
    """bar -> Pa. 1 bar = 1e5 Pa."""
    return x * 1e5


def pa_to_bar(x: float) -> float:
    """Pa -> bar."""
    return x / 1e5


def mpa_to_pa(x: float) -> float:
    """MPa -> Pa."""
    return x * 1e6


def pa_to_mpa(x: float) -> float:
    """Pa -> MPa."""
    return x / 1e6


def psi_to_pa(x: float) -> float:
    """psi -> Pa. 1 psi = 6894.757293168 Pa."""
    return x * 6894.757293168


def pa_to_psi(x: float) -> float:
    """Pa -> psi."""
    return x / 6894.757293168


# --- length ------------------------------------------------------------------

def mm_to_m(x: float) -> float:
    """millimetre -> metre."""
    return x / 1000.0


def m_to_mm(x: float) -> float:
    """metre -> millimetre."""
    return x * 1000.0


def inch_to_m(x: float) -> float:
    """inch -> metre. 1 in = 0.0254 m."""
    return x * 0.0254


def m_to_inch(x: float) -> float:
    """metre -> inch."""
    return x / 0.0254


def inch_to_mm(x: float) -> float:
    """inch -> millimetre."""
    return x * 25.4


def mm_to_inch(x: float) -> float:
    """millimetre -> inch."""
    return x / 25.4


# --- force ------------------------------------------------------------------

def lbf_to_n(x: float) -> float:
    """pound-force -> newton. 1 lbf = 4.4482216152605 N."""
    return x * 4.4482216152605


def n_to_lbf(x: float) -> float:
    """newton -> pound-force."""
    return x / 4.4482216152605


# --- mass ------------------------------------------------------------------

def lb_to_kg(x: float) -> float:
    """pound-mass -> kilogram. 1 lb = 0.45359237 kg."""
    return x * 0.45359237


def kg_to_lb(x: float) -> float:
    """kilogram -> pound-mass."""
    return x / 0.45359237


def g_to_kg(x: float) -> float:
    """gram -> kilogram."""
    return x / 1000.0


def kg_to_g(x: float) -> float:
    """kilogram -> gram."""
    return x * 1000.0


# --- temperature -----------------------------------------------------------

def celsius_to_k(x: float) -> float:
    """degree Celsius -> kelvin."""
    return x + 273.15


def k_to_celsius(x: float) -> float:
    """kelvin -> degree Celsius."""
    return x - 273.15


# --- geometry helpers ----------------------------------------------------------

def circle_area(diameter: float) -> float:
    """Area of a circle from its diameter [same unit^2 as input^2]."""
    return math.pi * (diameter * 0.5) ** 2


def circle_diameter(area: float) -> float:
    """Diameter of a circle from its area."""
    return 2.0 * math.sqrt(area / math.pi)
