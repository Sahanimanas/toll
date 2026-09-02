from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import get_current_user
from app.db import models
from app.db.session import get_db

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(get_current_user)])


@router.get("/summary", response_model=schemas.StatsSummary)
def summary(db: Session = Depends(get_db)):
    today_start = datetime.combine(
        datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc
    )
    recognitions_today = (
        db.scalar(
            select(func.count(models.Recognition.id)).where(
                models.Recognition.captured_at >= today_start
            )
        )
        or 0
    )
    recognitions_total = db.scalar(select(func.count(models.Recognition.id))) or 0
    open_alerts = (
        db.scalar(
            select(func.count(models.Alert.id)).where(
                models.Alert.acknowledged.is_(False)
            )
        )
        or 0
    )
    active_cameras = (
        db.scalar(
            select(func.count(models.Camera.id)).where(models.Camera.is_active.is_(True))
        )
        or 0
    )
    per_camera_rows = db.execute(
        select(models.Camera.name, func.count(models.Recognition.id))
        .join(models.Recognition, models.Recognition.camera_id == models.Camera.id)
        .where(models.Recognition.captured_at >= today_start)
        .group_by(models.Camera.name)
    ).all()
    return schemas.StatsSummary(
        recognitions_today=recognitions_today,
        recognitions_total=recognitions_total,
        open_alerts=open_alerts,
        active_cameras=active_cameras,
        per_camera_today={name: count for name, count in per_camera_rows},
    )
