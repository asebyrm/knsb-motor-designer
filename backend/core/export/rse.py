"""RockSim ``.rse`` writer (Section 7.2).

``<engine-database><engine-list><engine ...>`` with every attribute a quoted string.
Unlike ``.eng`` this carries time-varying mass and CG, so ``auto-calc-mass`` /
``auto-calc-cg`` are ``0`` and the real simulated values go into each ``<eng-data>``
row (``m`` in grams = total motor mass, ``cg`` in mm from the forward face).
"""

from __future__ import annotations

from xml.sax.saxutils import quoteattr

import numpy as np

from core.branding import ATTRIBUTION_LINE, DISCLAIMER_SHORT
from core.export.model import MotorExportData
from core.sampling import downsample_curve

_MAX_POINTS = 100


def render_rse(data: MotorExportData) -> str:
    t = np.asarray(data.time_s)
    f = np.asarray(data.thrust_n)
    m = np.asarray(data.total_mass_series_kg)
    cg = np.asarray(data.cg_series_mm)

    t_ds, f_ds, extra = downsample_curve(t, f, _MAX_POINTS,
                                         extra={"m": m, "cg": cg}, area_tol=0.005)
    m_ds, cg_ds = extra["m"], extra["cg"]

    def a(v) -> str:
        return quoteattr(f"{v}")

    eng_attrs = " ".join([
        f"mfg={a(data.manufacturer)}",
        f"code={a(data.display_name)}",
        'Type="single-use"',
        f"dia={a(round(data.case_diameter_mm, 2))}",
        f"len={a(round(data.case_length_mm, 2))}",
        f"initWt={a(round(data.total_mass_kg * 1000.0, 2))}",
        f"propWt={a(round(data.propellant_mass_kg * 1000.0, 2))}",
        f"delays={a(data.delay or 'P')}",
        'auto-calc-mass="0"',
        'auto-calc-cg="0"',
        f"Itot={a(round(data.total_impulse_ns, 2))}",
        f"avgThrust={a(round(data.average_thrust_n, 2))}",
        f"peakThrust={a(round(data.peak_thrust_n, 2))}",
        f"burn-time={a(round(data.burn_time_s, 3))}",
        f"Isp={a(round(data.specific_impulse_s, 2))}",
        f"throatDia={a(round(data.throat_diameter_mm, 2))}",
        f"exitDia={a(round(data.exit_diameter_mm, 2))}",
    ])

    rows = []
    for tt, ff, mm, cc in zip(t_ds, f_ds, m_ds, cg_ds, strict=True):
        rows.append(
            f'      <eng-data t={a(round(float(tt), 4))} f={a(round(float(ff), 3))} '
            f'm={a(round(float(mm) * 1000.0, 3))} cg={a(round(float(cc), 2))}/>'
        )

    return (
        '<engine-database>\n'
        '  <engine-list>\n'
        f'    <engine {eng_attrs}>\n'
        f'      <comments>{ATTRIBUTION_LINE} | {DISCLAIMER_SHORT}</comments>\n'
        '      <data>\n'
        + "\n".join(rows) + "\n"
        '      </data>\n'
        '    </engine>\n'
        '  </engine-list>\n'
        '</engine-database>\n'
    )
