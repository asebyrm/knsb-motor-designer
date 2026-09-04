"""Export endpoint - one route, format chosen by the request body (Section 7)."""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from api.deps import get_db, get_optional_user, rate_limit
from api.schemas import ExportRequest
from app_config import get_settings
from models.entities import ExportLog
from services.export_service import (
    ExportLockedError,
    export_csv,
    export_drawing_svg,
    export_eng,
    export_json,
    export_nozzle_contour_csv,
    export_pdf,
    export_rse,
)

router = APIRouter(prefix="/export", tags=["export"])
_settings = get_settings()

_MEDIA = {
    "eng": "text/plain", "rse": "application/xml", "csv": "text/csv",
    "json": "application/json", "pdf": "application/pdf", "svg": "image/svg+xml",
    "nozzle_csv": "text/csv",
}
_EXT = {"eng": "eng", "rse": "rse", "csv": "csv", "json": "json", "pdf": "pdf",
        "svg": "svg", "nozzle_csv": "csv"}


def _content_disposition(filename: str) -> str:
    """Build a Content-Disposition header that survives a design name with
    non-Latin1 characters (e.g. Turkish İ/ı/ş/ğ) - header values must be
    latin-1 encodable, so a raw Unicode filename crashes Response.init_headers
    (UnicodeEncodeError -> 500) if passed through directly. RFC 6266: send an
    ASCII-transliterated fallback in `filename=` plus the exact name, percent
    encoded, in `filename*=UTF-8''...` for clients that honour it."""
    ascii_fallback = (
        unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
    )
    ascii_fallback = re.sub(r'[^A-Za-z0-9._-]', "_", ascii_fallback) or "motor"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


@router.post("", dependencies=[Depends(rate_limit("export", 60))])
def export(req: ExportRequest, db: Session = Depends(get_db), user=Depends(get_optional_user)):
    try:
        if req.fmt == "eng":
            payload: bytes | str = export_eng(req.design, accept_risk=req.accept_risk)
        elif req.fmt == "rse":
            payload = export_rse(req.design, accept_risk=req.accept_risk)
        elif req.fmt == "csv":
            payload = export_csv(req.design)
        elif req.fmt == "json":
            payload = export_json(req.design)
        elif req.fmt == "pdf":
            payload = export_pdf(req.design, locale=req.locale)
        elif req.fmt == "svg":
            payload = export_drawing_svg(req.design)
        elif req.fmt == "nozzle_csv":
            payload = export_nozzle_contour_csv(req.design)
        else:  # pragma: no cover - schema guards this
            raise HTTPException(400, "unknown format")
    except ExportLockedError as exc:
        raise HTTPException(423, str(exc)) from exc  # 423 Locked
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, f"invalid design: {exc}") from exc

    db.add(ExportLog(user_id=user.id if user else None, fmt=req.fmt,
                     design_id=req.design.get("id")))
    db.commit()

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = str(req.design.get("name") or "motor").replace(" ", "_")
    filename = f"{name}-{stamp}.{_EXT[req.fmt]}"
    body = payload if isinstance(payload, bytes) else payload.encode("utf-8")
    return Response(content=body, media_type=_MEDIA[req.fmt],
                    headers={"Content-Disposition": _content_disposition(filename)})
