"""Centralised warning generation.

The core never emits user-facing text. Every diagnostic is a :class:`Warning` carrying

* ``code``   - stable identifier, e.g. ``"WARN_LOW_FOS"``
* ``level``  - ``"info"`` | ``"warning"`` | ``"danger"``
* ``params`` - numbers the frontend interpolates into the localised string

The i18n key for a warning is always ``info.warning.<CODE>``. The frontend (and the PDF
report generator) translate; see Section 11 of the spec.

``ALL_WARNING_CODES`` is the single source of truth used by the tooltip-coverage test:
every code here must have a ``tr`` and ``en`` translation or CI fails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Level(StrEnum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


@dataclass(frozen=True)
class Warning:
    """A single diagnostic. Immutable so it can be freely shared between layers."""

    code: str
    level: Level
    params: dict = field(default_factory=dict)

    @property
    def i18n_key(self) -> str:
        return f"info.warning.{self.code}"

    @property
    def is_blocking(self) -> bool:
        """A danger-level warning locks export until the user accepts the risk."""
        return self.level == Level.DANGER

    def to_dict(self) -> dict:
        return {"code": self.code, "level": self.level.value, "params": self.params}


# --- catalogue ---------------------------------------------------------------
# code -> default level. Keep this list in sync with the i18n files.

_CATALOGUE: dict[str, Level] = {
    # propellant / burn-rate
    "WARN_EXTRAPOLATED_BURN_RATE": Level.WARNING,
    "WARN_NO_EQUILIBRIUM_PRESSURE": Level.DANGER,
    "WARN_PRESSURE_SOLVER_FALLBACK": Level.INFO,
    # grain geometry
    "WARN_PROGRESSIVE_GEOMETRY": Level.WARNING,
    "WARN_ENDBURNER_THERMAL_SOAK": Level.WARNING,
    "WARN_GRAIN_CORE_TOO_LARGE": Level.WARNING,
    "WARN_SLIVER_FRACTION_HIGH": Level.INFO,
    # nozzle
    "WARN_FLOW_SEPARATION": Level.WARNING,
    "WARN_UNREALISTIC_EROSION": Level.WARNING,
    "WARN_NOZZLE_OVEREXPANDED": Level.INFO,
    "WARN_NOZZLE_UNDEREXPANDED": Level.INFO,
    "WARN_EXPANSION_RATIO_SUBOPTIMAL": Level.INFO,
    # ballistics
    "WARN_MEOP_EXCEEDED": Level.DANGER,
    "WARN_QUASI_STEADY_INVALID": Level.WARNING,
    "WARN_CONVERGENCE_NOT_REACHED": Level.WARNING,
    "WARN_BURN_TIME_EXCEEDED_LIMIT": Level.WARNING,
    # erosive burning / L*
    "WARN_EROSIVE_BURNING": Level.WARNING,
    "WARN_EROSIVE_BURNING_CRITICAL": Level.DANGER,
    "WARN_LSTAR_OUT_OF_RANGE": Level.WARNING,
    # structure
    "WARN_LOW_FOS": Level.DANGER,
    "WARN_MARGINAL_FOS": Level.WARNING,
    "WARN_THICK_WALL_MODEL": Level.INFO,
    "WARN_BULKHEAD_FASTENERS": Level.WARNING,
    "WARN_PRINT_DIRECTION_WEAK": Level.INFO,
    # thermal
    "WARN_THERMAL_LIMIT": Level.DANGER,
    "WARN_NO_LINER": Level.DANGER,
    "WARN_LINER_THIN": Level.WARNING,
    # assembly / fit
    "WARN_FIT_GRAIN_DIAMETER": Level.DANGER,
    "WARN_FIT_GRAIN_LENGTH": Level.DANGER,
    "WARN_FIT_THROAT_VS_CASE": Level.DANGER,
    "WARN_FIT_LINER_STACK": Level.DANGER,
    "WARN_FIT_PORT_NONPOSITIVE": Level.DANGER,
    # flight / mission
    "WARN_RAIL_EXIT_VELOCITY_LOW": Level.WARNING,
    "WARN_ACCEL_LIMIT_EXCEEDED": Level.WARNING,
    "WARN_APOGEE_UNCERTAINTY": Level.INFO,
    "WARN_THRUST_TO_WEIGHT_LOW": Level.WARNING,
    # solver
    "WARN_MISSION_INFEASIBLE": Level.WARNING,
    "WARN_SOLVER_TIMEOUT": Level.INFO,
    "WARN_SOLVER_BEST_EFFORT": Level.INFO,
    # calibration
    "WARN_UNCALIBRATED_DEFAULTS": Level.INFO,
}

ALL_WARNING_CODES: tuple[str, ...] = tuple(_CATALOGUE.keys())


def make(code: str, level: Level | None = None, **params) -> Warning:
    """Build a :class:`Warning` for a known code.

    ``level`` overrides the catalogue default (used e.g. to escalate a warning to
    danger when a threshold is badly violated).
    """
    if code not in _CATALOGUE:
        raise KeyError(f"unknown warning code {code!r}")
    return Warning(code=code, level=level or _CATALOGUE[code], params=dict(params))


def warning_catalogue() -> dict[str, str]:
    """Public ``{code: level}`` map (level as its string value) for the API catalogue."""
    return {code: level.value for code, level in _CATALOGUE.items()}


def highest_level(warnings: list[Warning]) -> Level:
    """The most severe level in a list (info if empty)."""
    order = {Level.INFO: 0, Level.WARNING: 1, Level.DANGER: 2}
    return max((w.level for w in warnings), key=lambda lv: order[lv], default=Level.INFO)


def has_blocking(warnings: list[Warning]) -> bool:
    """True if any warning locks export."""
    return any(w.is_blocking for w in warnings)


def dedupe(warnings: list[Warning]) -> list[Warning]:
    """Collapse duplicate codes, keeping the first (usually most specific) params."""
    seen: set[str] = set()
    out: list[Warning] = []
    for w in warnings:
        if w.code in seen:
            continue
        seen.add(w.code)
        out.append(w)
    return out
