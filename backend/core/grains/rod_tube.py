"""Rod-and-tube grain: a free (unbonded) central rod inside a case-bonded tube, ends
and OD inhibited (Section 5.2 extension).

The rod burns inward on its outer surface (shrinking) while the tube burns outward
on its inner surface (growing) at the same rate, toward each other::

    r_rod(x)     = max(d_rod/2 - x, 0)
    r_tube_id(x) = min(d_tube_id/2 + x, D_o/2)
    A_b(x)       = N * L * 2*pi * (r_rod(x) + r_tube_id(x))

Two circles offsetting toward each other keep the *sum* of their circumferences
close to constant for as long as both still have material left, which is what
makes this geometry read as an almost flat (neutral) thrust curve - no polygon
burnback needed, unlike star/wagon-wheel.
"""

from __future__ import annotations

import math

from core.grains.base import GrainGeometry, register_grain
from core.warnings import Warning, make


@register_grain("rod_tube")
class RodTubeGrain(GrainGeometry):
    def __init__(
        self,
        outer_diameter: float,
        core_diameter: float,      # rod diameter
        point_diameter: float,     # tube bore (inner) diameter
        length: float,
        segment_count: int = 1,
        segment_spacing: float = 0.0,
    ):
        if not (0 < core_diameter < outer_diameter):
            raise ValueError("rod diameter must be between 0 and outer_diameter")
        if not (0 < point_diameter < outer_diameter):
            raise ValueError("tube bore diameter must be between 0 and outer_diameter")
        if length <= 0:
            raise ValueError("rod-and-tube grain length must be positive")
        self.d_o = float(outer_diameter)
        self.d_rod = float(core_diameter)
        self.d_tube_i = float(point_diameter)
        self.l = float(length)
        self.n = int(segment_count)
        self.spacing = float(segment_spacing)

    def _radii(self, web: float) -> tuple[float, float]:
        r_o = self.d_o / 2.0
        r_rod = max(self.d_rod / 2.0 - web, 0.0)
        r_tube_i = min(self.d_tube_i / 2.0 + web, r_o)
        return r_rod, r_tube_i

    def burn_area(self, web: float) -> float:
        r_rod, r_tube_i = self._radii(web)
        return self.n * self.l * 2.0 * math.pi * (r_rod + r_tube_i)

    def volume(self, web: float) -> float:
        r_o = self.d_o / 2.0
        r_rod, r_tube_i = self._radii(web)
        solid = math.pi * r_rod**2 + math.pi * max(r_o**2 - r_tube_i**2, 0.0)
        return self.n * self.l * solid

    def port_area(self, web: float) -> float:
        r_rod, r_tube_i = self._radii(web)
        return math.pi * max(r_tube_i**2 - r_rod**2, 0.0)

    def web_thickness(self) -> float:
        return max(self.d_rod / 2.0, self.d_o / 2.0 - self.d_tube_i / 2.0)

    def outer_diameter(self) -> float:
        return self.d_o

    def envelope_length(self) -> float:
        return self.n * self.l + (self.n - 1) * self.spacing

    def validate(self) -> list[Warning]:
        w: list[Warning] = []
        if self.d_tube_i / self.d_o > 0.85:
            w.append(make("WARN_GRAIN_CORE_TOO_LARGE", ratio=round(self.d_tube_i / self.d_o, 2)))
        rod_web = self.d_rod / 2.0
        tube_web = self.d_o / 2.0 - self.d_tube_i / 2.0
        if rod_web > 0 and tube_web > 0 and abs(rod_web - tube_web) / max(rod_web, tube_web) > 0.25:
            w.append(make("WARN_PROGRESSIVE_GEOMETRY",
                          ratio=round(min(rod_web, tube_web) / max(rod_web, tube_web), 2),
                          geometry="rod_tube"))
        v0 = self.initial_volume()
        if v0 > 0 and self.sliver_volume() / v0 > 0.05:
            w.append(make("WARN_SLIVER_FRACTION_HIGH",
                          fraction=round(self.sliver_volume() / v0, 3)))
        return w

    def cross_section_svg(self, web: float) -> str:
        r_o = 45.0
        k = r_o / (self.d_o / 2.0)
        r_rod, r_tube_i = self._radii(web)
        return (
            f'<g stroke="currentColor" stroke-width="0.8">'
            f'<circle cx="50" cy="50" r="{r_o:.2f}" fill="var(--grain-fill, #d9b382)"/>'
            f'<circle cx="50" cy="50" r="{r_tube_i * k:.2f}" fill="var(--burnt-fill, #3a3a3a)"/>'
            f'<circle cx="50" cy="50" r="{r_rod * k:.2f}" fill="var(--grain-fill, #d9b382)"/>'
            f"</g>"
        )

    def to_dict(self) -> dict:
        return {
            "type": "rod_tube",
            "outer_diameter": self.d_o,
            "core_diameter": self.d_rod,
            "point_diameter": self.d_tube_i,
            "length": self.l,
            "segment_count": self.n,
            "segment_spacing": self.spacing,
        }
