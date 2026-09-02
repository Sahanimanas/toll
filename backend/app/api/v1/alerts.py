from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import ROLE_ADMIN, ROLE_OPERATOR, get_current_user, require_roles
from app.db import models
from app.db.session import get_db

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get(
    "",
    response_model=schemas.Page[schemas.AlertOut],
    dependencies=[Depends(get_current_user)],
)
def list_alerts(
    acknowledged: bool | None = None,
    severity: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    page, page_size = max(page, 1), min(max(page_size, 1), 200)
    query = select(models.Alert)
    if acknowledged is not None:
        query = query.where(models.Alert.acknowledged.is_(acknowledged))
    if severity:
        query = query.where(models.Alert.severity == severity)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(models.Alert.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return schemas.Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/{alert_id}/ack", response_model=schemas.AlertOut)
def acknowledge(
    alert_id: int,
    db: Session = Depends(get_db),
    actor=Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
):
    alert = db.get(models.Alert, alert_id)
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    alert.acknowledged = True
    alert.acknowledged_by = actor.id
    db.commit()
    db.refresh(alert)
    return alert
