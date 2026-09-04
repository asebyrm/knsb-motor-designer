"""Converging-diverging nozzle: real thrust coefficient, expansion, separation, erosion.

No fixed ``Cf`` (Section 5.3). The exit Mach number is found from the area-Mach
relation (supersonic branch), the exit pressure from the isentropic relation, and::

    Cf_ideal  = sqrt( (2*g**2/(g-1)) * (2/(g+1))**((g+1)/(g-1))
                      * (1 - (p_e/p_c)**((g-1)/g)) )  +  (p_e - p_a)/p_c * eps
    lambda    = (1 + cos(alpha)) / 2                 # conical divergence loss
    Cf_actual = lambda * eta_nozzle * Cf_ideal
    F         = Cf_actual * p_c * A_t

Throat erosion (default OFF)::

    dr_t/dt = K * (p_c[MPa])**m          # K in mm/s, converted to m/s here

Per Section 5.3 erosion is NEVER a pressure-limiting device: MEOP is always judged on
the erosionless curve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from core.warnings import Warning, make

_SUMMERFIELD_RATIO = 0.4  # p_e < 0.4 * p_a  => flow separation likely


@dataclass
class ErosionParams:
    """Throat erosion model. Disabled by default."""

    enabled: bool = False
    coefficient_mm_s: float = 0.05   # K, graphite ~0.02-0.1 mm/s
    exponent: float = 0.8            # m

    def rate_m_s(self, p_c_pa: float) -> float:
        """dr_t/dt [m/s]. Zero when disabled."""
        if not self.enabled or p_c_pa <= 0:
            return 0.0
        p_mpa = p_c_pa / 1e6
        return self.coefficient_mm_s * p_mpa**self.exponent / 1000.0

    def validate(self) -> list[Warning]:
        if self.enabled and self.coefficient_mm_s > 0.3:
            return [make("WARN_UNREALISTIC_EROSION", k=self.coefficient_mm_s)]
        return []


@dataclass
class Nozzle:
    throat_diameter: float                    # m
    expansion_ratio: float = 4.0              # A_e / A_t
    divergence_half_angle_deg: float = 15.0   # alpha - the divergent cone's own half-angle
    convergence_half_angle_deg: float = 45.0
    efficiency: float = 0.95                  # eta_nozzle
    throat_length: float = 0.0                # m (for the technical drawing)
    contour_type: str = "conic"               # "conic" | "bell" - Section 5.3
    erosion: ErosionParams = field(default_factory=ErosionParams)

    # --- areas -------------------------------------------------------

    @property
    def throat_area(self) -> float:
        return math.pi * (self.throat_diameter / 2.0) ** 2

    @property
    def exit_area(self) -> float:
        return self.throat_area * self.expansion_ratio

    @property
    def exit_diameter(self) -> float:
        return 2.0 * math.sqrt(self.exit_area / math.pi)

    @property
    def divergence_loss(self) -> float:
        """lambda = (1 + cos(alpha)) / 2.

        A "bell" contour is approximated the standard way: its parabolic wall has a
        much smaller average local flow angle than a straight cone sharing the same
        exit half-angle, so the loss is evaluated at half that angle rather than the
        full one (a common first-order stand-in for a proper Rao contour, since this
        model does not trace the wall shape point by point).
        """
        alpha = self.divergence_half_angle_deg / 2.0 if self.contour_type == "bell" \
            else self.divergence_half_angle_deg
        return (1.0 + math.cos(math.radians(alpha))) / 2.0

    # --- gas dynamics ---------------------------------------------------

    def exit_mach(self, gamma: float, expansion_ratio: float | None = None) -> float:
        """Supersonic solution of the area-Mach relation for ``expansion_ratio``
        (the nominal ``self.expansion_ratio`` if not given).

        Only the throat erodes at any meaningful rate (Section 5.3) - the exit is
        physically fixed, so an eroded throat's *effective* expansion ratio is
        smaller than the nominal, un-eroded one. Callers tracking erosion pass
        that effective ratio explicitly; everyone else gets the nominal value,
        unchanged from before this parameter existed.
        """
        from scipy.optimize import brentq

        g = gamma
        exp = (g + 1.0) / (2.0 * (g - 1.0))

        def area_ratio(m: float) -> float:
            return (1.0 / m) * ((2.0 / (g + 1.0)) * (1.0 + 0.5 * (g - 1.0) * m * m)) ** exp

        target = self.expansion_ratio if expansion_ratio is None else expansion_ratio
        return float(brentq(lambda m: area_ratio(m) - target, 1.0 + 1e-9, 60.0, maxiter=200))

    def exit_pressure(self, p_c_pa: float, gamma: float,
                       expansion_ratio: float | None = None) -> float:
        """Isentropic exit static pressure [Pa]."""
        m_e = self.exit_mach(gamma, expansion_ratio)
        g = gamma
        return p_c_pa * (1.0 + 0.5 * (g - 1.0) * m_e * m_e) ** (-g / (g - 1.0))

    def thrust_coefficient(self, p_c_pa: float, p_ambient_pa: float, gamma: float,
                            throat_area: float | None = None) -> float:
        """Actual thrust coefficient Cf (divergence + efficiency losses applied).

        Pass the *current* (possibly eroded) ``throat_area`` to get Cf for the
        effective expansion ratio at that throat size (``exit_area`` is the fixed,
        nominal one - see :meth:`exit_mach`); omitted, this is the nominal Cf,
        identical to before this parameter existed.
        """
        g = gamma
        eps = self.expansion_ratio if throat_area is None else self.exit_area / throat_area
        p_e = self.exit_pressure(p_c_pa, gamma, eps)
        momentum = math.sqrt(
            (2.0 * g * g / (g - 1.0))
            * (2.0 / (g + 1.0)) ** ((g + 1.0) / (g - 1.0))
            * (1.0 - (p_e / p_c_pa) ** ((g - 1.0) / g))
        )
        pressure_term = (p_e - p_ambient_pa) / p_c_pa * eps
        cf_ideal = momentum + pressure_term
        return self.divergence_loss * self.efficiency * cf_ideal

    def thrust(self, p_c_pa: float, p_ambient_pa: float, gamma: float,
               throat_area: float | None = None) -> float:
        """F = Cf * p_c * A_t [N]. Pass ``throat_area`` to use an eroded throat -
        this also feeds Cf's effective expansion ratio (see thrust_coefficient)."""
        a_t = self.throat_area if throat_area is None else throat_area
        return self.thrust_coefficient(p_c_pa, p_ambient_pa, gamma, throat_area) * p_c_pa * a_t

    # --- expansion tuning / checks -----------------------------------

    def optimum_expansion_ratio(self, p_c_pa: float, p_ambient_pa: float, gamma: float) -> float:
        """eps giving p_e == p_a (fully expanded) at this chamber pressure."""
        from scipy.optimize import brentq

        original = self.expansion_ratio
        try:
            def mismatch(eps: float) -> float:
                self.expansion_ratio = eps
                return self.exit_pressure(p_c_pa, gamma) - p_ambient_pa

            return float(brentq(mismatch, 1.01, 200.0, maxiter=200))
        finally:
            self.expansion_ratio = original

    def erosion_rate(self, p_c_pa: float) -> float:
        return self.erosion.rate_m_s(p_c_pa)

    def check_separation(self, p_c_pa: float, p_ambient_pa: float, gamma: float) -> Warning | None:
        """Summerfield criterion: separation likely if p_e < 0.4 * p_a."""
        p_e = self.exit_pressure(p_c_pa, gamma)
        if p_e < _SUMMERFIELD_RATIO * p_ambient_pa:
            return make("WARN_FLOW_SEPARATION",
                        p_e_bar=round(p_e / 1e5, 2), p_a_bar=round(p_ambient_pa / 1e5, 2))
        return None

    def validate(self, p_c_design_pa: float, p_ambient_pa: float, gamma: float) -> list[Warning]:
        w: list[Warning] = []
        w += self.erosion.validate()
        sep = self.check_separation(p_c_design_pa, p_ambient_pa, gamma)
        if sep:
            w.append(sep)
        p_e = self.exit_pressure(p_c_design_pa, gamma)
        eps_opt = self.optimum_expansion_ratio(p_c_design_pa, p_ambient_pa, gamma)
        if p_e < 0.7 * p_ambient_pa:
            w.append(make("WARN_NOZZLE_OVEREXPANDED",
                          eps=round(self.expansion_ratio, 2), eps_opt=round(eps_opt, 2)))
        elif p_e > 1.5 * p_ambient_pa:
            w.append(make("WARN_NOZZLE_UNDEREXPANDED",
                          eps=round(self.expansion_ratio, 2), eps_opt=round(eps_opt, 2)))
        if abs(self.expansion_ratio - eps_opt) / eps_opt > 0.35:
            w.append(make("WARN_EXPANSION_RATIO_SUBOPTIMAL",
                          eps=round(self.expansion_ratio, 2), eps_opt=round(eps_opt, 2)))
        return w

    def to_dict(self) -> dict:
        return {
            "throat_diameter": self.throat_diameter,
            "expansion_ratio": self.expansion_ratio,
            "divergence_half_angle_deg": self.divergence_half_angle_deg,
            "convergence_half_angle_deg": self.convergence_half_angle_deg,
            "efficiency": self.efficiency,
            "throat_length": self.throat_length,
            "contour_type": self.contour_type,
            "erosion": {
                "enabled": self.erosion.enabled,
                "coefficient_mm_s": self.erosion.coefficient_mm_s,
                "exponent": self.erosion.exponent,
            },
        }
