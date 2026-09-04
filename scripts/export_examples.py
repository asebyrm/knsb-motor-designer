#!/usr/bin/env python3
"""Write the bundled example motors to ./outputs as .eng / .rse / .pdf.

Use the .eng files to verify OpenRocket / RockSim load them (acceptance criterion 3).
Run from the repo root:  .venv/bin/python scripts/export_examples.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "backend"))

from core.examples import ALL_EXAMPLES
from services.design_service import build_motor, motor_to_design
from services.export_service import (
    build_export_data,
    export_eng,
    export_pdf,
    export_rse,
)

_OUT = _ROOT / "outputs"
_OUT.mkdir(exist_ok=True)


def _design_for(key: str, ex) -> dict:
    ref = key == "reference"
    return {
        "name": ex.name,
        "prefix": "PARS",
        "designer": "PARS Rocketry Team",
        "propellant": {"id": ex.propellant.id},
        "grain": ex.grain.to_dict(),
        "nozzle": ex.nozzle.to_dict(),
        "case": {
            "material_id": "al6061_t6" if ref else "pa12",
            "inner_diameter": ex.grain.outer_diameter() + 0.006,
            "wall_thickness": 0.005,
            "print_method": "machined" if ref else "sls",
        },
        "liner": None if key == "unsafe" else {"material_id": "kraft_phenolic", "thickness": 0.003},
        "bulkhead": {"material_id": "al6061_t6" if ref else "pa12", "thickness": 0.01},
        "meop_bar": (ex.meop_pa or 4e6) / 1e5,
    }


def main() -> None:
    for key, factory in ALL_EXAMPLES.items():
        ex = factory()
        design = motor_to_design(build_motor(_design_for(key, ex)))
        data, _ballistics, _ctx = build_export_data(design)
        base = _OUT / data.display_name
        base.with_suffix(".eng").write_text(export_eng(design, accept_risk=True))
        base.with_suffix(".rse").write_text(export_rse(design, accept_risk=True))
        base.with_suffix(".pdf").write_bytes(export_pdf(design, locale="en"))
        print(f"  wrote {base.name}.{{eng,rse,pdf}}  ({data.designation})")


if __name__ == "__main__":
    main()
