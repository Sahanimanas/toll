import logging

from sqlalchemy.orm import Session

from app.db import models

logger = logging.getLogger(__name__)


def audit(db: Session, user_id: int | None, action: str, resource: str, detail: dict) -> None:
    """Record a mutating action. Never blocks the main operation on failure."""
    detail = {k: v for k, v in detail.items() if k != "password"}
    try:
        db.add(
            models.AuditLog(
                user_id=user_id, action=action, resource=resource, detail=detail
            )
        )
        db.commit()
    except Exception:  # pragma: no cover - defensive
        logger.exception("failed to write audit log for %s %s", action, resource)
        db.rollback()
