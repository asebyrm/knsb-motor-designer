"""Health + catalogue endpoints (Section 3, 9, 11)."""

from __future__ import annotations

from fastapi import APIRouter

from core.grains.base import available_grains
from core.materials import case_materials, liner_materials
from core.propellant import available_propellants, load_propellant
from core.warnings import ALL_WARNING_CODES, warning_catalogue
from services.design_service import DESIGN_SCHEMA_VERSION

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/catalog")
def catalog() -> dict:
    """Everything the frontend needs to populate dropdowns and validate tooltips."""
    props = []
    # KNSB is the v1 primary fuel — list it first, then the rest alphabetically
    ordered = sorted(available_propellants(), key=lambda pid: (pid != "knsb", pid))
    for pid in ordered:
        p = load_propellant(pid)
        props.append({
            "id": p.id, "file": pid, "name_tr": p.name_tr, "name_en": p.name_en,
            "composition": p.composition, "density_ideal": p.density_ideal,
            "gamma": p.gamma, "flame_temperature": p.flame_temperature,
            # full property set (Section 5.1), for the Materials tab - density and
            # c* also have a user-adjustable factor (design.propellant.density_factor
            # / c_star_efficiency, "Static-fire calibration"), which this catalog
            # entry does not carry - only the catalog's own reference values do
            "properties": {
                "density_ideal": p.density_ideal, "c_star_ideal": p.c_star_ideal,
                "gamma": p.gamma, "flame_temperature": p.flame_temperature,
                "molar_mass": p.molar_mass,
            },
            "burn_rate_ranges": [
                {"p_min_mpa": r.p_min_mpa, "p_max_mpa": r.p_max_mpa, "a": r.a, "n": r.n}
                for r in p.burn_rate_ranges
            ],
        })
    return {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "propellants": props,
        "grains": available_grains(),
        "case_materials": [
            {"id": m.id, "name_tr": m.name_tr, "name_en": m.name_en,
             "tensile_strength": m.tensile_strength, "max_service_temp": m.max_service_temp,
             "notes_key": m.notes_key,
             # full property set (Section 5.6) - lets the frontend show/edit every
             # number that actually feeds the structural/thermal analysis, not just
             # the two headline figures above
             "properties": {
                 "tensile_strength": m.tensile_strength, "yield_strength": m.yield_strength,
                 "print_direction_factor": m.print_direction_factor,
                 "elastic_modulus": m.elastic_modulus, "density": m.density,
                 "thermal_conductivity": m.thermal_conductivity,
                 "specific_heat": m.specific_heat, "glass_transition": m.glass_transition,
                 "max_service_temp": m.max_service_temp,
             }}
            for m in case_materials().values()
        ],
        "liner_materials": [
            {"id": m.id, "name_tr": m.name_tr, "name_en": m.name_en,
             "min_thickness": m.min_thickness, "notes_key": m.notes_key,
             "properties": {
                 "ablation_rate": m.ablation_rate, "min_thickness": m.min_thickness,
                 "thermal_conductivity": m.thermal_conductivity, "density": m.density,
                 "specific_heat": m.specific_heat, "max_interface_temp": m.max_interface_temp,
             }}
            for m in liner_materials().values()
        ],
        "warning_codes": [
            {"code": c, "level": level, "i18n_key": f"info.warning.{c}"}
            for c, level in warning_catalogue().items()
        ],
        "all_warning_codes": list(ALL_WARNING_CODES),
        "print_methods": ["fdm", "sls", "machined"],
    }
