"""Wagon-wheel (cross) grain: a central hub bore with N radial slots, ends and OD
inhibited (Section 5.2 extension).

Burn area starts high (the slots' side walls plus the hub's own perimeter) and
falls as the slots widen and the hub grows into them - a regressive burn, the
classic "cross" shape being the N=4 case. See ``core/grains/_slotted.py`` for how
the burn-area/volume/port-area curves are computed.
"""

from __future__ import annotations

import math

from core.grains._slotted import PolygonBurnbackMixin, wagon_wheel_void_polygon
from core.grains.base import GrainGeometry, register_grain
from core.warnings import Warning, make


@register_grain("wagon_wheel")
class WagonWheelGrain(PolygonBurnbackMixin, GrainGeometry):
    def __init__(
        self,
        outer_diameter: float,
        core_diameter: float,      # hub diameter
        point_diameter: float,     # slot-tip diameter
        length: float,
        n_points: int = 4,         # slot count ("points" name shared with star, group UI)
        segment_count: int = 1,
        segment_spacing: float = 0.0,
        slot_half_angle_deg: float | None = None,
    ):
        if not (0 < core_diameter < point_diameter < outer_diameter):
            raise ValueError(
                "wagon-wheel grain needs core_diameter < point_diameter < outer_diameter")
        if length <= 0:
            raise ValueError("wagon-wheel grain length must be positive")
        if n_points < 3:
            raise ValueError("n_points (slot count) must be >= 3")
        self.d_o = float(outer_diameter)
        self.d = float(core_diameter)
        self.d_point = float(point_diameter)
        self.l = float(length)
        self.n_points = int(n_points)
        self.n = int(segment_count)
        self.spacing = float(segment_spacing)
        # a slot occupying too much of its angular pitch would self-intersect its
        # neighbour; keep a comfortable margin unless the caller overrides it
        self.slot_half_angle_deg = float(slot_half_angle_deg) if slot_half_angle_deg else min(
            15.0, 0.35 * 180.0 / self.n_points)

        void0 = wagon_wheel_void_polygon(
            self.n_points, self.d / 2.0, self.d_point / 2.0, self.slot_half_angle_deg)
        self._init_burnback(void0, self.d_o / 2.0, self.l * self.n)

    def outer_diameter(self) -> float:
        return self.d_o

    def envelope_length(self) -> float:
        return self.n * self.l + (self.n - 1) * self.spacing

    def validate(self) -> list[Warning]:
        w: list[Warning] = []
        if self.d_point / self.d_o > 0.92:
            w.append(make("WARN_GRAIN_CORE_TOO_LARGE", ratio=round(self.d_point / self.d_o, 2)))
        v0 = self.initial_volume()
        if v0 > 0 and self.sliver_volume() / v0 > 0.05:
            w.append(make("WARN_SLIVER_FRACTION_HIGH",
                          fraction=round(self.sliver_volume() / v0, 3)))
        return w

    def cross_section_svg(self, web: float) -> str:
        r_o = 45.0
        k = r_o / (self.d_o / 2.0)
        r_hub = self.d / 2.0 * k + web * k
        r_tip = min(self.d_point / 2.0 * k + web * k, r_o)
        half = math.radians(self.slot_half_angle_deg)
        parts = [f'<circle cx="50" cy="50" r="{r_hub:.2f}" fill="var(--burnt-fill, #3a3a3a)"/>']
        for i in range(self.n_points):
            c = 2.0 * math.pi * i / self.n_points
            x1, y1 = 50 + r_tip * math.cos(c - half), 50 + r_tip * math.sin(c - half)
            x2, y2 = 50 + r_tip * math.cos(c + half), 50 + r_tip * math.sin(c + half)
            hx1, hy1 = 50 + r_hub * math.cos(c - half), 50 + r_hub * math.sin(c - half)
            hx2, hy2 = 50 + r_hub * math.cos(c + half), 50 + r_hub * math.sin(c + half)
            parts.append(
                f'<polygon points="{hx1:.2f},{hy1:.2f} {x1:.2f},{y1:.2f} '
                f'{x2:.2f},{y2:.2f} {hx2:.2f},{hy2:.2f}" fill="var(--burnt-fill, #3a3a3a)"/>')
        return (
            f'<g stroke="currentColor" stroke-width="0.8">'
            f'<circle cx="50" cy="50" r="{r_o:.2f}" fill="var(--grain-fill, #d9b382)"/>'
            f'{"".join(parts)}'
            f"</g>"
        )

    def to_dict(self) -> dict:
        return {
            "type": "wagon_wheel",
            "outer_diameter": self.d_o,
            "core_diameter": self.d,
            "point_diameter": self.d_point,
            "length": self.l,
            "n_points": self.n_points,
            "segment_count": self.n,
            "segment_spacing": self.spacing,
            "slot_half_angle_deg": self.slot_half_angle_deg,
        }
