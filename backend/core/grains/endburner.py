"""End-burner grain: only one circular face burns, cigarette-style.

``A_b = pi*(D_o/2)**2`` — constant, so the burn is perfectly neutral. The trade-off
is a long burn time and low thrust, and because ``L/D`` is high the case wall is
heat-soaked for the whole burn: ``WARN_ENDBURNER_THERMAL_SOAK`` (Section 5.2).
"""

from __future__ import annotations

import math

from core.grains.base import GrainGeometry, register_grain
from core.warnings import Warning, make


@register_grain("endburner")
class EndBurnerGrain(GrainGeometry):
    def __init__(self, outer_diameter: float, length: float):
        if outer_diameter <= 0 or length <= 0:
            raise ValueError("end-burner dimensions must be positive")
        self.d_o = float(outer_diameter)
        self.l = float(length)

    def burn_area(self, web: float) -> float:
        if web >= self.l:
            return 0.0
        return math.pi * (self.d_o / 2.0) ** 2

    def volume(self, web: float) -> float:
        remaining = max(self.l - web, 0.0)
        return math.pi * (self.d_o / 2.0) ** 2 * remaining

    def port_area(self, web: float) -> float:
        # no central port; the free cross-section upstream of the flame is the bore
        return math.pi * (self.d_o / 2.0) ** 2

    def web_thickness(self) -> float:
        return self.l

    def outer_diameter(self) -> float:
        return self.d_o

    def envelope_length(self) -> float:
        return self.l

    def validate(self) -> list[Warning]:
        lod = round(self.l / self.d_o, 2)
        return [make("WARN_ENDBURNER_THERMAL_SOAK", length_over_diameter=lod)]

    def cross_section_svg(self, web: float) -> str:
        r_o = 45.0
        return (
            f'<g stroke="currentColor" stroke-width="0.8">'
            f'<circle cx="50" cy="50" r="{r_o:.2f}" fill="var(--grain-fill, #d9b382)"/>'
            f"</g>"
        )

    def to_dict(self) -> dict:
        return {"type": "endburner", "outer_diameter": self.d_o, "length": self.l}
