"""Tubular (internal-burning tube) grain: ends and OD inhibited, core burns outward.

``A_b = 2*pi*r_p*L`` with ``r_p = d/2 + x``. The burning area grows monotonically, so
this geometry is **inherently progressive**: chamber pressure rises throughout the
burn. Selecting it always emits ``WARN_PROGRESSIVE_GEOMETRY`` (Section 5.2) and BATES
is recommended instead. It is kept because the Section 13.1 reference case uses it.
"""

from __future__ import annotations

import math

from core.grains.base import GrainGeometry, register_grain
from core.warnings import Warning, make


@register_grain("tubular")
class TubularGrain(GrainGeometry):
    def __init__(
        self,
        outer_diameter: float,
        core_diameter: float,
        length: float,
        segment_count: int = 1,
        segment_spacing: float = 0.0,
    ):
        if core_diameter >= outer_diameter:
            raise ValueError("core_diameter must be < outer_diameter")
        if length <= 0 or outer_diameter <= 0 or core_diameter <= 0:
            raise ValueError("tubular dimensions must be positive")
        self.d_o = float(outer_diameter)
        self.d = float(core_diameter)
        self.l = float(length)
        self.n = int(segment_count)
        self.spacing = float(segment_spacing)

    def _port_radius(self, web: float) -> float:
        return self.d / 2.0 + web

    def burn_area(self, web: float) -> float:
        r_p = min(self._port_radius(web), self.d_o / 2.0)
        return self.n * 2.0 * math.pi * r_p * self.l

    def volume(self, web: float) -> float:
        r_p = min(self._port_radius(web), self.d_o / 2.0)
        return self.n * math.pi * max((self.d_o / 2.0) ** 2 - r_p**2, 0.0) * self.l

    def port_area(self, web: float) -> float:
        return math.pi * min(self._port_radius(web), self.d_o / 2.0) ** 2

    def web_thickness(self) -> float:
        return (self.d_o - self.d) / 2.0

    def outer_diameter(self) -> float:
        return self.d_o

    def envelope_length(self) -> float:
        return self.n * self.l + (self.n - 1) * self.spacing

    def validate(self) -> list[Warning]:
        a0 = self.burn_area(0.0)
        a_end = self.burn_area(self.web_thickness() * 0.999)
        ratio = round(a_end / a0, 2) if a0 > 0 else None
        return [make("WARN_PROGRESSIVE_GEOMETRY", geometry="tubular",
                     suggestion="bates", area_ratio=ratio)]

    def cross_section_svg(self, web: float) -> str:
        r_o = 45.0
        core_r = min(self._port_radius(web) / (self.d_o / 2.0) * r_o, r_o)
        return (
            f'<g stroke="currentColor" stroke-width="0.8">'
            f'<circle cx="50" cy="50" r="{r_o:.2f}" fill="var(--grain-fill, #d9b382)"/>'
            f'<circle cx="50" cy="50" r="{core_r:.2f}" fill="var(--burnt-fill, #3a3a3a)"/>'
            f"</g>"
        )

    def to_dict(self) -> dict:
        return {
            "type": "tubular",
            "outer_diameter": self.d_o,
            "core_diameter": self.d,
            "length": self.l,
            "segment_count": self.n,
            "segment_spacing": self.spacing,
        }
