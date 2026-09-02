from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import get_current_user
from app.db import models
from app.db.session import get_db
from app.services.evidence import resolve_evidence_path

router = APIRouter(
    prefix="/recognitions",
    tags=["recognitions"],
    dependencies=[Depends(get_current_user)],
)


def _to_out(rec: models.Recognition) -> schemas.RecognitionOut:
    out = schemas.RecognitionOut.model_validate(rec)
    out.has_evidence = bool(rec.evidence_path)
    return out


@router.get("", response_model=schemas.Page[schemas.RecognitionOut])
def search_recognitions(
    plate: str | None = None,
    camera_id: int | None = None,
    vehicle_type: str | None = None,
    min_confidence: float | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    page, page_size = max(page, 1), min(max(page_size, 1), 200)
    query = select(models.Recognition)
    if plate:
        query = query.where(
            models.Recognition.plate_text.like(f"%{plate.upper().strip()}%")
        )
    if camera_id is not None:
        query = query.where(models.Recognition.camera_id == camera_id)
    if vehicle_type:
        query = query.where(models.Recognition.vehicle_type == vehicle_type)
    if min_confidence is not None:
        query = query.where(models.Recognition.plate_confidence >= min_confidence)
    if date_from is not None:
        query = query.where(models.Recognition.captured_at >= date_from)
    if date_to is not None:
        query = query.where(models.Recognition.captured_at <= date_to)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(models.Recognition.captured_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return schemas.Page(
        items=[_to_out(r) for r in items], total=total, page=page, page_size=page_size
    )


@router.get("/{recognition_id}", response_model=schemas.RecognitionOut)
def get_recognition(recognition_id: int, db: Session = Depends(get_db)):
    rec = db.get(models.Recognition, recognition_id)
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recognition not found")
    return _to_out(rec)


@router.get("/{recognition_id}/evidence")
def get_evidence(
    recognition_id: int, kind: str = "full", db: Session = Depends(get_db)
):
    rec = db.get(models.Recognition, recognition_id)
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recognition not found")
    rel_path = rec.plate_image_path if kind == "plate" else rec.evidence_path
    if not rel_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No evidence stored")
    path = resolve_evidence_path(rel_path)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence file missing")
    return FileResponse(path, media_type="image/jpeg")
