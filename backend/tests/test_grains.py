"""Grain geometry: BATES neutrality, web thickness, volume/area consistency."""

from __future__ import annotations

import math

import numpy as np
import pytest

from core.grains.base import available_grains, make_grain
from core.grains.bates import BatesGrain, suggest_neutral_segment_length
from core.grains.endburner import EndBurnerGrain
from core.grains.rod_tube import RodTubeGrain
from core.grains.star import StarGrain
from core.grains.tubular import TubularGrain
from core.grains.wagon_wheel import WagonWheelGrain


def test_registry_has_builtin_geometries():
    assert set(available_grains()) >= {
        "bates", "tubular", "endburner", "star", "wagon_wheel", "rod_tube",
    }
    g = make_grain("bates", outer_diameter=0.05, core_diameter=0.02,
                   segment_length=0.1, segment_count=2)
    assert isinstance(g, BatesGrain)


def test_bates_web_thickness_rule():
    g = BatesGrain(0.050, 0.020, 0.120)      # radial-limited
    assert g.web_thickness() == pytest.approx((0.050 - 0.020) / 2)
    g2 = BatesGrain(0.050, 0.020, 0.020)     # length-limited
    assert g2.web_thickness() == pytest.approx(0.020 / 2)


def test_bates_neutral_segment_length_is_neutral():
    """Section 13.2: A_b(0) vs A_b(web) differ by < 2 % at the suggested length."""
    d_o, d = 0.075, 0.025
    l_s = suggest_neutral_segment_length(d_o, d)
    g = BatesGrain(d_o, d, l_s, segment_count=1)
    web = g.web_thickness()
    a0, a_end = g.burn_area(0.0), g.burn_area(web * 0.999)
    assert abs(a_end - a0) / a0 < 0.02
    # closed-form cross-check L_s = (3 D_o + d) / 2
    assert l_s == pytest.approx((3 * d_o + d) / 2, rel=0.05)


def test_bates_volume_matches_area_integral():
    """d(Volume)/d(web) == -burn_area(web) (regression identity)."""
    g = BatesGrain(0.060, 0.020, 0.100, segment_count=3)
    web = np.linspace(0, g.web_thickness() * 0.999, 400)
    vol = np.array([g.volume(x) for x in web])
    area = np.array([g.burn_area(x) for x in web])
    dvol = -np.gradient(vol, web)
    # compare on the interior where gradients are clean
    sl = slice(5, -5)
    assert np.allclose(dvol[sl], area[sl], rtol=0.02, atol=area.max() * 0.01)


def test_bates_multisegment_scales_linearly():
    one = BatesGrain(0.05, 0.02, 0.08, segment_count=1)
    three = BatesGrain(0.05, 0.02, 0.08, segment_count=3)
    assert three.burn_area(0.003) == pytest.approx(3 * one.burn_area(0.003))
    assert three.volume(0.0) == pytest.approx(3 * one.volume(0.0))


def test_tubular_is_progressive_and_warns():
    g = TubularGrain(outer_diameter=0.08, core_diameter=0.03, length=0.15)
    assert g.burn_area(g.web_thickness() * 0.99) > g.burn_area(0.0)
    codes = {w.code for w in g.validate()}
    assert "WARN_PROGRESSIVE_GEOMETRY" in codes


def test_endburner_area_is_constant():
    g = EndBurnerGrain(outer_diameter=0.04, length=0.2)
    assert g.burn_area(0.0) == pytest.approx(g.burn_area(0.15))
    assert g.burn_area(0.0) == pytest.approx(math.pi * 0.02**2)
    assert "WARN_ENDBURNER_THERMAL_SOAK" in {w.code for w in g.validate()}


def test_bates_rejects_bad_dimensions():
    with pytest.raises(ValueError):
        BatesGrain(0.02, 0.03, 0.1)          # core >= outer
    with pytest.raises(ValueError):
        BatesGrain(0.05, 0.02, -0.1)         # negative length


def test_bates_svg_is_wellformed():
    g = BatesGrain(0.05, 0.02, 0.08)
    svg = g.cross_section_svg(0.003)
    assert svg.startswith("<g") and svg.endswith("</g>")
    assert "circle" in svg


# --- star / wagon-wheel / rod-and-tube (Section 5.2 extension) ---------------


def test_star_volume_matches_area_integral():
    """Same regression identity as BATES: -dV/dweb == burn_area(web), this time for
    a polygon-offset (numeric, not closed-form) geometry."""
    g = StarGrain(outer_diameter=0.06, core_diameter=0.015, point_diameter=0.045,
                  length=0.1, n_points=6)
    web = np.linspace(0, g.web_thickness() * 0.98, 200)
    vol = np.array([g.volume(x) for x in web])
    area = np.array([g.burn_area(x) for x in web])
    dvol = -np.gradient(vol, web)
    sl = slice(5, -5)
    assert np.allclose(dvol[sl], area[sl], rtol=0.05, atol=area.max() * 0.02)


def test_star_burns_out_to_zero():
    g = StarGrain(outer_diameter=0.06, core_diameter=0.015, point_diameter=0.045,
                  length=0.1, n_points=6)
    assert g.burn_area(g.web_thickness()) == pytest.approx(0.0, abs=1e-6)
    assert g.volume(g.web_thickness()) == pytest.approx(0.0, abs=1e-9)


def test_star_rejects_bad_radii_order():
    with pytest.raises(ValueError):
        StarGrain(0.06, 0.05, 0.03, 0.1)  # point_diameter < core_diameter


def test_wagon_wheel_volume_matches_area_integral():
    g = WagonWheelGrain(outer_diameter=0.06, core_diameter=0.012, point_diameter=0.045,
                        length=0.1, n_points=4)
    web = np.linspace(0, g.web_thickness() * 0.98, 200)
    vol = np.array([g.volume(x) for x in web])
    area = np.array([g.burn_area(x) for x in web])
    dvol = -np.gradient(vol, web)
    sl = slice(5, -5)
    assert np.allclose(dvol[sl], area[sl], rtol=0.05, atol=area.max() * 0.02)


def test_rod_tube_is_neutral_when_balanced():
    """Rod web == tube web -> burn area should stay essentially flat throughout,
    the classic rod-and-tube "top hat" curve."""
    g = RodTubeGrain(outer_diameter=0.05, core_diameter=0.020, point_diameter=0.030,
                     length=0.1)  # rod web = 10mm, tube web = 25-15 = 10mm
    a0 = g.burn_area(0.0)
    a_mid = g.burn_area(g.web_thickness() * 0.5)
    a_end = g.burn_area(g.web_thickness() * 0.999)
    assert a_mid == pytest.approx(a0, rel=0.01)
    assert a_end == pytest.approx(a0, rel=0.05)


def test_rod_tube_volume_matches_area_integral():
    g = RodTubeGrain(outer_diameter=0.05, core_diameter=0.012, point_diameter=0.030,
                     length=0.1)
    web = np.linspace(0, g.web_thickness() * 0.999, 400)
    vol = np.array([g.volume(x) for x in web])
    area = np.array([g.burn_area(x) for x in web])
    dvol = -np.gradient(vol, web)
    sl = slice(5, -5)
    assert np.allclose(dvol[sl], area[sl], rtol=0.02, atol=area.max() * 0.01)


def test_rod_tube_rejects_bad_dimensions():
    with pytest.raises(ValueError):
        RodTubeGrain(0.05, 0.06, 0.03, 0.1)   # rod bigger than the case
    with pytest.raises(ValueError):
        RodTubeGrain(0.05, 0.02, 0.06, 0.1)   # tube bore bigger than the case
