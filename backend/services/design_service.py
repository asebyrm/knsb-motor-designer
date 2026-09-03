"""Turn a design document (dict) into core objects, and back.

The design document is the single serialisable representation of a motor - it is what
the frontend sends, what JSON export writes and what the mission solver produces.
``DESIGN_SCHEMA_VERSION`` tracks breaking changes.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from core.assembly import BulkheadSpec, CaseSpec, LinerSpec, MotorAssembly
from core.grains.base import GrainGeometry, make_grain
from core.materials import PrintMethod, load_case_material, load_liner_material
from core.nozzle import ErosionParams, Nozzle
from core.propellant import Propellant, load_propellant

DESIGN_SCHEMA_VERSION = 1

_GRAIN_LENGTH_KEY = {
    "bates": "segment_length",
    "tubular": "length",
    "endburner": "length",
}


@dataclass
class MotorContext:
    """Everything the analysis + export layers need for one motor."""

    design: dict
    grain: GrainGeometry
    propellant: Propellant
    nozzle: Nozzle
    assembly: MotorAssembly
    meop_pa: float | None
    print_method: PrintMethod
    ambient_pressure: float
    bolt_diameter: float
    bolt_shear_strength: float
    name: str
    prefix: str
    designer: str

    # metadata that flows to exports
    extra: dict = field(default_factory=dict)


def _num(d: dict, key: str, default: float) -> float:
    v = d.get(key, default)
    return float(v) if v is not None else float(default)


def build_propellant(spec: dict) -> Propellant:
    """Load a propellant YAML and apply user calibration overrides (Section 14)."""
    base = load_propellant(spec.get("id", "knsb"))
    overrides = {}
    if "density_factor" in spec and spec["density_factor"] is not None:
        overrides["density_factor"] = float(spec["density_factor"])
    if "c_star_efficiency" in spec and spec["c_star_efficiency"] is not None:
        overrides["c_star_efficiency"] = float(spec["c_star_efficiency"])
    return dataclasses.replace(base, **overrides) if overrides else base


def build_grain(spec: dict) -> GrainGeometry:
    gtype = spec.get("type", "bates")
    length_key = _GRAIN_LENGTH_KEY.get(gtype, "segment_length")
    kwargs: dict = {"outer_diameter": _num(spec, "outer_diameter", 0.05)}
    if gtype != "endburner":
        kwargs["core_diameter"] = _num(spec, "core_diameter", 0.02)
    kwargs[length_key] = _num(spec, length_key, spec.get("segment_length", 0.1))
    if gtype == "bates":
        kwargs["segment_count"] = int(spec.get("segment_count", 1))
        kwargs["segment_spacing"] = _num(spec, "segment_spacing", 0.0)
    elif gtype == "tubular":
        kwargs["segment_count"] = int(spec.get("segment_count", 1))
    return make_grain(gtype, **kwargs)


def build_nozzle(spec: dict) -> Nozzle:
    ero = spec.get("erosion", {}) or {}
    return Nozzle(
        throat_diameter=_num(spec, "throat_diameter", 0.012),
        expansion_ratio=_num(spec, "expansion_ratio", 4.0),
        divergence_half_angle_deg=_num(spec, "divergence_half_angle_deg", 15.0),
        convergence_half_angle_deg=_num(spec, "convergence_half_angle_deg", 45.0),
        efficiency=_num(spec, "efficiency", 0.95),
        throat_length=_num(spec, "throat_length", 0.0),
        erosion=ErosionParams(
            enabled=bool(ero.get("enabled", False)),
            coefficient_mm_s=_num(ero, "coefficient_mm_s", 0.05),
            exponent=_num(ero, "exponent", 0.8),
        ),
    )


def build_motor(design: dict) -> MotorContext:
    """Assemble a :class:`MotorContext` from a design document."""
    grain = build_grain(design.get("grain", {}))
    propellant = build_propellant(design.get("propellant", {}))
    nozzle = build_nozzle(design.get("nozzle", {}))

    case_spec = design.get("case", {})
    case_mat = load_case_material(case_spec.get("material_id", "pa12"))
    liner_spec = design.get("liner")
    liner = None
    if liner_spec and liner_spec.get("material_id"):
        liner = LinerSpec(load_liner_material(liner_spec["material_id"]),
                          _num(liner_spec, "thickness", 0.003))
    bh_spec = design.get("bulkhead", {})
    bh_mat = load_case_material(bh_spec.get("material_id", case_spec.get("material_id", "pa12")))
    asm_spec = design.get("assembly", {})

    assembly = MotorAssembly(
        grain=grain, propellant=propellant, nozzle=nozzle,
        case=CaseSpec(
            case_mat,
            _num(case_spec, "inner_diameter", grain.outer_diameter() + 0.006),
            _num(case_spec, "wall_thickness", 0.004),
            case_spec.get("length"),
        ),
        bulkhead=BulkheadSpec(bh_mat, _num(bh_spec, "thickness", 0.010)),
        liner=liner,
        forward_gap=_num(asm_spec, "forward_gap", 0.002),
        aft_gap=_num(asm_spec, "aft_gap", 0.002),
    )

    env = design.get("environment", {})
    bolt = design.get("bolt", {})
    meop_bar = design.get("meop_bar")
    pm = case_spec.get("print_method", "sls")

    return MotorContext(
        design=design,
        grain=grain,
        propellant=propellant,
        nozzle=nozzle,
        assembly=assembly,
        meop_pa=float(meop_bar) * 1e5 if meop_bar is not None else None,
        print_method=PrintMethod(pm) if pm in PrintMethod._value2member_map_ else PrintMethod.SLS,
        ambient_pressure=_num(env, "ambient_pressure", 101_325.0),
        bolt_diameter=_num(bolt, "diameter", 0.004),
        bolt_shear_strength=_num(bolt, "shear_strength", 200e6),
        name=design.get("name", "Motor"),
        prefix=design.get("prefix", "PARS"),
        designer=design.get("designer", "anonymous"),
    )


def motor_to_design(ctx: MotorContext) -> dict:
    """Round-trip: serialise a context's core objects back to a design document."""
    d = {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "name": ctx.name,
        "prefix": ctx.prefix,
        "designer": ctx.designer,
        "propellant": {
            "id": ctx.propellant.id,
            "density_factor": ctx.propellant.density_factor,
            "c_star_efficiency": ctx.propellant.c_star_efficiency,
        },
        "grain": ctx.grain.to_dict(),
        "nozzle": ctx.nozzle.to_dict(),
        "case": {
            "material_id": ctx.assembly.case.material.id,
            "inner_diameter": ctx.assembly.case.inner_diameter,
            "wall_thickness": ctx.assembly.case.wall_thickness,
            "length": ctx.assembly.case.length,
            "print_method": ctx.print_method.value,
        },
        "bulkhead": {
            "material_id": ctx.assembly.bulkhead.material.id,
            "thickness": ctx.assembly.bulkhead.thickness,
        },
        "environment": {"ambient_pressure": ctx.ambient_pressure},
        "meop_bar": ctx.meop_pa / 1e5 if ctx.meop_pa else None,
    }
    if ctx.assembly.liner:
        d["liner"] = {
            "material_id": ctx.assembly.liner.material.id,
            "thickness": ctx.assembly.liner.thickness,
        }
    return d
