"""Case and liner material libraries loaded from YAML (Section 5.6, 5.7).

Adding a material = a YAML entry, never a code change.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml

_DIR = Path(__file__).resolve().parent.parent / "data" / "materials"


class PrintMethod(StrEnum):
    FDM = "fdm"
    SLS = "sls"
    MACHINED = "machined"


_PRINT_FACTORS = {PrintMethod.FDM: 0.5, PrintMethod.SLS: 0.9, PrintMethod.MACHINED: 1.0}


@dataclass(frozen=True)
class CaseMaterial:
    id: str
    name_en: str
    name_tr: str
    tensile_strength: float          # Pa
    yield_strength: float            # Pa
    print_direction_factor: float    # material baseline knock-down
    elastic_modulus: float           # Pa
    density: float                   # kg/m^3
    thermal_conductivity: float      # W/(m*K)
    specific_heat: float             # J/(kg*K)
    glass_transition: float          # K
    max_service_temp: float          # K
    notes_key: str

    @property
    def thermal_diffusivity(self) -> float:
        """alpha = k / (rho * c_p) [m^2/s]."""
        return self.thermal_conductivity / (self.density * self.specific_heat)

    def strength_factor(self, method: PrintMethod | None = None) -> float:
        """Effective knock-down: the print method's factor if given, else the baseline."""
        if method is None:
            return self.print_direction_factor
        return _PRINT_FACTORS[method]

    def allowable_stress(self, method: PrintMethod | None = None) -> float:
        """sigma_allow = tensile_strength * strength_factor [Pa] (Section 5.6)."""
        return self.tensile_strength * self.strength_factor(method)

    @classmethod
    def from_dict(cls, d: dict) -> CaseMaterial:
        return cls(
            id=d["id"],
            name_en=d["name_en"],
            name_tr=d["name_tr"],
            tensile_strength=float(d["tensile_strength"]),
            yield_strength=float(d.get("yield_strength", 0.9 * float(d["tensile_strength"]))),
            print_direction_factor=float(d["print_direction_factor"]),
            elastic_modulus=float(d.get("elastic_modulus", 2.0e9)),
            density=float(d["density"]),
            thermal_conductivity=float(d["thermal_conductivity"]),
            specific_heat=float(d["specific_heat"]),
            glass_transition=float(d["glass_transition"]),
            max_service_temp=float(d["max_service_temp"]),
            notes_key=d.get("notes_key", f"material.{d['id']}.notes"),
        )


@dataclass(frozen=True)
class LinerMaterial:
    id: str
    name_en: str
    name_tr: str
    ablation_rate: float             # m/s
    min_thickness: float             # m
    thermal_conductivity: float      # W/(m*K)
    density: float                   # kg/m^3
    specific_heat: float             # J/(kg*K)
    max_interface_temp: float        # K
    notes_key: str

    @property
    def thermal_diffusivity(self) -> float:
        return self.thermal_conductivity / (self.density * self.specific_heat)

    def recommended_thickness(self, burn_time: float) -> float:
        """min_thickness plus an allowance for total ablation over the burn (Section 5.7).

        Burns longer than 3 s get the ablation allowance scaled up 1.5x.
        """
        factor = 1.5 if burn_time > 3.0 else 1.0
        return self.min_thickness + factor * self.ablation_rate * burn_time

    @classmethod
    def from_dict(cls, d: dict) -> LinerMaterial:
        return cls(
            id=d["id"],
            name_en=d["name_en"],
            name_tr=d["name_tr"],
            ablation_rate=float(d["ablation_rate"]),
            min_thickness=float(d["min_thickness"]),
            thermal_conductivity=float(d["thermal_conductivity"]),
            density=float(d["density"]),
            specific_heat=float(d["specific_heat"]),
            max_interface_temp=float(d["max_interface_temp"]),
            notes_key=d.get("notes_key", f"liner.{d['id']}.notes"),
        )


def _load(path: Path, key: str, cls):
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return {item["id"]: cls.from_dict(item) for item in data[key]}


_CASE_CACHE: dict[str, CaseMaterial] | None = None
_LINER_CACHE: dict[str, LinerMaterial] | None = None


def case_materials() -> dict[str, CaseMaterial]:
    global _CASE_CACHE
    if _CASE_CACHE is None:
        _CASE_CACHE = _load(_DIR / "case_materials.yaml", "materials", CaseMaterial)
    return _CASE_CACHE


def liner_materials() -> dict[str, LinerMaterial]:
    global _LINER_CACHE
    if _LINER_CACHE is None:
        _LINER_CACHE = _load(_DIR / "liner_materials.yaml", "liners", LinerMaterial)
    return _LINER_CACHE


def load_case_material(identifier: str) -> CaseMaterial:
    try:
        return case_materials()[identifier]
    except KeyError:
        raise FileNotFoundError(f"no case material {identifier!r}") from None


def load_liner_material(identifier: str) -> LinerMaterial:
    try:
        return liner_materials()[identifier]
    except KeyError:
        raise FileNotFoundError(f"no liner material {identifier!r}") from None
