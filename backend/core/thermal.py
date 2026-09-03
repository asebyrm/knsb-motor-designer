"""Thermal analysis and liner sizing (Section 5.7).

KNSB flame temperature is ~1600 K; no thermoplastic survives that unprotected. When
the case is a structural element a liner is **mandatory** - a design without one is
UNSAFE (``WARN_NO_LINER``).

Case inner-surface temperature after the burn is estimated with the semi-infinite
solid solution, the liner inner face held at the flame temperature::

    T(x, t) = T_i + (T_s - T_i) * erfc( x / (2 * sqrt(alpha * t)) )

with ``x`` the liner thickness, ``t`` the burn time and ``alpha`` the liner thermal
diffusivity. If the estimate exceeds the case material's ``max_service_temp`` the
design trips ``WARN_THERMAL_LIMIT``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.assembly import MotorAssembly
from core.warnings import Warning, make

_LONG_BURN = 3.0  # s


@dataclass
class ThermalResult:
    flame_temperature: float          # K
    burn_time: float                  # s
    liner_present: bool
    liner_thickness: float            # m (0 if none)
    recommended_liner_thickness: float  # m
    ablation_depth: float             # m consumed over the burn
    case_inner_surface_temp: float    # K estimate
    case_max_service_temp: float      # K
    is_safe: bool
    warnings: list[Warning]

    def to_dict(self) -> dict:
        return {
            "flame_temperature_k": self.flame_temperature,
            "burn_time_s": self.burn_time,
            "liner_present": self.liner_present,
            "liner_thickness_mm": self.liner_thickness * 1e3,
            "recommended_liner_thickness_mm": self.recommended_liner_thickness * 1e3,
            "ablation_depth_mm": self.ablation_depth * 1e3,
            "case_inner_surface_temp_k": self.case_inner_surface_temp,
            "case_max_service_temp_k": self.case_max_service_temp,
            "is_safe": self.is_safe,
            "warnings": [w.to_dict() for w in self.warnings],
        }


def semi_infinite_surface_temperature(
    depth: float, time: float, diffusivity: float, t_surface: float, t_initial: float
) -> float:
    """T at ``depth`` into a semi-infinite solid after ``time`` (Section 5.7 formula)."""
    if time <= 0 or diffusivity <= 0:
        return t_initial
    arg = depth / (2.0 * math.sqrt(diffusivity * time))
    return t_initial + (t_surface - t_initial) * math.erfc(arg)


def analyse_thermal(
    assembly: MotorAssembly,
    flame_temperature: float,
    burn_time: float,
    *,
    ambient_temp: float = 293.15,
) -> ThermalResult:
    case_mat = assembly.case.material
    liner = assembly.liner

    warnings: list[Warning] = []

    if liner is None or liner.thickness <= 0:
        warnings.append(make("WARN_NO_LINER", flame_temp_k=round(flame_temperature)))
        return ThermalResult(
            flame_temperature=flame_temperature,
            burn_time=burn_time,
            liner_present=False,
            liner_thickness=0.0,
            recommended_liner_thickness=0.0,
            ablation_depth=0.0,
            case_inner_surface_temp=flame_temperature,
            case_max_service_temp=case_mat.max_service_temp,
            is_safe=False,
            warnings=warnings,
        )

    lm = liner.material
    ablation_depth = lm.ablation_rate * burn_time
    remaining = liner.thickness - ablation_depth

    # temperature reaches the case through the *un-ablated* liner thickness
    t_case = semi_infinite_surface_temperature(
        max(remaining, 0.0), burn_time, lm.thermal_diffusivity,
        flame_temperature, ambient_temp,
    )

    recommended = lm.recommended_thickness(burn_time)

    if remaining <= 0.0:
        warnings.append(make("WARN_THERMAL_LIMIT",
                             reason="liner_burnthrough",
                             ablation_mm=round(ablation_depth * 1e3, 2),
                             liner_mm=round(liner.thickness * 1e3, 2)))
    if t_case > case_mat.max_service_temp:
        warnings.append(make("WARN_THERMAL_LIMIT",
                             t_case_k=round(t_case),
                             t_max_k=round(case_mat.max_service_temp)))
    if liner.thickness < recommended:
        warnings.append(make("WARN_LINER_THIN",
                             liner_mm=round(liner.thickness * 1e3, 2),
                             recommended_mm=round(recommended * 1e3, 2)))
    if burn_time > _LONG_BURN:
        warnings.append(make("WARN_LONG_BURN_THERMAL", burn_time_s=round(burn_time, 2)))

    is_safe = remaining > 0.0 and t_case <= case_mat.max_service_temp
    return ThermalResult(
        flame_temperature=flame_temperature,
        burn_time=burn_time,
        liner_present=True,
        liner_thickness=liner.thickness,
        recommended_liner_thickness=recommended,
        ablation_depth=ablation_depth,
        case_inner_surface_temp=t_case,
        case_max_service_temp=case_mat.max_service_temp,
        is_safe=is_safe,
        warnings=warnings,
    )
