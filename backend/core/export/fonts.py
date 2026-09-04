"""Register a Unicode-capable TTF font pair for the PDF report.

ReportLab's built-in "Helvetica"/"Helvetica-Bold" use WinAnsiEncoding, which does
**not** include the Turkish-specific letters (dotless ı, İ, ğ, Ğ, ş, Ş) - they
silently render as a missing-glyph box. Those characters appear throughout the TR
locale (parameter labels, warning text, the disclaimer), so the PDF report needs a
real Unicode font. ö/ü/ç are in WinAnsi and were never affected.

We try a short list of fonts that are either installed by
``backend/Dockerfile`` (``fonts-dejavu-core``) or commonly present on a dev
machine, and fall back to Helvetica (ASCII-safe, but Turkish glyphs will be
missing) if none exist - the report must never fail to render because a font is
absent.
"""

from __future__ import annotations

import os
from functools import lru_cache

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FAMILY = "AppSans"

# (regular path, bold path or None to reuse the regular face)
_CANDIDATES: list[tuple[str, str | None]] = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
     "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
    ("/Library/Fonts/Arial Unicode.ttf", None),
    ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None),
]


@lru_cache(maxsize=1)
def register_unicode_fonts() -> tuple[str, str]:
    """Register the first available TTF pair; returns ``(regular, bold)`` font names.

    Also registers the ``AppSans`` font *family* so ``<b>...</b>`` markup inside
    ReportLab ``Paragraph`` text resolves to the bold face instead of silently
    falling back to Helvetica.
    """
    for regular_path, bold_path in _CANDIDATES:
        if not os.path.exists(regular_path):
            continue
        resolved_bold = bold_path if bold_path and os.path.exists(bold_path) else regular_path
        try:
            pdfmetrics.registerFont(TTFont(FAMILY, regular_path))
            pdfmetrics.registerFont(TTFont(f"{FAMILY}-Bold", resolved_bold))
            pdfmetrics.registerFontFamily(
                FAMILY, normal=FAMILY, bold=f"{FAMILY}-Bold",
                italic=FAMILY, boldItalic=f"{FAMILY}-Bold",
            )
            return FAMILY, f"{FAMILY}-Bold"
        except Exception:  # pragma: no cover - a broken font file, try the next
            continue
    return "Helvetica", "Helvetica-Bold"  # ASCII-only fallback; never raises
