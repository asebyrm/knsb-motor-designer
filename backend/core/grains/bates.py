"""BATES grain: N cylindrical segments, core + both end faces burning, OD inhibited.

Burn area (Section 5.2)::

    core_r  = d/2 + x
    A_b(x)  = N * [ 2*pi*core_r*(L_s - 2x) + 2*pi*((D_o/2)**2 - core_r**2) ]
    web     = min( (D_o - d)/2 , L_s/2 )

Each bracketed term is clamped at zero (a segment that has burnt through axially,
or a core that has reached the OD, stops contributing).
"""

from __future__ import annotations

import math

from core.grains.base import GrainGeometry, register_grain
from core.warnings import Warning, make


@register_grain("bates")
class BatesGrain(GrainGeometry):
    def __init__(
        self,
        outer_diameter: float,
        core_diameter: float,
        segment_length: float,
        segment_count: int = 1,
        segment_spacing: float = 0.0,
    ):
        if core_diameter >= outer_diameter:
            raise ValueError("core_diameter must be < outer_diameter")
        if segment_length <= 0 or outer_diameter <= 0 or core_diameter <= 0:
            raise ValueError("BATES dimensions must be positive")
        if segment_count < 1:
            raise ValueError("segment_count must be >= 1")
        self.d_o = float(outer_diameter)
        self.d = float(core_diameter)
        self.l_s = float(segment_length)
        self.n = int(segment_count)
        self.spacing = float(segment_spacing)

    # --- geometry ------------------------------------------------------

    def _core_radius(self, web: float) -> float:
        return self.d / 2.0 + web

    def burn_area(self, web: float) -> float:
        core_r = self._core_radius(web)
        r_o = self.d_o / 2.0
        seg_len = max(self.l_s - 2.0 * web, 0.0)
        core_surface = 2.0 * math.pi * core_r * seg_len
        end_faces = 2.0 * math.pi * max(r_o**2 - core_r**2, 0.0)
        return self.n * max(core_surface + end_faces, 0.0)

    def volume(self, web: float) -> float:
        core_r = self._core_radius(web)
        r_o = self.d_o / 2.0
        seg_len = max(self.l_s - 2.0 * web, 0.0)
        solid = math.pi * max(r_o**2 - core_r**2, 0.0) * seg_len
        return self.n * solid

    def port_area(self, web: float) -> float:
        return math.pi * self._core_radius(web) ** 2

    def web_thickness(self) -> float:
        return min((self.d_o - self.d) / 2.0, self.l_s / 2.0)

    def outer_diameter(self) -> float:
        return self.d_o

    def envelope_length(self) -> float:
        return self.n * self.l_s + (self.n - 1) * self.spacing

    # --- validation --------------------------------------------------

    def validate(self) -> list[Warning]:
        w: list[Warning] = []
        if self.d / self.d_o > 0.55:
            w.append(make("WARN_GRAIN_CORE_TOO_LARGE",
                          ratio=round(self.d / self.d_o, 2)))
        a0 = self.burn_area(0.0)
        a_end = self.burn_area(self.web_thickness() * 0.999)
        if a0 > 0 and (a_end - a0) / a0 > 0.20:
            w.append(make("WARN_PROGRESSIVE_GEOMETRY",
                          ratio=round(a_end / a0, 2), geometry="bates"))
        v0 = self.initial_volume()
        if v0 > 0 and self.sliver_volume() / v0 > 0.05:
            w.append(make("WARN_SLIVER_FRACTION_HIGH",
                          fraction=round(self.sliver_volume() / v0, 3)))
        return w

    # --- drawing ---------------------------------------------------

    def cross_section_svg(self, web: float) -> str:
        """Transverse section (one segment), viewBox 0 0 100 100."""
        r_o = 45.0
        core_r = self._core_radius(web) / (self.d_o / 2.0) * r_o
        burnt_r = self.d / 2.0 / (self.d_o / 2.0) * r_o
        return (
            f'<g stroke="currentColor" stroke-width="0.8">'
            f'<circle cx="50" cy="50" r="{r_o:.2f}" fill="var(--grain-fill, #d9b382)"/>'
            f'<circle cx="50" cy="50" r="{core_r:.2f}" fill="var(--burnt-fill, #3a3a3a)"/>'
            f'<circle cx="50" cy="50" r="{burnt_r:.2f}" fill="none" '
            f'stroke-dasharray="1.5 1.5" opacity="0.5"/>'
            f"</g>"
        )

    def to_dict(self) -> dict:
        return {
            "type": "bates",
            "outer_diameter": self.d_o,
            "core_diameter": self.d,
            "segment_length": self.l_s,
            "segment_count": self.n,
            "segment_spacing": self.spacing,
        }


def suggest_neutral_segment_length(outer_diameter: float, core_diameter: float) -> float:
    """Segment length [m] making A_b(0) == A_b(web) for a single BATES segment.

    Solved numerically (Section 5.2). The closed-form seed is L_s = (3*D_o + d)/2,
    valid while the grain stays radially web-limited.
    """
    from scipy.optimize import brentq

    d_o, d = float(outer_diameter), float(core_diameter)

    def imbalance(l_s: float) -> float:
        g = BatesGrain(d_o, d, l_s, segment_count=1)
        web = g.web_thickness()
        return g.burn_area(0.0) - g.burn_area(web * 0.999999)

    seed = (3.0 * d_o + d) / 2.0
    lo, hi = 0.2 * seed, 5.0 * seed
    # ensure a bracket
    f_lo, f_hi = imbalance(lo), imbalance(hi)
    tries = 0
    while f_lo * f_hi > 0 and tries < 30:
        hi *= 1.3
        f_hi = imbalance(hi)
        tries += 1
    if f_lo * f_hi > 0:
        return seed
    return float(brentq(imbalance, lo, hi, xtol=1e-6, maxiter=200))
