"""Star grain: an N-pointed star bore, ends and OD inhibited (Section 5.2 extension).

The star points sit closest to the case OD (thinnest initial web there) and the
valleys sit closest to the axis (thickest web). As burning progresses the points
round off and eventually the shape merges into a plain circle - burn area therefore
typically starts high (long scalloped perimeter) and falls as the points burn away,
tapering into the same late-burn trend as a plain tubular grain. See
``core/grains/_slotted.py`` for how the burn-area/volume/port-area curves are
computed (a numeric polygon-offset, not a hand-derived formula).
"""

from __future__ import annotations

import math

from core.grains._slotted import PolygonBurnbackMixin, star_void_polygon
from core.grains.base import GrainGeometry, register_grain
from core.warnings import Warning, make


@register_grain("star")
class StarGrain(PolygonBurnbackMixin, GrainGeometry):
    def __init__(
        self,
        outer_diameter: float,
        core_diameter: float,     # root (valley) diameter
        point_diameter: float,    # tip-to-tip diameter
        length: float,
        n_points: int = 6,
        segment_count: int = 1,
        segment_spacing: float = 0.0,
    ):
        if not (0 < core_diameter < point_diameter < outer_diameter):
            raise ValueError("star grain needs core_diameter < point_diameter < outer_diameter")
        if length <= 0:
            raise ValueError("star grain length must be positive")
        if n_points < 3:
            raise ValueError("n_points must be >= 3")
        self.d_o = float(outer_diameter)
        self.d = float(core_diameter)
        self.d_point = float(point_diameter)
        self.l = float(length)
        self.n_points = int(n_points)
        self.n = int(segment_count)
        self.spacing = float(segment_spacing)

        void0 = star_void_polygon(self.n_points, self.d / 2.0, self.d_point / 2.0)
        self._init_burnback(void0, self.d_o / 2.0, self.l * self.n)

    def outer_diameter(self) -> float:
        return self.d_o

    def envelope_length(self) -> float:
        return self.n * self.l + (self.n - 1) * self.spacing

    def validate(self) -> list[Warning]:
        w: list[Warning] = []
        if self.d_point / self.d_o > 0.92:
            w.append(make("WARN_GRAIN_CORE_TOO_LARGE", ratio=round(self.d_point / self.d_o, 2)))
        a0 = self.burn_area(0.0)
        a_end = self.burn_area(self.web_thickness() * 0.999)
        if a0 > 0 and (a_end - a0) / a0 > 0.20:
            w.append(make("WARN_PROGRESSIVE_GEOMETRY",
                          ratio=round(a_end / a0, 2), geometry="star"))
        v0 = self.initial_volume()
        if v0 > 0 and self.sliver_volume() / v0 > 0.05:
            w.append(make("WARN_SLIVER_FRACTION_HIGH",
                          fraction=round(self.sliver_volume() / v0, 3)))
        return w

    def cross_section_svg(self, web: float) -> str:
        r_o = 45.0
        k = r_o / (self.d_o / 2.0)
        r_root0 = self.d / 2.0 * k
        r_tip0 = self.d_point / 2.0 * k
        n = self.n_points
        pts = []
        for i in range(2 * n):
            r = (r_tip0 if i % 2 == 0 else r_root0) + web * k
            r = min(r, r_o)
            theta = math.pi * i / n
            pts.append(f"{50 + r * math.cos(theta):.2f},{50 + r * math.sin(theta):.2f}")
        return (
            f'<g stroke="currentColor" stroke-width="0.8">'
            f'<circle cx="50" cy="50" r="{r_o:.2f}" fill="var(--grain-fill, #d9b382)"/>'
            f'<polygon points="{" ".join(pts)}" fill="var(--burnt-fill, #3a3a3a)"/>'
            f"</g>"
        )

    def to_dict(self) -> dict:
        return {
            "type": "star",
            "outer_diameter": self.d_o,
            "core_diameter": self.d,
            "point_diameter": self.d_point,
            "length": self.l,
            "n_points": self.n_points,
            "segment_count": self.n,
            "segment_spacing": self.spacing,
        }
