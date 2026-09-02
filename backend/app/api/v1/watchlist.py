from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import ROLE_ADMIN, ROLE_OPERATOR, get_current_user, require_roles
from app.db import models
from app.db.session import get_db
from app.services.audit import audit

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get(
    "",
    response_model=schemas.Page[schemas.WatchlistOut],
    dependencies=[Depends(get_current_user)],
)
def list_watchlist(page: int = 1, page_size: int = 100, db: Session = Depends(get_db)):
    page, page_size = max(page, 1), min(max(page_size, 1), 500)
    total = db.scalar(select(func.count(models.WatchlistEntry.id))) or 0
    items = db.scalars(
        select(models.WatchlistEntry)
        .order_by(models.WatchlistEntry.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return schemas.Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=schemas.WatchlistOut, status_code=201)
def add_entry(
    body: schemas.WatchlistCreate,
    db: Session = Depends(get_db),
    actor=Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
):
    entry = models.WatchlistEntry(
        plate_text=body.plate_text.upper().strip(),
        reason=body.reason,
        severity=body.severity,
        is_active=body.is_active,
        created_by=actor.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    audit(db, actor.id, "watchlist.add", f"watchlist/{entry.id}", {"plate": entry.plate_text})
    return entry


@router.delete("/{entry_id}", status_code=204)
def remove_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    actor=Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
):
    entry = db.get(models.WatchlistEntry, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found")
    entry.is_active = False
    db.commit()
    audit(db, actor.id, "watchlist.deactivate", f"watchlist/{entry_id}", {})
