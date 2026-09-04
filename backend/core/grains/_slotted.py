"""Shared "burnback" engine for grain cross-sections with no simple closed-form
burn-area formula: star and wagon-wheel (Section 5.2 extension).

BATES and tubular have a burning surface whose shape never changes topology as it
burns, so the perimeter can be written down directly. A star or wagon-wheel bore
does change topology - point tips round off and disappear, valleys eventually merge
into a plain circle - and getting a hand-derived formula right for every phase of
that is exactly the kind of thing best not done from memory. Instead this treats the
bore as a real 2D polygon and grows it by the burnt web distance using shapely's
`buffer` (a standard, exact polygon-offset/erosion operation), the same idea BATES'
own ``core_r = d/2 + x`` is doing in closed form for a circle.

Definitions, all per unit axial length (multiplied by grain length by the caller):
  - the *void* (bore) at web=0 is a polygon built by the concrete subclass
  - at web ``w``, the void has grown to ``void0.buffer(w)`` clipped to the outer
    circle (burning stops at the case-bonded OD)
  - remaining solid (propellant) area  = outer circle area - grown void area
  - burn_area(w)  = -d(solid area)/dw       (by definition: this *is* the rate the
    solid is consumed per unit of web progression), taken as a central finite
    difference of the exact shapely-computed area - no shape-specific formula
  - port_area(w)  = grown void area (the local free-flow cross-section)

A handful of shapely `buffer` calls per web sample is too slow to call directly
from the ballistics integrator (thousands of timesteps), so each instance builds a
dense lookup table once at construction and answers queries by interpolating it
(``np.interp``) - accurate to the table's resolution, and back to closed-form speed
for everything downstream.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.interpolate import PchipInterpolator
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

_TABLE_POINTS = 400
_DWEB_FRACTION = 1e-4  # finite-difference step, as a fraction of web_thickness


def star_void_polygon(n_points: int, r_root: float, r_tip: float) -> Polygon:
    """The star-shaped bore: ``n_points`` tips at radius r_tip alternating with
    ``n_points`` root (valley) vertices at radius r_root, evenly spaced."""
    n = 2 * n_points
    pts = []
    for i in range(n):
        r = r_tip if i % 2 == 0 else r_root
        theta = math.pi * i / n_points
        pts.append((r * math.cos(theta), r * math.sin(theta)))
    return Polygon(pts)


def wagon_wheel_void_polygon(n_slots: int, r_hub: float, r_slot_tip: float,
                              slot_half_angle_deg: float, arc_segs: int = 12) -> Polygon:
    """A central hub disc of radius ``r_hub`` with ``n_slots`` identical sector-shaped
    slots cut radially outward to ``r_slot_tip``."""
    hub = Point(0, 0).buffer(r_hub, quad_segs=64)
    half = math.radians(slot_half_angle_deg)
    shapes = [hub]
    for k in range(n_slots):
        center = 2.0 * math.pi * k / n_slots
        arc = [(r_hub * math.cos(center - half + i * (2 * half) / arc_segs),
                r_hub * math.sin(center - half + i * (2 * half) / arc_segs))
               for i in range(arc_segs + 1)]
        pts = [*arc,
               (r_slot_tip * math.cos(center + half), r_slot_tip * math.sin(center + half)),
               (r_slot_tip * math.cos(center - half), r_slot_tip * math.sin(center - half))]
        shapes.append(Polygon(pts))
    return unary_union(shapes)


@dataclass
class _BurnbackTable:
    web_grid: np.ndarray
    burn_area_grid: np.ndarray     # m^2 per unit length
    volume_grid: np.ndarray        # m^3 per unit length (= solid area)
    port_area_grid: np.ndarray     # m^2
    web_max: float
    # monotone cubic (PCHIP) fits of the grids above - smoother derivatives than
    # raw piecewise-linear interpolation, which otherwise gives the per-timestep
    # pressure-equilibrium solver a tiny kink at every one of the table's nodes and
    # pushes it toward its slower iterative fallback far more than a closed-form
    # grain's naturally smooth curve would
    _burn_area_fit: PchipInterpolator | None = None
    _volume_fit: PchipInterpolator | None = None
    _port_area_fit: PchipInterpolator | None = None

    def __post_init__(self) -> None:
        self._burn_area_fit = PchipInterpolator(self.web_grid, self.burn_area_grid)
        self._volume_fit = PchipInterpolator(self.web_grid, self.volume_grid)
        self._port_area_fit = PchipInterpolator(self.web_grid, self.port_area_grid)


def build_burnback_table(void0: Polygon, outer_radius: float) -> _BurnbackTable:
    outer = Point(0, 0).buffer(outer_radius, quad_segs=128)
    outer_area = outer.area

    def solid_area(w: float) -> float:
        w = max(w, 0.0)
        grown = void0.buffer(w, quad_segs=48) if w > 0 else void0
        grown = grown.intersection(outer)
        return outer_area - grown.area

    def void_area(w: float) -> float:
        w = max(w, 0.0)
        grown = void0.buffer(w, quad_segs=48) if w > 0 else void0
        return grown.intersection(outer).area

    # web_thickness: smallest w at which the solid area has (numerically) vanished
    w_hi = outer_radius
    while solid_area(w_hi) > 1e-12 and w_hi < outer_radius * 4:
        w_hi *= 1.5
    lo, hi = 0.0, w_hi
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if solid_area(mid) > 1e-12:
            lo = mid
        else:
            hi = mid
    web_max = lo

    web_grid = np.linspace(0.0, web_max, _TABLE_POINTS)
    dweb = max(web_max * _DWEB_FRACTION, 1e-9)
    burn_area_grid = np.empty(_TABLE_POINTS)
    volume_grid = np.empty(_TABLE_POINTS)
    port_area_grid = np.empty(_TABLE_POINTS)
    for i, w in enumerate(web_grid):
        volume_grid[i] = solid_area(w)
        port_area_grid[i] = void_area(w)
        a_plus = solid_area(min(w + dweb, web_max))
        a_minus = solid_area(max(w - dweb, 0.0))
        span = min(w + dweb, web_max) - max(w - dweb, 0.0)
        burn_area_grid[i] = max(-(a_plus - a_minus) / span, 0.0) if span > 0 else 0.0
    burn_area_grid[-1] = 0.0  # exactly consumed at web_max by construction

    return _BurnbackTable(web_grid, burn_area_grid, volume_grid, port_area_grid, web_max)


class PolygonBurnbackMixin:
    """Mixin for a grain whose bore is a 2D polygon (star, wagon wheel). The
    concrete class must set ``self._table`` (a :class:`_BurnbackTable`) and
    ``self._length_total`` (total axial burning length, all segments) in
    ``__init__``, e.g. via :meth:`_init_burnback`."""

    _table: _BurnbackTable
    _length_total: float

    def _init_burnback(self, void0: Polygon, outer_radius: float, length_total: float) -> None:
        self._table = build_burnback_table(void0, outer_radius)
        self._length_total = length_total

    def burn_area(self, web: float) -> float:
        w = min(max(web, 0.0), self._table.web_max)
        return max(float(self._table._burn_area_fit(w)), 0.0) * self._length_total

    def volume(self, web: float) -> float:
        w = min(max(web, 0.0), self._table.web_max)
        return max(float(self._table._volume_fit(w)), 0.0) * self._length_total

    def port_area(self, web: float) -> float:
        w = min(max(web, 0.0), self._table.web_max)
        return max(float(self._table._port_area_fit(w)), 0.0)

    def web_thickness(self) -> float:
        return self._table.web_max
