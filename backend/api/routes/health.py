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
        })
    return {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "propellants": props,
        "grains": available_grains(),
        "case_materials": [
            {"id": m.id, "name_tr": m.name_tr, "name_en": m.name_en,
             "tensile_strength": m.tensile_strength, "max_service_temp": m.max_service_temp,
             "notes_key": m.notes_key}
            for m in case_materials().values()
        ],
        "liner_materials": [
            {"id": m.id, "name_tr": m.name_tr, "name_en": m.name_en,
             "min_thickness": m.min_thickness, "notes_key": m.notes_key}
            for m in liner_materials().values()
        ],
        "warning_codes": [
            {"code": c, "level": level, "i18n_key": f"info.warning.{c}"}
            for c, level in warning_catalogue().items()
        ],
        "all_warning_codes": list(ALL_WARNING_CODES),
        "print_methods": ["fdm", "sls", "machined"],
    }
