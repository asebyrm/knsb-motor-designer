"""Grain geometry: BATES neutrality, web thickness, volume/area consistency."""

from __future__ import annotations

import math

import numpy as np
import pytest

from core.grains.base import available_grains, make_grain
from core.grains.bates import BatesGrain, suggest_neutral_segment_length
from core.grains.endburner import EndBurnerGrain
from core.grains.tubular import TubularGrain


def test_registry_has_builtin_geometries():
    assert set(available_grains()) >= {"bates", "tubular", "endburner"}
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
