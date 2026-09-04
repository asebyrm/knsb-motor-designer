"""PDF design report (Section 7.3) via ReportLab.

Layout: cover (logo + designation + disclaimer), input table, geometry section
drawing, 3x3 chart grid (p_c, F, r_b, K_n, mdot, I_t, r_p ~ port radius, r_t, A_b),
result table, warning list, disclaimer. Every page footer carries the attribution
and the "NOT FLIGHT CERTIFIED" note. Rendered in ``tr`` or ``en``.
"""

from __future__ import annotations

import io

import numpy as np
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from core.branding import APP_AUTHOR, APP_NAME, DISCLAIMER_SHORT
from core.export.fonts import register_unicode_fonts
from core.export.model import MotorExportData
from core.i18n import t

_PAGE_W, _PAGE_H = A4

# Registered once per process. Falls back to ASCII-only Helvetica if no Unicode
# TTF is installed, but backend/Dockerfile installs fonts-dejavu-core so the
# deployed report always has Turkish glyphs (ı, ğ, ş, İ, Ğ, Ş).
FONT, FONT_BOLD = register_unicode_fonts()


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(18 * mm, 12 * mm,
                      f"{APP_NAME} - by {APP_AUTHOR}   |   {DISCLAIMER_SHORT}")
    canvas.drawRightString(_PAGE_W - 18 * mm, 12 * mm, f"p. {doc.page}")
    canvas.restoreState()


def _logo_flowable(size: float = 34 * mm) -> Drawing:
    d = Drawing(size, size)
    s = size
    d.add(Line(s * 0.5, s * 0.92, s * 0.92, s * 0.10, strokeColor=colors.black, strokeWidth=1.4))
    d.add(Line(s * 0.92, s * 0.10, s * 0.08, s * 0.10, strokeColor=colors.black, strokeWidth=1.4))
    d.add(Line(s * 0.08, s * 0.10, s * 0.5, s * 0.92, strokeColor=colors.black, strokeWidth=1.4))
    from reportlab.graphics.shapes import Circle

    d.add(Circle(s * 0.5, s * 0.36, s * 0.22, strokeColor=colors.black, fillColor=None,
                 strokeWidth=1.2))
    d.add(String(s * 0.5, s * 0.33, "KNSB", textAnchor="middle", fontSize=s * 0.11,
                 fontName=FONT_BOLD))
    return d


def _panel(title: str, x: np.ndarray, y: np.ndarray, w=58 * mm, h=42 * mm) -> Drawing:
    d = Drawing(w, h)
    lp = LinePlot()
    lp.x, lp.y, lp.width, lp.height = 12, 14, w - 20, h - 24
    step = max(1, len(x) // 120)
    lp.data = [list(zip(x[::step].tolist(), y[::step].tolist(), strict=False))]
    lp.lines[0].strokeColor = colors.HexColor("#1f77b4")
    lp.lines[0].strokeWidth = 1.0
    lp.joinedLines = 1
    d.add(lp)
    d.add(String(2, h - 9, title, fontSize=7, fontName=FONT_BOLD))
    return d


def render_pdf(
    data: MotorExportData,
    ballistics,
    *,
    locale: str = "en",
    input_rows: list[tuple[str, str]] | None = None,
) -> bytes:
    """Return PDF bytes for the given export bundle + ballistics result."""
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                          topMargin=18 * mm, bottomMargin=20 * mm, title=data.display_name)
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="main")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=_footer),
        PageTemplate(id="body", frames=[frame], onPage=_footer),
    ])

    story = []
    h1, h2, normal = styles["Title"], styles["Heading2"], styles["BodyText"]
    for style in (h1, h2, normal, styles["Normal"]):
        style.fontName = FONT
    h1.fontName = h2.fontName = FONT_BOLD

    # --- cover ---
    story.append(_logo_flowable())
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(f"{APP_NAME}", h2))
    story.append(Paragraph(f"{data.display_name} &nbsp; &mdash; &nbsp; {data.propellant_name}", h1))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        f"{t('report.designer', locale)}: {data.designer} &nbsp;&nbsp; "
        f"{t('report.date', locale)}: {data.date_iso}", normal))
    story.append(Spacer(1, 8 * mm))
    safe_txt = t("report.safe", locale) if data.is_safe else t("report.unsafe", locale)
    story.append(Paragraph(f"<b>{t('report.status', locale)}:</b> {safe_txt}", normal))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(t("report.disclaimer_full", locale), normal))
    story.append(NextPageTemplate("body"))
    story.append(PageBreak())

    # --- inputs ---
    story.append(Paragraph(t("report.inputs", locale), h2))
    rows = input_rows or [(k, str(v)) for k, v in (data.design_document or {}).items()]
    if rows:
        tbl = Table([[t("report.parameter", locale), t("report.value", locale)]] + rows,
                    colWidths=[80 * mm, 90 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ]))
        story.append(tbl)
    story.append(Spacer(1, 6 * mm))

    # --- results ---
    story.append(Paragraph(t("report.results", locale), h2))
    res = [
        (t("metric.total_impulse", locale), f"{data.total_impulse_ns:.1f} N·s"),
        (t("metric.average_thrust", locale), f"{data.average_thrust_n:.1f} N"),
        (t("metric.peak_thrust", locale), f"{data.peak_thrust_n:.1f} N"),
        (t("metric.burn_time", locale), f"{data.burn_time_s:.2f} s"),
        (t("metric.peak_pressure", locale),
         f"{ballistics.summary['peak_pressure_no_erosion_bar']:.2f} bar"),
        (t("metric.specific_impulse", locale), f"{data.specific_impulse_s:.1f} s"),
        (t("metric.propellant_mass", locale), f"{data.propellant_mass_kg * 1e3:.1f} g"),
        (t("metric.total_mass", locale), f"{data.total_mass_kg * 1e3:.1f} g"),
        (t("metric.designation", locale), data.designation),
        (t("metric.min_j", locale), f"{ballistics.summary.get('min_j')}"),
        (t("metric.lstar", locale), f"{ballistics.summary['lstar_mm']:.0f} mm"),
    ]
    rtbl = Table([[t("report.metric", locale), t("report.value", locale)]] + res,
                 colWidths=[80 * mm, 90 * mm])
    rtbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
    ]))
    story.append(rtbl)
    story.append(PageBreak())

    # --- 3x3 chart grid ---
    story.append(Paragraph(t("report.curves", locale), h2))
    b = ballistics
    panels = [
        _panel("p_c [bar]", b.time, b.chamber_pressure / 1e5),
        _panel("F [N]", b.time, b.thrust),
        _panel("r_b [mm/s]", b.time, b.burn_rate * 1e3),
        _panel("K_n", b.time, b.kn),
        _panel("mdot [kg/s]", b.time, b.mass_flow),
        _panel("I_t [N·s]", b.time, b.cumulative_impulse),
        _panel("port r [mm]", b.time, np.sqrt(np.maximum(b.port_area, 0) / np.pi) * 1e3),
        _panel("throat r [mm]", b.time, np.sqrt(np.maximum(b.throat_area, 0) / np.pi) * 1e3),
        _panel("A_b [mm²]", b.time, b.burn_area * 1e6),
    ]
    grid = Table([panels[0:3], panels[3:6], panels[6:9]])
    grid.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTRE"),
                              ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(grid)
    story.append(PageBreak())

    # --- warnings ---
    story.append(Paragraph(t("report.warnings", locale), h2))
    if data.warnings:
        wrows = [[w["level"].upper(),
                  t(f"info.warning.{w['code']}", locale),
                  str(w.get("params", {}))]
                 for w in data.warnings]
        wtbl = Table([[t("report.level", locale), t("report.warning", locale),
                       t("report.detail", locale)]] + wrows,
                     colWidths=[22 * mm, 95 * mm, 53 * mm])
        wtbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ]))
        story.append(wtbl)
    else:
        story.append(Paragraph(t("report.no_warnings", locale), normal))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(t("report.disclaimer_full", locale), normal))

    doc.build(story)
    return buf.getvalue()
