"""Acceptance criterion 8: a new propellant is a YAML file, zero core code change.

Also checks the grain registry accepts a new geometry via ``@register_grain`` only.
"""

from __future__ import annotations

import math

from core.grains.base import GrainGeometry, available_grains, make_grain, register_grain
from core.propellant import available_propellants, load_propellant
from services.simulation_service import run_simulation


def test_kndx_available_from_yaml_only():
    assert "kndx" in available_propellants()
    kndx = load_propellant("kndx")
    assert kndx.id == "kndx"
    assert kndx.gamma == 1.1308
    # burn-rate law works through the same code path as KNSB
    r_b = kndx.burn_rate(2.0e6)   # 2 MPa -> row 2, a=7.553, n=-0.009
    assert r_b == __import__("pytest").approx(7.553 * 2.0**-0.009 / 1000.0, rel=1e-9)


def test_kndx_runs_full_simulation_unchanged_core():
    design = {
        "name": "KNDX test", "propellant": {"id": "kndx"},
        "grain": {"type": "bates", "outer_diameter": 0.045, "core_diameter": 0.018,
                  "segment_length": 0.08, "segment_count": 3, "segment_spacing": 0.003},
        "nozzle": {"throat_diameter": 0.012, "expansion_ratio": 5.0},
        "case": {"material_id": "pa12", "inner_diameter": 0.052, "wall_thickness": 0.005},
        "liner": {"material_id": "kraft_phenolic", "thickness": 0.003},
        "bulkhead": {"material_id": "pa12", "thickness": 0.010},
        "meop_bar": 50,
    }
    out = run_simulation(design)
    assert out["summary"]["total_impulse"] > 0
    assert out["summary"]["designation"]


def test_new_grain_geometry_via_decorator_only():
    """A geometry needs only subclass + @register_grain - no engine edits."""

    if "slab" not in available_grains():
        @register_grain("slab")
        class _Slab(GrainGeometry):
            def __init__(self, outer_diameter: float, length: float):
                self.d, self.l = outer_diameter, length

            def burn_area(self, web): return math.pi * (self.d / 2) ** 2
            def volume(self, web): return math.pi * (self.d / 2) ** 2 * max(self.l - web, 0)
            def port_area(self, web): return math.pi * (self.d / 2) ** 2
            def web_thickness(self): return self.l
            def outer_diameter(self): return self.d
            def envelope_length(self): return self.l
            def cross_section_svg(self, web): return "<g/>"
            def validate(self): return []

    g = make_grain("slab", outer_diameter=0.04, length=0.1)
    assert g.web_thickness() == 0.1
    assert g.burn_area(0.0) > 0
