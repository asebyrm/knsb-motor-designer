"""Export: .eng round-trip + downsampling, .rse structure, CSV/JSON, PDF, drawing.

Covers Section 13.2 (.eng round-trip impulse within 1 %, 32-point downsample within
1 %) and acceptance criteria 6 (FoS < 2 locks export) and 11 (BOM total == .eng
header mass).
"""

from __future__ import annotations

import numpy as np
import pytest

from core.export.eng import parse_eng
from services.export_service import (
    ExportLockedError,
    build_export_data,
    export_csv,
    export_drawing_svg,
    export_eng,
    export_json,
    export_pdf,
    export_rse,
)

GOOD_DESIGN = {
    "name": "T", "prefix": "PARS", "designer": "asb",
    "propellant": {"id": "knsb"},
    "grain": {"type": "bates", "outer_diameter": 0.045, "core_diameter": 0.018,
              "segment_length": 0.075, "segment_count": 3, "segment_spacing": 0.003},
    "nozzle": {"throat_diameter": 0.0115, "expansion_ratio": 5.0, "throat_length": 0.006},
    "case": {"material_id": "pa12", "inner_diameter": 0.052, "wall_thickness": 0.005,
             "print_method": "sls"},
    "liner": {"material_id": "kraft_phenolic", "thickness": 0.003},
    "bulkhead": {"material_id": "pa12", "thickness": 0.010},
    "meop_bar": 45,
}

UNSAFE_DESIGN = {
    **GOOD_DESIGN,
    "case": {"material_id": "pla", "inner_diameter": 0.052, "wall_thickness": 0.0012,
             "print_method": "fdm"},
    "meop_bar": 20,
}


@pytest.fixture(scope="module")
def bundle():
    return build_export_data(GOOD_DESIGN)


def test_eng_header_has_seven_fields(bundle):
    data, ballistics, _ = bundle
    from core.export.eng import render_eng

    header = [ln for ln in render_eng(data).splitlines() if not ln.startswith(";")][0]
    assert len(header.split()) == 7


def test_eng_roundtrip_impulse_within_one_percent(bundle):
    data, ballistics, _ = bundle
    parsed = parse_eng(export_eng(GOOD_DESIGN))
    full = float(np.trapezoid(ballistics.thrust, ballistics.time))
    assert abs(parsed.total_impulse - full) / full < 0.01


def test_eng_downsample_max_32_points_and_ends_at_zero():
    parsed = parse_eng(export_eng(GOOD_DESIGN))
    assert 1 < len(parsed.points) <= 32
    assert parsed.points[-1][1] == 0.0
    assert all(f > 0.0 for _, f in parsed.points[:-1])
    times = [t for t, _ in parsed.points]
    assert times == sorted(times) and len(set(times)) == len(times)


def test_eng_header_mass_matches_bom_total(bundle):
    _, _, ctx = bundle
    parsed = parse_eng(export_eng(GOOD_DESIGN))
    assert parsed.total_mass_kg == pytest.approx(ctx.assembly.bom_total_mass(0.0), abs=1e-4)


def test_rse_is_wellformed_xml():
    import xml.etree.ElementTree as ET

    root = ET.fromstring(export_rse(GOOD_DESIGN))
    assert root.tag == "engine-database"
    eng = root.find("./engine-list/engine")
    assert eng.get("Type") == "single-use"
    assert eng.get("auto-calc-mass") == "0"
    data_rows = eng.findall("./data/eng-data")
    assert len(data_rows) >= 2
    assert all({"t", "f", "m", "cg"} <= set(r.keys()) for r in data_rows)


def test_csv_full_resolution(bundle):
    _, ballistics, _ = bundle
    csv_text = export_csv(GOOD_DESIGN)
    body = [ln for ln in csv_text.splitlines() if ln][1:]
    assert len(body) == ballistics.time.size          # not downsampled
    assert csv_text.splitlines()[0].startswith("time_s,")


def test_json_is_versioned_and_reimportable():
    import json

    doc = json.loads(export_json(GOOD_DESIGN))
    assert doc["schema_version"] >= 1
    assert doc["design"]["grain"]["type"] == "bates"
    assert "summary" in doc and "warnings" in doc


def test_pdf_renders_bytes():
    pdf = export_pdf(GOOD_DESIGN, locale="tr")
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 3000


def test_drawing_svg_is_svg():
    svg = export_drawing_svg(GOOD_DESIGN)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert "scale 1 :" in svg


def test_unsafe_design_locks_eng_and_rse():
    """Acceptance 6: FoS < 2 -> export blocked unless risk explicitly accepted."""
    data, _, _ = build_export_data(UNSAFE_DESIGN)
    assert data.blocking_codes()
    with pytest.raises(ExportLockedError):
        export_eng(UNSAFE_DESIGN)
    with pytest.raises(ExportLockedError):
        export_rse(UNSAFE_DESIGN)
    # override works
    assert export_eng(UNSAFE_DESIGN, accept_risk=True).startswith(";")
    # non-safety formats are always allowed
    assert export_json(UNSAFE_DESIGN)
