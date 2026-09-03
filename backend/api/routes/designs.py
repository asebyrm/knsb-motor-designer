"""Design save / list / update / delete / fork / public share (Section 8)."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db, get_optional_user
from api.schemas import DesignIn, DesignOut
from models.entities import Design, User

router = APIRouter(prefix="/designs", tags=["designs"])


def _out(d: Design) -> DesignOut:
    return DesignOut(
        id=d.id, name=d.name, description=d.description, config_json=d.config_json,
        visibility=d.visibility, slug=d.slug, fork_of_id=d.fork_of_id,
        owner_username=d.owner.username if d.owner else None,
        created_at=d.created_at.isoformat(), updated_at=d.updated_at.isoformat(),
    )


def _slug() -> str:
    return secrets.token_urlsafe(9)[:12]


@router.get("", response_model=list[DesignOut])
def list_mine(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(Design).where(Design.owner_id == user.id)
                      .order_by(Design.updated_at.desc())).all()
    return [_out(d) for d in rows]


@router.post("", response_model=DesignOut, status_code=201)
def create(body: DesignIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = Design(owner_id=user.id, name=body.name, description=body.description,
               config_json=body.config_json, visibility=body.visibility,
               schema_version=int(body.config_json.get("schema_version", 1)),
               slug=_slug() if body.visibility != "private" else None)
    db.add(d)
    db.commit()
    db.refresh(d)
    return _out(d)


@router.get("/{design_id}", response_model=DesignOut)
def get_one(design_id: str, db: Session = Depends(get_db),
            user: User | None = Depends(get_optional_user)):
    d = db.get(Design, design_id)
    if not d:
        raise HTTPException(404, "not found")
    if d.visibility == "private" and (not user or user.id != d.owner_id):
        raise HTTPException(404, "not found")
    return _out(d)


@router.put("/{design_id}", response_model=DesignOut)
def update(design_id: str, body: DesignIn, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    d = db.get(Design, design_id)
    if not d or d.owner_id != user.id:
        raise HTTPException(404, "not found")
    d.name, d.description = body.name, body.description
    d.config_json, d.visibility = body.config_json, body.visibility
    if body.visibility != "private" and not d.slug:
        d.slug = _slug()
    db.add(d)
    db.commit()
    db.refresh(d)
    return _out(d)


@router.delete("/{design_id}", status_code=204)
def delete(design_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = db.get(Design, design_id)
    if not d or d.owner_id != user.id:
        raise HTTPException(404, "not found")
    db.delete(d)
    db.commit()


@router.post("/{design_id}/fork", response_model=DesignOut, status_code=201)
def fork(design_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    src = db.get(Design, design_id)
    if not src or (src.visibility == "private" and src.owner_id != user.id):
        raise HTTPException(404, "not found")
    d = Design(owner_id=user.id, name=f"{src.name} (fork)", description=src.description,
               config_json=src.config_json, visibility="private",
               schema_version=src.schema_version, fork_of_id=src.id)
    db.add(d)
    db.commit()
    db.refresh(d)
    return _out(d)


# public read-only share link: /api/d/{slug}
public_router = APIRouter(tags=["designs"])


@public_router.get("/d/{slug}", response_model=DesignOut)
def by_slug(slug: str, db: Session = Depends(get_db)):
    d = db.scalar(select(Design).where(Design.slug == slug))
    if not d or d.visibility == "private":
        raise HTTPException(404, "not found")
    return _out(d)
