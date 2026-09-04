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
    "star": "length",
    "wagon_wheel": "length",
    "rod_tube": "length",
}
_MULTI_SEGMENT_TYPES = {"bates", "tubular", "star", "wagon_wheel", "rod_tube"}


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


_MATERIAL_LABEL_FIELDS = {"id", "name_en", "name_tr", "notes_key"}


def apply_material_overrides(mat, overrides: dict | None):
    """User-supplied per-design property overrides for a catalog material (Section
    5.6/5.7) - the same idea as the propellant's density_factor/c_star_efficiency
    calibration, generalised: "my sample of PLA is denser than the catalog value"
    should not require editing the shared YAML. Only numeric, non-identity fields
    of the material's own dataclass can be overridden; anything else is ignored
    rather than raising, so a stray/unknown key in the request never 500s.
    """
    if not overrides:
        return mat
    valid = {f.name for f in dataclasses.fields(mat)} - _MATERIAL_LABEL_FIELDS
    patch = {k: float(v) for k, v in overrides.items()
             if k in valid and isinstance(v, (int, float)) and v is not None}
    return dataclasses.replace(mat, **patch) if patch else mat


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
    if gtype in _MULTI_SEGMENT_TYPES:
        kwargs["segment_count"] = int(spec.get("segment_count", 1))
        kwargs["segment_spacing"] = _num(spec, "segment_spacing", 0.0)
    if gtype in ("star", "wagon_wheel", "rod_tube"):
        kwargs["point_diameter"] = _num(spec, "point_diameter", 0.03)
    if gtype in ("star", "wagon_wheel"):
        kwargs["n_points"] = int(spec.get("n_points", 6 if gtype == "star" else 4))
    return make_grain(gtype, **kwargs)


def build_nozzle(spec: dict) -> Nozzle:
    ero = spec.get("erosion", {}) or {}
    contour = spec.get("contour_type", "conic")
    return Nozzle(
        throat_diameter=_num(spec, "throat_diameter", 0.012),
        expansion_ratio=_num(spec, "expansion_ratio", 4.0),
        divergence_half_angle_deg=_num(spec, "divergence_half_angle_deg", 15.0),
        convergence_half_angle_deg=_num(spec, "convergence_half_angle_deg", 45.0),
        efficiency=_num(spec, "efficiency", 0.95),
        throat_length=_num(spec, "throat_length", 0.0),
        contour_type=contour if contour in ("conic", "bell") else "conic",
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
    case_mat = apply_material_overrides(
        load_case_material(case_spec.get("material_id", "pa12")),
        case_spec.get("material_overrides"))
    liner_spec = design.get("liner")
    liner = None
    if liner_spec and liner_spec.get("material_id"):
        liner_mat = apply_material_overrides(
            load_liner_material(liner_spec["material_id"]), liner_spec.get("material_overrides"))
        liner = LinerSpec(liner_mat, _num(liner_spec, "thickness", 0.003))
    bh_spec = design.get("bulkhead", {})
    bh_mat = apply_material_overrides(
        load_case_material(bh_spec.get("material_id", case_spec.get("material_id", "pa12"))),
        bh_spec.get("material_overrides"))
    asm_spec = design.get("assembly", {})

    # the nozzle is drawn and treated as part of the case by default - same
    # material - but can be given its own (Section 5.3 / 10.1)
    noz_spec = design.get("nozzle", {})
    noz_mat = apply_material_overrides(
        load_case_material(noz_spec.get("material_id") or case_spec.get("material_id", "pa12")),
        noz_spec.get("material_overrides"))

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
        nozzle_material_density=noz_mat.density,
        nozzle_material_id=noz_mat.id,
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
    """Round-trip: serialise a context's core objects back to a design document.

    Material property overrides are not carried on the core dataclasses (they are
    baked into the loaded material's numbers), so they are forwarded straight from
    the original request (``ctx.design``) rather than reconstructed.
    """
    orig = ctx.design or {}

    def overrides_of(section: str) -> dict | None:
        return (orig.get(section) or {}).get("material_overrides")

    nozzle_dict = ctx.nozzle.to_dict()
    nozzle_dict["material_id"] = ctx.assembly.nozzle_material_id
    if overrides_of("nozzle"):
        nozzle_dict["material_overrides"] = overrides_of("nozzle")

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
        "nozzle": nozzle_dict,
        "case": {
            "material_id": ctx.assembly.case.material.id,
            "inner_diameter": ctx.assembly.case.inner_diameter,
            "wall_thickness": ctx.assembly.case.wall_thickness,
            "length": ctx.assembly.case.length,
            "print_method": ctx.print_method.value,
            **({"material_overrides": overrides_of("case")} if overrides_of("case") else {}),
        },
        "bulkhead": {
            "material_id": ctx.assembly.bulkhead.material.id,
            "thickness": ctx.assembly.bulkhead.thickness,
            **({"material_overrides": overrides_of("bulkhead")}
               if overrides_of("bulkhead") else {}),
        },
        "environment": {"ambient_pressure": ctx.ambient_pressure},
        "meop_bar": ctx.meop_pa / 1e5 if ctx.meop_pa else None,
    }
    if ctx.assembly.liner:
        d["liner"] = {
            "material_id": ctx.assembly.liner.material.id,
            "thickness": ctx.assembly.liner.thickness,
            **({"material_overrides": overrides_of("liner")} if overrides_of("liner") else {}),
        }
    return d
