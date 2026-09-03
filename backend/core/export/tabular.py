"""CSV (full-resolution time series) and JSON (versioned design document) writers.

Section 7.3. The CSV is NOT downsampled. The JSON schema is versioned so a design
can be re-imported later; ``DESIGN_SCHEMA_VERSION`` is bumped on any breaking change.
"""

from __future__ import annotations

import csv
import io
import json

import numpy as np

from core.export.model import MotorExportData

DESIGN_SCHEMA_VERSION = 1

_CSV_COLUMNS = [
    ("time_s", "time_s"),
    ("chamber_pressure_bar", "chamber_pressure_bar"),
    ("chamber_pressure_no_erosion_bar", "chamber_pressure_no_erosion_bar"),
    ("thrust_n", "thrust_n"),
    ("burn_rate_mm_s", "burn_rate_mm_s"),
    ("kn", "kn"),
    ("burn_area_mm2", "burn_area_mm2"),
    ("throat_area_mm2", "throat_area_mm2"),
    ("port_area_mm2", "port_area_mm2"),
    ("mass_flow_kg_s", "mass_flow_kg_s"),
    ("cumulative_impulse_ns", "cumulative_impulse_ns"),
    ("propellant_mass_g", "propellant_mass_g"),
    ("web_mm", "web_mm"),
]


def render_csv(ballistics) -> str:
    """Full-resolution time series from a :class:`core.ballistics.BallisticsResult`."""
    cols = {
        "time_s": ballistics.time,
        "chamber_pressure_bar": ballistics.chamber_pressure / 1e5,
        "chamber_pressure_no_erosion_bar": ballistics.chamber_pressure_no_erosion / 1e5,
        "thrust_n": ballistics.thrust,
        "burn_rate_mm_s": ballistics.burn_rate * 1e3,
        "kn": ballistics.kn,
        "burn_area_mm2": ballistics.burn_area * 1e6,
        "throat_area_mm2": ballistics.throat_area * 1e6,
        "port_area_mm2": ballistics.port_area * 1e6,
        "mass_flow_kg_s": ballistics.mass_flow,
        "cumulative_impulse_ns": ballistics.cumulative_impulse,
        "propellant_mass_g": ballistics.propellant_mass * 1e3,
        "web_mm": ballistics.web * 1e3,
    }
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([name for name, _ in _CSV_COLUMNS])
    n = len(ballistics.time)
    for i in range(n):
        writer.writerow([f"{float(cols[key][i]):.6g}" for _, key in _CSV_COLUMNS])
    return buf.getvalue()


def render_json(data: MotorExportData) -> str:
    """The full design document + summary metrics, schema-versioned."""
    doc = {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "generated_by": "KNSB Motor Designer",
        "designation": data.designation,
        "display_name": data.display_name,
        "designer": data.designer,
        "date": data.date_iso,
        "propellant_name": data.propellant_name,
        "design": data.design_document,
        "summary": {
            "total_impulse_ns": data.total_impulse_ns,
            "average_thrust_n": data.average_thrust_n,
            "peak_thrust_n": data.peak_thrust_n,
            "burn_time_s": data.burn_time_s,
            "specific_impulse_s": data.specific_impulse_s,
            "propellant_mass_kg": data.propellant_mass_kg,
            "total_mass_kg": data.total_mass_kg,
            "throat_diameter_mm": data.throat_diameter_mm,
            "exit_diameter_mm": data.exit_diameter_mm,
        },
        "is_safe": data.is_safe,
        "warnings": data.warnings,
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)


def render_nozzle_contour_csv(nozzle, points: int = 60) -> str:
    """(x_mm, r_mm) contour of the nozzle flow path for CAD import (Section 7.3)."""
    import math

    r_t = nozzle.throat_diameter / 2.0
    r_e = nozzle.exit_diameter / 2.0
    conv = r_t * 3.0
    div = max(r_e - r_t, 1e-4) / math.tan(math.radians(nozzle.divergence_half_angle_deg))
    throat_len = nozzle.throat_length or 0.3 * r_t
    xs = np.linspace(0.0, conv + throat_len + div, points)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["x_mm", "r_mm"])
    for x in xs:
        if x < conv:
            r = r_t * 3.0 + (r_t - r_t * 3.0) * (x / conv)
        elif x < conv + throat_len:
            r = r_t
        else:
            r = r_t + (r_e - r_t) * ((x - conv - throat_len) / max(div, 1e-9))
        w.writerow([f"{x * 1e3:.4f}", f"{r * 1e3:.4f}"])
    return buf.getvalue()
