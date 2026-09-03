"""Dimensioned longitudinal-section SVG of a motor assembly (Section 10.1).

Backend renderer used by the PDF report and the "download technical drawing" button.
The interactive, click-to-edit version in the frontend is separate but reads the same
``MotorAssembly`` layout so the numbers match.

Conventions:
* half-section above the axis, mirrored below for the visible outline;
* every dimension carries arrowheads + a label; input dimensions are solid, derived
  ones (web, total length, L*) are dashed and use the secondary colour;
* the drawing scale (e.g. ``1 : 2.4``) is printed in the corner.
"""

from __future__ import annotations

from core.assembly import MotorAssembly

_MARGIN = 90
_CANVAS_W = 900


def _fmt(v_mm: float) -> str:
    return f"{v_mm:.1f}"


def _dim_line(x1, y1, x2, y2, label, *, derived=False, above=True):
    colour = "var(--dim-derived,#8a8a8a)" if derived else "var(--dim,#333)"
    dash = ' stroke-dasharray="4 3"' if derived else ""
    mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
    dy = -6 if above else 14
    return (
        f'<g stroke="{colour}" stroke-width="0.6" fill="{colour}" font-size="11">'
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"{dash}/>'
        f'<path d="M{x1:.1f},{y1:.1f} l6,-3 v6 z"/>'
        f'<path d="M{x2:.1f},{y2:.1f} l-6,-3 v6 z"/>'
        f'<text x="{mid_x:.1f}" y="{mid_y + dy:.1f}" text-anchor="middle" '
        f'stroke="none">{label}</text>'
        f"</g>"
    )


def render_dimensioned_svg(assembly: MotorAssembly, web: float = 0.0) -> str:
    """Return a standalone ``<svg>`` string."""
    parts = assembly.compute_layout(web)
    total_len_m = assembly.total_length()
    max_od_m = max(p.outer_diameter for p in parts)

    draw_w = _CANVAS_W - 2 * _MARGIN
    scale = draw_w / total_len_m                      # px per metre
    canvas_h = int(max_od_m * scale) + 2 * _MARGIN + 120
    axis_y = _MARGIN + max_od_m * scale / 2

    def sx(x_m: float) -> float:
        return _MARGIN + x_m * scale

    def sy_up(d_m: float) -> float:
        return axis_y - d_m / 2 * scale

    def sy_dn(d_m: float) -> float:
        return axis_y + d_m / 2 * scale

    body: list[str] = []
    # axis centre line
    body.append(
        f'<line x1="{_MARGIN - 20}" y1="{axis_y}" x2="{_CANVAS_W - _MARGIN + 20}" '
        f'y2="{axis_y}" stroke="var(--axis,#bbb)" stroke-width="0.6" '
        f'stroke-dasharray="8 3 2 3"/>'
    )

    fit_codes = {w.code for w in assembly.validate_fit()}
    part_bad = {
        "grain": {"WARN_FIT_GRAIN_DIAMETER", "WARN_FIT_GRAIN_LENGTH"},
        "nozzle": {"WARN_FIT_THROAT_VS_CASE"},
        "liner": {"WARN_FIT_LINER_STACK"},
    }
    for p in parts:
        bad = bool(part_bad.get(p.name, set()) & fit_codes)
        stroke = "var(--error,#d33)" if bad else "currentColor"
        x1, x2 = sx(p.x_start), sx(p.x_end)
        yo1, yo2 = sy_up(p.outer_diameter), sy_dn(p.outer_diameter)
        body.append(
            f'<rect x="{x1:.1f}" y="{yo1:.1f}" width="{x2 - x1:.1f}" '
            f'height="{yo2 - yo1:.1f}" fill="none" stroke="{stroke}" stroke-width="1.1"/>'
        )
        if p.inner_diameter > 0:
            yi1, yi2 = sy_up(p.inner_diameter), sy_dn(p.inner_diameter)
            body.append(
                f'<rect x="{x1:.1f}" y="{yi1:.1f}" width="{x2 - x1:.1f}" '
                f'height="{yi2 - yi1:.1f}" fill="none" stroke="{stroke}" '
                f'stroke-width="0.7" opacity="0.7"/>'
            )
        body.append(
            f'<text x="{(x1 + x2) / 2:.1f}" y="{axis_y + 4:.1f}" text-anchor="middle" '
            f'font-size="10" fill="var(--dim-derived,#8a8a8a)">{p.name}</text>'
        )

    # key dimensions
    dim_y_top = _MARGIN - 40
    body.append(_dim_line(sx(0), dim_y_top, sx(total_len_m), dim_y_top,
                          f"L_total {_fmt(total_len_m * 1e3)} mm", derived=True))
    grain = next((p for p in parts if p.name == "grain"), None)
    if grain:
        gy = sy_up(grain.outer_diameter) - 22
        body.append(_dim_line(sx(grain.x_start), gy, sx(grain.x_end), gy,
                              f"grain L {_fmt((grain.x_end - grain.x_start) * 1e3)} mm"))
    case = next((p for p in parts if p.name == "case"), None)
    if case:
        cx = sx(case.x_end) + 34
        body.append(_dim_line(cx, sy_up(case.outer_diameter), cx, sy_dn(case.outer_diameter),
                              f"D_case_o {_fmt(case.outer_diameter * 1e3)} mm", above=False))
        cx2 = sx(case.x_end) + 16
        body.append(_dim_line(cx2, sy_up(case.inner_diameter), cx2, sy_dn(case.inner_diameter),
                              f"D_case_i {_fmt(case.inner_diameter * 1e3)} mm", above=False))
    noz = next((p for p in parts if p.name == "nozzle"), None)
    if noz:
        nx = sx(noz.x_end) + 14
        body.append(_dim_line(nx, sy_up(assembly.nozzle.throat_diameter),
                              nx, sy_dn(assembly.nozzle.throat_diameter),
                              f"D_t {_fmt(assembly.nozzle.throat_diameter * 1e3)} mm",
                              above=False))
        nx2 = sx(noz.x_end) + 30
        body.append(_dim_line(nx2, sy_up(assembly.nozzle.exit_diameter),
                              nx2, sy_dn(assembly.nozzle.exit_diameter),
                              f"D_e {_fmt(assembly.nozzle.exit_diameter * 1e3)} mm",
                              above=False))

    ratio = (total_len_m * 1000.0) / draw_w  # real mm per drawn px
    body.append(
        f'<text x="{_MARGIN}" y="{canvas_h - 24}" font-size="12" '
        f'fill="var(--dim,#333)">scale 1 : {ratio:.2f}   '
        f'(dashed = derived / not editable)</text>'
    )
    body.append(
        f'<text x="{_MARGIN}" y="{canvas_h - 8}" font-size="10" '
        f'fill="var(--dim-derived,#8a8a8a)">L* {_fmt(assembly.characteristic_length() * 1e3)} mm'
        f'   inert mass {_fmt(assembly.inert_mass() * 1e3)} g'
        f'   loaded mass {_fmt(assembly.total_mass(web) * 1e3)} g</text>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_CANVAS_W} {canvas_h}" '
        f'font-family="system-ui, sans-serif" stroke="currentColor">'
        + "".join(body) +
        "</svg>"
    )
