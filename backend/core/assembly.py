"""Motor layout: part positions, total length / mass / CG, free volume, fit checks.

One source of truth for the technical drawing (Section 10.1) *and* the ``.eng`` / ``.rse``
exports and the CG-vs-time series - they must not compute geometry twice.

Axis convention: ``x`` grows from the forward face of the bulkhead (x = 0) toward the
nozzle exit. All SI.

Stack, front to back::

    bulkhead | fwd gap | [ liner [ grain ] ] | aft gap | nozzle (conv + throat + div)

The case tube wall surrounds the liner/grain region and the convergent nozzle seat;
the divergent cone protrudes past the case.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.grains.base import GrainGeometry
from core.materials import CaseMaterial, LinerMaterial
from core.nozzle import Nozzle
from core.propellant import Propellant
from core.warnings import Warning, make

_GRAPHITE_DENSITY = 1800.0  # kg/m^3, machined nozzle blank


@dataclass
class CaseSpec:
    material: CaseMaterial
    inner_diameter: float          # m
    wall_thickness: float          # m
    length: float | None = None    # m internal length; auto-fitted when None

    @property
    def outer_diameter(self) -> float:
        return self.inner_diameter + 2.0 * self.wall_thickness


@dataclass
class LinerSpec:
    material: LinerMaterial
    thickness: float               # m


@dataclass
class BulkheadSpec:
    material: CaseMaterial
    thickness: float               # m
    seat_length: float = 0.0       # m axial engagement into the case


@dataclass
class Part:
    name: str            # i18n key suffix, e.g. "bulkhead"
    x_start: float       # m
    x_end: float         # m
    outer_diameter: float
    inner_diameter: float
    material_id: str
    mass: float          # kg (at the reference web)
    centroid: float      # m

    @property
    def length(self) -> float:
        return self.x_end - self.x_start


@dataclass
class MotorAssembly:
    grain: GrainGeometry
    propellant: Propellant
    nozzle: Nozzle
    case: CaseSpec
    bulkhead: BulkheadSpec
    liner: LinerSpec | None = None
    forward_gap: float = 0.002     # m ullage forward of the grain
    aft_gap: float = 0.002         # m between grain and nozzle seat
    nozzle_material_density: float = _GRAPHITE_DENSITY
    nozzle_outer_diameter: float | None = None  # defaults to case OD

    # --- derived diameters --------------------------------------------

    @property
    def liner_inner_diameter(self) -> float:
        t = self.liner.thickness if self.liner else 0.0
        return self.case.inner_diameter - 2.0 * t

    @property
    def nozzle_od(self) -> float:
        return self.nozzle_outer_diameter or self.case.outer_diameter

    # --- nozzle external geometry (from the gas-dynamics Nozzle) ------

    def _nozzle_lengths(self) -> tuple[float, float, float]:
        """(convergent, throat, divergent) axial lengths [m]."""
        r_t = self.nozzle.throat_diameter / 2.0
        r_e = self.nozzle.exit_diameter / 2.0
        r_chamber = self.liner_inner_diameter / 2.0
        conv = max(r_chamber - r_t, 0.0) / math.tan(
            math.radians(self.nozzle.convergence_half_angle_deg))
        div = max(r_e - r_t, 0.0) / math.tan(
            math.radians(self.nozzle.divergence_half_angle_deg))
        throat = self.nozzle.throat_length or 0.3 * r_t
        return conv, throat, div

    @staticmethod
    def _frustum_volume(h: float, r1: float, r2: float) -> float:
        return math.pi * h / 3.0 * (r1 * r1 + r1 * r2 + r2 * r2)

    def _nozzle_flow_volume(self) -> float:
        conv, throat, div = self._nozzle_lengths()
        r_t = self.nozzle.throat_diameter / 2.0
        r_e = self.nozzle.exit_diameter / 2.0
        r_c = self.liner_inner_diameter / 2.0
        return (self._frustum_volume(conv, r_c, r_t) + math.pi * r_t * r_t * throat
                + self._frustum_volume(div, r_t, r_e))

    def _nozzle_mass(self) -> float:
        conv, throat, div = self._nozzle_lengths()
        r_out = self.nozzle_od / 2.0
        solid = math.pi * r_out * r_out * (conv + throat + div) - self._nozzle_flow_volume()
        return max(solid, 0.0) * self.nozzle_material_density

    # --- layout ------------------------------------------------------

    def _grain_region_length(self) -> float:
        return self.forward_gap + self.grain.envelope_length() + self.aft_gap

    def case_tube_length(self) -> float:
        """Axial length of the cylindrical case wall (excludes the divergent cone)."""
        if self.case.length is not None:
            return self.case.length
        conv, throat, _ = self._nozzle_lengths()
        return (self.bulkhead.thickness + self._grain_region_length() + conv + throat)

    def compute_layout(self, web: float = 0.0) -> list[Part]:
        """Ordered parts with axial extents, diameters, masses and centroids."""
        parts: list[Part] = []
        d_ci, d_co = self.case.inner_diameter, self.case.outer_diameter
        rho_case = self.case.material.density

        # bulkhead (solid disc spanning the case OD)
        x = 0.0
        bh_len = self.bulkhead.thickness
        bh_mass = math.pi * (d_co / 2.0) ** 2 * bh_len * self.bulkhead.material.density
        parts.append(Part("bulkhead", x, x + bh_len, d_co, 0.0,
                          self.bulkhead.material.id, bh_mass, x + bh_len / 2.0))
        x += bh_len

        grain_region_start = x + self.forward_gap
        grain_env = self.grain.envelope_length()

        # liner sleeve
        if self.liner and self.liner.thickness > 0:
            d_li = self.liner_inner_diameter
            liner_len = grain_env
            liner_mass = (math.pi * ((d_ci / 2.0) ** 2 - (d_li / 2.0) ** 2)
                          * liner_len * self.liner.material.density)
            parts.append(Part("liner", grain_region_start, grain_region_start + liner_len,
                              d_ci, d_li, self.liner.material.id, liner_mass,
                              grain_region_start + liner_len / 2.0))

        # grain (propellant)
        d_go = self.grain.outer_diameter()
        grain_mass = self.propellant.density * self.grain.volume(web)
        port_a = self.grain.port_area(web)
        d_port = 2.0 * math.sqrt(port_a / math.pi) if port_a > 0 else 0.0
        parts.append(Part("grain", grain_region_start, grain_region_start + grain_env,
                          d_go, d_port, self.propellant.id, grain_mass,
                          grain_region_start + grain_env / 2.0))

        # case tube wall
        tube_len = self.case_tube_length()
        tube_mass = (math.pi * ((d_co / 2.0) ** 2 - (d_ci / 2.0) ** 2) * tube_len * rho_case)
        parts.append(Part("case", 0.0, tube_len, d_co, d_ci,
                          self.case.material.id, tube_mass, tube_len / 2.0))

        # nozzle (convergent + throat + divergent)
        conv, throat, div = self._nozzle_lengths()
        noz_start = grain_region_start + grain_env + self.aft_gap
        noz_len = conv + throat + div
        noz_mass = self._nozzle_mass()
        parts.append(Part("nozzle", noz_start, noz_start + noz_len, self.nozzle_od,
                          self.nozzle.throat_diameter, "graphite", noz_mass,
                          noz_start + 0.45 * noz_len))

        return parts

    # --- aggregate metrics ------------------------------------------

    def total_length(self) -> float:
        """Bulkhead front face to nozzle exit plane [m] (=> .eng header 'len')."""
        parts = self.compute_layout(0.0)
        return max(p.x_end for p in parts)

    def total_mass(self, web: float = 0.0) -> float:
        """Loaded motor mass [kg] at burnt web ``web`` (=> .eng header 'initWt' at web 0)."""
        return sum(p.mass for p in self.compute_layout(web))

    def inert_mass(self) -> float:
        """Motor mass with all propellant gone [kg]."""
        return self.total_mass(self.grain.web_thickness())

    def center_of_gravity(self, web: float = 0.0) -> float:
        """CG measured from the forward face [m]."""
        parts = self.compute_layout(web)
        m = sum(p.mass for p in parts)
        if m <= 0:
            return self.total_length() / 2.0
        return sum(p.mass * p.centroid for p in parts) / m

    def free_volume(self, web: float = 0.0) -> float:
        """Combustion-chamber free (gas) volume [m^3] at burnt web ``web``."""
        r_bore = self.liner_inner_diameter / 2.0
        bore_volume = math.pi * r_bore * r_bore * self._grain_region_length()
        conv, _throat, _div = self._nozzle_lengths()
        r_t = self.nozzle.throat_diameter / 2.0
        conv_flow = math.pi * conv / 3.0 * (r_bore**2 + r_bore * r_t + r_t**2)
        solid = self.grain.volume(min(web, self.grain.web_thickness()))
        return max(bore_volume + conv_flow - solid, 1e-9)

    def characteristic_length(self) -> float:
        """L* = free volume at ignition / throat area [m]."""
        return self.free_volume(0.0) / self.nozzle.throat_area

    # --- fit validation -------------------------------------------

    def validate_fit(self) -> list[Warning]:
        """Geometric interference checks (Section 10.1 pt 4). Frontend does not repeat these."""
        w: list[Warning] = []
        d_li = self.liner_inner_diameter

        if self.liner and (self.liner.thickness <= 0 or d_li <= 0
                           or 2.0 * self.liner.thickness >= self.case.inner_diameter):
            w.append(make("WARN_FIT_LINER_STACK",
                          t_liner_mm=round((self.liner.thickness if self.liner else 0) * 1e3, 2),
                          d_case_i_mm=round(self.case.inner_diameter * 1e3, 2)))

        if self.grain.outer_diameter() > d_li + 1e-9:
            w.append(make("WARN_FIT_GRAIN_DIAMETER",
                          d_grain_mm=round(self.grain.outer_diameter() * 1e3, 2),
                          d_bore_mm=round(d_li * 1e3, 2)))

        available = self.case_tube_length() - self.bulkhead.thickness - self.forward_gap
        conv, throat, _ = self._nozzle_lengths()
        available -= conv + throat + self.aft_gap
        if self.grain.envelope_length() > available + 1e-9:
            w.append(make("WARN_FIT_GRAIN_LENGTH",
                          grain_len_mm=round(self.grain.envelope_length() * 1e3, 2),
                          available_mm=round(max(available, 0.0) * 1e3, 2)))

        if self.nozzle.throat_diameter > self.case.inner_diameter + 1e-9:
            w.append(make("WARN_FIT_THROAT_VS_CASE",
                          d_throat_mm=round(self.nozzle.throat_diameter * 1e3, 2),
                          d_case_i_mm=round(self.case.inner_diameter * 1e3, 2)))

        if self.grain.port_area(0.0) <= 0.0:
            w.append(make("WARN_FIT_PORT_NONPOSITIVE"))

        return w

    def bill_of_materials(self, web: float = 0.0) -> list[dict]:
        """Rows for the BOM table (Section 10.1 pt 8).

        The TOTAL row is the sum of the *displayed* (rounded) part masses so the
        table is internally consistent to the last digit; ``.eng`` / ``.rse`` take
        their header mass from this same figure (acceptance criterion 11).
        """
        rows = []
        for p in self.compute_layout(web):
            rows.append({
                "part": p.name,
                "material_id": p.material_id,
                "length_mm": round(p.length * 1e3, 2),
                "outer_diameter_mm": round(p.outer_diameter * 1e3, 2),
                "inner_diameter_mm": round(p.inner_diameter * 1e3, 2),
                "mass_g": round(p.mass * 1e3, 2),
                "quantity": 1,
            })
        total_g = round(sum(r["mass_g"] for r in rows), 2)
        rows.append({"part": "TOTAL", "material_id": "", "length_mm": None,
                     "outer_diameter_mm": None, "inner_diameter_mm": None,
                     "mass_g": total_g, "quantity": None})
        return rows

    def bom_total_mass(self, web: float = 0.0) -> float:
        """The BOM TOTAL row mass [kg] - the figure exports must use verbatim."""
        return next(r["mass_g"] for r in self.bill_of_materials(web) if r["part"] == "TOTAL") / 1e3
