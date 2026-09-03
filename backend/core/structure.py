"""Structural analysis of a 3D-printed (or metal) chamber - the key safety feature.

Thin wall (t / r_i <= 0.1), cylindrical case, internal pressure p (Section 5.6)::

    sigma_hoop  = p * r_i / t
    sigma_axial = p * r_i / (2 t)
    sigma_vm    = sqrt(hoop^2 - hoop*axial + axial^2)
    sigma_allow = tensile_strength * strength_factor      # print-direction knock-down
    FoS         = sigma_allow / sigma_vm

Thick wall (t / r_i > 0.1): Lame, evaluated at the bore where hoop stress peaks::

    sigma_hoop  =  p (r_o^2 + r_i^2) / (r_o^2 - r_i^2)
    sigma_radial = -p
    sigma_axial =  p r_i^2 / (r_o^2 - r_i^2)

Rules: minimum FoS is 2.0. Below that the design is UNSAFE and export is locked
(Section 5.6). The pressure used is always the **erosionless peak** (MEOP), never the
design-point pressure.

Bulkhead / nozzle retainer: axial blow-out force ``F_axial = p * pi * r_i^2``; the
fasteners must carry ``F_axial`` with the target FoS in shear.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.assembly import MotorAssembly
from core.materials import CaseMaterial, PrintMethod
from core.warnings import Warning, make

MIN_FOS = 2.0
_THIN_WALL_LIMIT = 0.10


@dataclass
class WallResult:
    model: str                 # "thin" | "thick"
    sigma_hoop: float          # Pa
    sigma_axial: float         # Pa
    sigma_vm: float            # Pa
    sigma_allow: float         # Pa
    fos: float


@dataclass
class FastenerResult:
    axial_force: float         # N
    bolt_diameter: float       # m
    bolt_shear_strength: float  # Pa
    target_fos: float
    min_count: int


@dataclass
class StructureResult:
    meop_pa: float
    wall: WallResult
    bulkhead_fasteners: FastenerResult
    nozzle_fasteners: FastenerResult
    is_safe: bool
    warnings: list[Warning]

    def to_dict(self) -> dict:
        return {
            "meop_bar": self.meop_pa / 1e5,
            "wall_model": self.wall.model,
            "sigma_hoop_mpa": self.wall.sigma_hoop / 1e6,
            "sigma_vm_mpa": self.wall.sigma_vm / 1e6,
            "sigma_allow_mpa": self.wall.sigma_allow / 1e6,
            "fos": self.wall.fos,
            "is_safe": self.is_safe,
            "bulkhead_min_bolts": self.bulkhead_fasteners.min_count,
            "nozzle_min_bolts": self.nozzle_fasteners.min_count,
            "warnings": [w.to_dict() for w in self.warnings],
        }


def analyse_wall(
    p_pa: float,
    inner_radius: float,
    wall_thickness: float,
    material: CaseMaterial,
    print_method: PrintMethod | None = None,
) -> WallResult:
    """Hoop/axial/Von-Mises stress and FoS for the cylindrical wall."""
    r_i, t = inner_radius, wall_thickness
    sigma_allow = material.allowable_stress(print_method)

    if t / r_i <= _THIN_WALL_LIMIT:
        hoop = p_pa * r_i / t
        axial = p_pa * r_i / (2.0 * t)
        model = "thin"
    else:
        r_o = r_i + t
        denom = r_o**2 - r_i**2
        hoop = p_pa * (r_o**2 + r_i**2) / denom
        axial = p_pa * r_i**2 / denom
        model = "thick"

    # Von Mises with radial stress ~ -p at the bore (thick) or ~0 (thin, negligible)
    if model == "thin":
        vm = math.sqrt(hoop**2 - hoop * axial + axial**2)
    else:
        radial = -p_pa
        vm = math.sqrt(0.5 * ((hoop - axial) ** 2 + (axial - radial) ** 2 + (radial - hoop) ** 2))

    fos = sigma_allow / vm if vm > 0 else math.inf
    return WallResult(model, hoop, axial, vm, sigma_allow, fos)


def size_fasteners(
    p_pa: float,
    inner_radius: float,
    *,
    bolt_diameter: float = 0.004,
    bolt_shear_strength: float = 200e6,
    target_fos: float = MIN_FOS,
) -> FastenerResult:
    """Minimum number of shear bolts to retain a closure against blow-out.

    ``F_axial = p * pi * r_i^2``; each bolt carries ``tau_allow * pi d^2 / 4`` in
    single shear. Default ``bolt_shear_strength`` ~ 200 MPa (class-4.8 steel, ~0.6 Sy).
    """
    f_axial = p_pa * math.pi * inner_radius**2
    per_bolt = bolt_shear_strength * math.pi * bolt_diameter**2 / 4.0
    min_count = max(2, math.ceil(f_axial * target_fos / per_bolt))
    return FastenerResult(f_axial, bolt_diameter, bolt_shear_strength, target_fos, min_count)


def analyse_structure(
    assembly: MotorAssembly,
    meop_pa: float,
    *,
    print_method: PrintMethod | None = None,
    bolt_diameter: float = 0.004,
    bolt_shear_strength: float = 200e6,
    min_fos: float = MIN_FOS,
) -> StructureResult:
    """Full structural check at MEOP (the erosionless peak pressure)."""
    r_i = assembly.case.inner_diameter / 2.0
    t = assembly.case.wall_thickness
    wall = analyse_wall(meop_pa, r_i, t, assembly.case.material, print_method)

    bulkhead = size_fasteners(meop_pa, r_i, bolt_diameter=bolt_diameter,
                              bolt_shear_strength=bolt_shear_strength, target_fos=min_fos)
    nozzle = size_fasteners(meop_pa, r_i, bolt_diameter=bolt_diameter,
                            bolt_shear_strength=bolt_shear_strength, target_fos=min_fos)

    warnings: list[Warning] = []
    if wall.fos < min_fos:
        warnings.append(make("WARN_LOW_FOS", fos=round(wall.fos, 2), required=min_fos))
    elif wall.fos < 1.5 * min_fos:
        warnings.append(make("WARN_MARGINAL_FOS", fos=round(wall.fos, 2), required=min_fos))

    if wall.model == "thick":
        warnings.append(make("WARN_THICK_WALL_MODEL",
                             t_over_ri=round(t / r_i, 3)))

    if assembly.case.material.strength_factor(print_method) < 0.6:
        warnings.append(make("WARN_PRINT_DIRECTION_WEAK",
                             factor=round(assembly.case.material.strength_factor(print_method), 2)))

    if max(bulkhead.min_count, nozzle.min_count) > 12:
        warnings.append(make("WARN_BULKHEAD_FASTENERS",
                             bulkhead=bulkhead.min_count, nozzle=nozzle.min_count))

    is_safe = wall.fos >= min_fos
    return StructureResult(meop_pa, wall, bulkhead, nozzle, is_safe, warnings)
