"""RASP ``.eng`` writer and parser (thrustcurve.org spec, Section 7.1).

Hard rules (OpenRocket rejects the file silently otherwise):

* header line = 7 space-separated fields
  ``name  dia_mm  len_mm  delays  prop_kg  total_kg  manufacturer``
* an implicit ``(0, 0)`` start point - never written
* the last data point's thrust is **exactly 0** and defines the burn time
* no interior point has thrust 0
* time strictly increasing, never negative
* at most 32 data points
* file ends with a single ``;`` line

Downsampling keeps the ignition ramp, the peak and the tail-off, and the
downsampled total impulse stays within 1 % of the full-resolution impulse
(Section 13.2 - enforced by :func:`_downsample_for_eng` and its test).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.branding import ATTRIBUTION_LINE, DISCLAIMER_SHORT
from core.export.model import MotorExportData
from core.sampling import downsample_curve

_MAX_POINTS = 32
_MIN_INTERIOR_THRUST = 1e-3  # N - clamp so no interior point is exactly zero


def _downsample_for_eng(time: np.ndarray, thrust: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """<=32 points, ending at exactly zero, impulse within 1 %."""
    # drop a leading t == 0 sample (the (0,0) point is implicit)
    if time.size and time[0] <= 0.0:
        time, thrust = time[1:], thrust[1:]

    t_ds, f_ds, _ = downsample_curve(time, thrust, _MAX_POINTS, area_tol=0.008)

    f_ds = np.where((f_ds < _MIN_INTERIOR_THRUST) & (np.arange(f_ds.size) < f_ds.size - 1),
                    _MIN_INTERIOR_THRUST, f_ds)
    # force the final point to zero thrust; keep its time as the burn end
    f_ds = f_ds.copy()
    f_ds[-1] = 0.0
    if t_ds[-1] <= t_ds[-2]:
        t_ds = t_ds.copy()
        t_ds[-1] = t_ds[-2] + 1e-3
    return t_ds, f_ds


def render_eng(data: MotorExportData) -> str:
    """Return the full ``.eng`` file text."""
    t_ds, f_ds = _downsample_for_eng(np.asarray(data.time_s), np.asarray(data.thrust_n))

    header = " ".join([
        data.display_name.replace(" ", "-"),
        f"{data.case_diameter_mm:.0f}",
        f"{data.case_length_mm:.0f}",
        data.delay or "P",
        f"{data.propellant_mass_kg:.4f}",
        f"{data.total_mass_kg:.4f}",
        data.manufacturer.replace(" ", "-") or "PARS",
    ])

    lines = [
        f"; {data.designation} - {data.propellant_name}",
        f"; {ATTRIBUTION_LINE}",
        f"; Designer: {data.designer}  Date: {data.date_iso}",
        f"; {DISCLAIMER_SHORT}",
        header,
    ]
    for t, f in zip(t_ds, f_ds, strict=True):
        lines.append(f"   {t:.4f}   {f:.3f}")
    lines.append(";")
    return "\n".join(lines) + "\n"


# --- parser (for the round-trip test and design re-import) -------------------

@dataclass
class ParsedEng:
    name: str
    diameter_mm: float
    length_mm: float
    delays: str
    propellant_mass_kg: float
    total_mass_kg: float
    manufacturer: str
    points: list[tuple[float, float]]   # (t, F), excludes the implicit (0, 0)

    @property
    def total_impulse(self) -> float:
        t = np.array([0.0] + [p[0] for p in self.points])
        f = np.array([0.0] + [p[1] for p in self.points])
        return float(np.trapezoid(f, t))

    @property
    def burn_time(self) -> float:
        return self.points[-1][0] if self.points else 0.0


def parse_eng(text: str) -> ParsedEng:
    """Parse a RASP ``.eng`` string. Ignores comment (``;``) and blank lines."""
    header = None
    points: list[tuple[float, float]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        parts = line.split()
        if header is None:
            if len(parts) != 7:
                raise ValueError(f"RASP header must have 7 fields, got {len(parts)}: {line!r}")
            header = parts
            continue
        if len(parts) != 2:
            raise ValueError(f"data line must be 't F', got {line!r}")
        points.append((float(parts[0]), float(parts[1])))

    if header is None:
        raise ValueError("no RASP header line found")
    if not points:
        raise ValueError("no data points")
    if points[-1][1] != 0.0:
        raise ValueError("last point thrust must be exactly 0")
    if any(f == 0.0 for _, f in points[:-1]):
        raise ValueError("interior points must not have zero thrust")
    times = [t for t, _ in points]
    if any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise ValueError("times must be strictly increasing")
    if len(points) > _MAX_POINTS:
        raise ValueError(f"more than {_MAX_POINTS} data points")

    return ParsedEng(
        name=header[0],
        diameter_mm=float(header[1]),
        length_mm=float(header[2]),
        delays=header[3],
        propellant_mass_kg=float(header[4]),
        total_mass_kg=float(header[5]),
        manufacturer=header[6],
        points=points,
    )
