"""Assembly: layout, total length/mass/CG, free volume, fit validation."""

from __future__ import annotations

import pytest

from core.assembly import BulkheadSpec, CaseSpec, LinerSpec, MotorAssembly
from core.grains.bates import BatesGrain
from core.materials import load_case_material, load_liner_material
from core.nozzle import Nozzle
from core.propellant import load_propellant


def _assembly(**over):
    prop = load_propellant("knsb")
    cm = load_case_material(over.get("case_mat", "pa12"))
    lm = load_liner_material("kraft_phenolic")
    grain = over.get("grain", BatesGrain(0.045, 0.018, 0.09, segment_count=3,
                                         segment_spacing=0.003))
    nozzle = over.get("nozzle", Nozzle(throat_diameter=0.012, expansion_ratio=5.0,
                                       throat_length=0.006))
    return MotorAssembly(
        grain=grain, propellant=prop, nozzle=nozzle,
        case=CaseSpec(cm, over.get("d_ci", 0.055), over.get("t_wall", 0.004)),
        bulkhead=BulkheadSpec(cm, 0.010),
        liner=LinerSpec(lm, over.get("t_liner", 0.003)),
    )


def test_layout_is_ordered_and_contiguous_ish():
    a = _assembly()
    parts = {p.name: p for p in a.compute_layout(0.0)}
    assert set(parts) >= {"bulkhead", "liner", "grain", "case", "nozzle"}
    assert parts["bulkhead"].x_start == 0.0
    assert parts["grain"].x_start >= parts["bulkhead"].x_end
    assert parts["nozzle"].x_start >= parts["grain"].x_end


def test_total_mass_equals_sum_of_parts():
    a = _assembly()
    parts = a.compute_layout(0.0)
    assert a.total_mass(0.0) == pytest.approx(sum(p.mass for p in parts))


def test_bom_total_matches_total_mass():
    """Section 10.1 pt 8 / acceptance 11: BOM total == .eng header mass."""
    a = _assembly()
    bom = a.bill_of_materials(0.0)
    total_row = next(r for r in bom if r["part"] == "TOTAL")
    part_rows = [r for r in bom if r["part"] != "TOTAL"]
    assert total_row["mass_g"] == round(sum(r["mass_g"] for r in part_rows), 2)
    assert a.bom_total_mass(0.0) == total_row["mass_g"] / 1e3
    assert total_row["mass_g"] == pytest.approx(a.total_mass(0.0) * 1e3, rel=1e-3)


def test_mass_and_cg_shift_as_propellant_burns():
    a = _assembly()
    m0 = a.total_mass(0.0)
    m1 = a.total_mass(a.grain.web_thickness())
    assert m1 < m0
    assert a.inert_mass() == pytest.approx(m1)
    # CG moves (grain is not perfectly centred on the whole motor)
    assert a.center_of_gravity(0.0) != pytest.approx(a.center_of_gravity(a.grain.web_thickness()))


def test_free_volume_grows_as_grain_burns():
    a = _assembly()
    assert a.free_volume(a.grain.web_thickness()) > a.free_volume(0.0) > 0


def test_fit_ok_for_reasonable_design():
    a = _assembly()
    assert a.validate_fit() == []


def test_fit_flags_oversized_grain_diameter():
    a = _assembly(grain=BatesGrain(0.060, 0.020, 0.08, segment_count=2))  # > bore
    codes = {w.code for w in a.validate_fit()}
    assert "WARN_FIT_GRAIN_DIAMETER" in codes


def test_fit_flags_throat_bigger_than_case():
    a = _assembly(nozzle=Nozzle(throat_diameter=0.070, expansion_ratio=3.0))
    codes = {w.code for w in a.validate_fit()}
    assert "WARN_FIT_THROAT_VS_CASE" in codes


def test_characteristic_length_positive():
    a = _assembly()
    assert 50.0 < a.characteristic_length() * 1e3 < 5000.0
