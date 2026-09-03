"""The bundle every export writer consumes.

Built once by ``services.export_service`` from an assembly + a ballistics result so
the ``.eng`` header mass, the drawing and the ``.rse`` mass/CG series all come from
one computation (acceptance criterion 11).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class MotorExportData:
    # identity
    designation: str                 # "J240"
    display_name: str                # "PARS-J240" (prefix + designation)
    manufacturer: str                # <=6 chars ideally; RASP field 7
    designer: str
    date_iso: str
    propellant_name: str

    # RASP header numbers
    case_diameter_mm: float
    case_length_mm: float
    delay: str                       # "P" plugged for research motors
    propellant_mass_kg: float
    total_mass_kg: float

    # curves (full resolution, SI)
    time_s: np.ndarray
    thrust_n: np.ndarray
    total_mass_series_kg: np.ndarray  # motor mass vs time (for .rse <eng-data m=...>)
    cg_series_mm: np.ndarray          # CG from the forward face vs time

    # informational metrics
    total_impulse_ns: float
    average_thrust_n: float
    peak_thrust_n: float
    burn_time_s: float
    specific_impulse_s: float
    throat_diameter_mm: float
    exit_diameter_mm: float
    isp_s: float = 0.0

    # safety
    is_safe: bool = True
    warnings: list[dict] = field(default_factory=list)

    # the full design document (for JSON export / re-import)
    design_document: dict = field(default_factory=dict)

    def blocking_codes(self) -> list[str]:
        return [w["code"] for w in self.warnings if w.get("level") == "danger"]
