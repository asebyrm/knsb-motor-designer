"""Propellant model and piecewise Saint-Robert burn-rate law.

Data comes from ``data/propellants/<id>.yaml`` (schema in Section 5.1 of the spec).
Adding a propellant = adding a YAML file; no code changes.

Burn-rate law (piecewise)
-------------------------
The tables give ``r_b`` in **mm/s** and ``p_c`` in **MPa**::

    r_b[mm/s] = a * (p_c[MPa]) ** n

Inside the core everything is SI, so the conversion (done in exactly ONE place,
:meth:`Propellant.burn_rate`) is::

    r_b[m/s] = a * (p_c[Pa] / 1e6) ** n / 1000

Equilibrium chamber pressure
----------------------------
Mass balance  rho_p * A_b * r_b(p) = p * A_t / c*_eff  gives, per piecewise row,

    p_eq = (rho_p * eta_cstar * a_SI * c*_ideal * K_n) ** (1 / (1 - n))

with ``a_SI`` the SI-form coefficient. Because ``(a, n)`` depend on pressure the
correct row is the *self-consistent* one: solve each row, accept the result that
falls inside that row's pressure band. If none is self-consistent (possible in the
negative-``n`` bands where multiple crossings exist) fall back to Brent root finding
on the residual ``R(p) = rho_p * c*_eff * K_n * r_b(p) - p``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

from core.units import R_UNIVERSAL
from core.warnings import Warning, make

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "propellants"


@dataclass(frozen=True)
class BurnRateRange:
    """One row of the piecewise Saint-Robert table. Pressures in MPa, a/n table units."""

    p_min_mpa: float
    p_max_mpa: float
    a: float
    n: float

    def a_si(self) -> float:
        """Coefficient in SI form: r_b[m/s] = a_si * p[Pa] ** n."""
        return self.a * (1e-6 ** self.n) / 1000.0

    def burn_rate(self, p_pa: float) -> float:
        """r_b [m/s] for chamber pressure ``p_pa`` [Pa] using THIS row's a, n."""
        return self.a * (max(p_pa, 0.0) / 1e6) ** self.n / 1000.0


class PressureSolveMethod(str, Enum):
    PIECEWISE_CLOSED_FORM = "piecewise_closed_form"
    BRENT = "brent"
    FAILED = "failed"


@dataclass(frozen=True)
class EquilibriumSolution:
    pressure_pa: float
    method: PressureSolveMethod
    row_index: int | None
    warnings: tuple[Warning, ...] = ()


@dataclass(frozen=True)
class Propellant:
    id: str
    name_tr: str
    name_en: str
    composition: str
    density_ideal: float          # kg/m^3
    density_factor: float         # actual/ideal cast density
    c_star_ideal: float           # m/s
    c_star_efficiency: float      # eta_c*
    gamma: float
    flame_temperature: float      # K
    molar_mass: float             # g/mol
    burn_rate_ranges: tuple[BurnRateRange, ...]

    # --- derived ------------------------------------------------------------

    @property
    def density(self) -> float:
        """Actual cast density [kg/m^3] = density_ideal * density_factor."""
        return self.density_ideal * self.density_factor

    @property
    def c_star_effective(self) -> float:
        """c*_eff [m/s] = c_star_ideal * c_star_efficiency."""
        return self.c_star_ideal * self.c_star_efficiency

    @property
    def r_specific(self) -> float:
        """Specific gas constant [J/(kg*K)] = R_universal / (M[kg/mol])."""
        return R_UNIVERSAL / (self.molar_mass / 1000.0)

    @property
    def table_p_min_pa(self) -> float:
        return min(r.p_min_mpa for r in self.burn_rate_ranges) * 1e6

    @property
    def table_p_max_pa(self) -> float:
        return max(r.p_max_mpa for r in self.burn_rate_ranges) * 1e6

    def c_star_theoretical(self) -> float:
        """Cross-check value [m/s]: c* = sqrt(R*Tc/g) / sqrt((2/(g+1))**((g+1)/(g-1)))."""
        g = self.gamma
        num = math.sqrt(self.r_specific * self.flame_temperature / g)
        den = math.sqrt((2.0 / (g + 1.0)) ** ((g + 1.0) / (g - 1.0)))
        return num / den

    # --- burn rate --------------------------------------------------------

    def _row_for_pressure(self, p_pa: float) -> BurnRateRange:
        """Row whose band contains ``p_pa``; nearest row if outside the table."""
        p_mpa = p_pa / 1e6
        for r in self.burn_rate_ranges:
            if r.p_min_mpa <= p_mpa <= r.p_max_mpa:
                return r
        if p_mpa < self.burn_rate_ranges[0].p_min_mpa:
            return self.burn_rate_ranges[0]
        return self.burn_rate_ranges[-1]

    def burn_rate(self, p_pa: float) -> float:
        """r_b [m/s] at chamber pressure ``p_pa`` [Pa]. Extrapolates outside the table."""
        return self._row_for_pressure(p_pa).burn_rate(p_pa)

    def is_extrapolated(self, p_pa: float) -> bool:
        """True if ``p_pa`` is outside the tabulated pressure range."""
        return p_pa < self.table_p_min_pa or p_pa > self.table_p_max_pa

    # --- equilibrium pressure -------------------------------------------

    def _p_eq_closed_form(self, row: BurnRateRange, k_n: float) -> float:
        """Closed-form equilibrium pressure [Pa] for one row's (a, n)."""
        n = row.n
        if abs(1.0 - n) < 1e-6:
            raise ValueError("closed form undefined for n == 1")
        base = self.density * self.c_star_efficiency * row.a_si() * self.c_star_ideal * k_n
        if base <= 0.0:
            raise ValueError("non-positive base in closed form")
        return base ** (1.0 / (1.0 - n))

    def _residual(self, p_pa: float, k_n: float) -> float:
        """R(p) = rho * c*_eff * K_n * r_b(p) - p. Zero at equilibrium."""
        return self.density * self.c_star_effective * k_n * self.burn_rate(p_pa) - p_pa

    def solve_equilibrium_pressure(self, k_n: float) -> EquilibriumSolution:
        """Equilibrium chamber pressure for a given Klemmung ``K_n = A_b / A_t``."""
        if k_n <= 0.0:
            return EquilibriumSolution(0.0, PressureSolveMethod.FAILED, None,
                                       (make("WARN_NO_EQUILIBRIUM_PRESSURE", reason="k_n<=0"),))

        warns: list[Warning] = []

        # 1) self-consistent closed-form row
        consistent: list[tuple[int, float]] = []
        for i, row in enumerate(self.burn_rate_ranges):
            try:
                p = self._p_eq_closed_form(row, k_n)
            except ValueError:
                continue
            if row.p_min_mpa <= p / 1e6 <= row.p_max_mpa:
                consistent.append((i, p))

        if consistent:
            # prefer a locally stable crossing (dR/dp < 0); among those the lowest p
            def stable(p: float) -> bool:
                dp = max(p * 1e-4, 1.0)
                return (self._residual(p + dp, k_n) - self._residual(p - dp, k_n)) < 0.0

            stable_hits = [(i, p) for i, p in consistent if stable(p)]
            pick = min(stable_hits or consistent, key=lambda t: t[1])
            idx, p = pick
            if self.is_extrapolated(p):
                warns.append(make("WARN_EXTRAPOLATED_BURN_RATE", pressure_mpa=round(p / 1e6, 3)))
            return EquilibriumSolution(p, PressureSolveMethod.PIECEWISE_CLOSED_FORM, idx, tuple(warns))

        # 2) Brent on the residual
        from scipy.optimize import brentq  # local import keeps import graph light

        lo = 0.2 * self.table_p_min_pa
        hi = 5.0 * self.table_p_max_pa
        f_lo, f_hi = self._residual(lo, k_n), self._residual(hi, k_n)
        expand = 0
        while f_lo * f_hi > 0.0 and expand < 40:
            hi *= 1.5
            f_hi = self._residual(hi, k_n)
            expand += 1
        if f_lo * f_hi > 0.0:
            # last resort: coarse scan for a sign change
            import numpy as np

            grid = np.linspace(lo, hi, 400)
            vals = np.array([self._residual(float(p), k_n) for p in grid])
            sign_change = np.where(np.sign(vals[:-1]) != np.sign(vals[1:]))[0]
            if len(sign_change) == 0:
                best = float(grid[int(np.argmin(np.abs(vals)))])
                return EquilibriumSolution(
                    best, PressureSolveMethod.FAILED, None,
                    (make("WARN_NO_EQUILIBRIUM_PRESSURE", k_n=round(k_n, 1)),),
                )
            j = int(sign_change[0])
            lo, hi = float(grid[j]), float(grid[j + 1])

        p = float(brentq(self._residual, lo, hi, args=(k_n,), xtol=1.0, rtol=1e-8, maxiter=200))
        warns.append(make("WARN_PRESSURE_SOLVER_FALLBACK", pressure_mpa=round(p / 1e6, 3)))
        if self.is_extrapolated(p):
            warns.append(make("WARN_EXTRAPOLATED_BURN_RATE", pressure_mpa=round(p / 1e6, 3)))
        return EquilibriumSolution(p, PressureSolveMethod.BRENT, None, tuple(warns))

    # --- loading --------------------------------------------------------

    @classmethod
    def from_dict(cls, d: dict) -> "Propellant":
        ranges = tuple(
            BurnRateRange(
                p_min_mpa=float(r["p_min"]),
                p_max_mpa=float(r["p_max"]),
                a=float(r["a"]),
                n=float(r["n"]),
            )
            for r in d["burn_rate_ranges"]
        )
        ranges = tuple(sorted(ranges, key=lambda r: r.p_min_mpa))
        return cls(
            id=d["id"],
            name_tr=d["name_tr"],
            name_en=d["name_en"],
            composition=d.get("composition", ""),
            density_ideal=float(d["density_ideal"]),
            density_factor=float(d.get("density_factor", 1.0)),
            c_star_ideal=float(d["c_star_ideal"]),
            c_star_efficiency=float(d.get("c_star_efficiency", 1.0)),
            gamma=float(d["gamma"]),
            flame_temperature=float(d["flame_temperature"]),
            molar_mass=float(d["molar_mass"]),
            burn_rate_ranges=ranges,
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Propellant":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh))


def available_propellants() -> list[str]:
    """IDs of every YAML propellant file that can be loaded."""
    return sorted(p.stem for p in _DATA_DIR.glob("*.yaml"))


def load_propellant(identifier: str) -> Propellant:
    """Load a propellant by file stem (e.g. ``"knsb"``) or by its ``id`` field."""
    direct = _DATA_DIR / f"{identifier}.yaml"
    if direct.exists():
        return Propellant.from_yaml(direct)
    for path in _DATA_DIR.glob("*.yaml"):
        prop = Propellant.from_yaml(path)
        if prop.id == identifier:
            return prop
    raise FileNotFoundError(f"no propellant {identifier!r} in {_DATA_DIR}")
