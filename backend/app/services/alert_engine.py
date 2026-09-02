"""Rule engine: evaluates a freshly ingested recognition and raises alerts.

Rules implemented:
- watchlist: exact match on normalized plate text against active entries.
- speed: recognition speed exceeds the camera's configured speed_limit_kmh.

Alerts are added to the session but not committed; the caller owns the
transaction so recognition + alerts persist atomically.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models

logger = logging.getLogger(__name__)


def evaluate_alerts(
    db: Session, rec: models.Recognition, camera: models.Camera
) -> list[models.Alert]:
    alerts: list[models.Alert] = []

    entries = db.scalars(
        select(models.WatchlistEntry).where(
            models.WatchlistEntry.plate_text == rec.plate_text,
            models.WatchlistEntry.is_active.is_(True),
        )
    ).all()
    for entry in entries:
        alerts.append(
            models.Alert(
                recognition_id=rec.id,
                watchlist_id=entry.id,
                type="watchlist",
                severity=entry.severity,
                message=(
                    f"Watchlist hit: {rec.plate_text} at {camera.name}"
                    + (f" — {entry.reason}" if entry.reason else "")
                ),
            )
        )

    speed_limit = (camera.config or {}).get("speed_limit_kmh")
    if speed_limit is not None and rec.speed_kmh is not None:
        try:
            limit = float(speed_limit)
        except (TypeError, ValueError):
            logger.warning("camera %s has invalid speed_limit_kmh %r", camera.id, speed_limit)
            limit = None
        if limit is not None and rec.speed_kmh > limit:
            overshoot = rec.speed_kmh - limit
            severity = "critical" if overshoot > limit * 0.5 else "high"
            alerts.append(
                models.Alert(
                    recognition_id=rec.id,
                    type="speed",
                    severity=severity,
                    message=(
                        f"Speed violation: {rec.plate_text} at {rec.speed_kmh:.0f} km/h "
                        f"(limit {limit:.0f}) on {camera.name}"
                    ),
                )
            )

    for alert in alerts:
        db.add(alert)
    return alerts
