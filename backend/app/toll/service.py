"""Toll business logic: rate lookup, FASTag deduction, and the
recognition -> transaction hook that bridges the ANPR pipeline to tolling.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.toll import models
from app.toll.sse import broadcast

logger = logging.getLogger(__name__)

# Fallback rates if the toll_rates table is empty/unseeded.
TOLL_BY_CLASS_FALLBACK = {
    "Car / Jeep": 185, "LCV": 285, "Bus": 445, "3-Axle": 685, "Oversized": 985,
}

# Map vehicle-class strings -> toll_rates.key.
CLASS_TO_RATE_KEY = {
    "Car / Jeep": "car", "car": "car",
    "LCV": "lcv", "lcv": "lcv",
    "Bus": "bus", "bus": "bus", "Truck": "bus", "truck": "bus",
    "3-Axle": "axle3", "4-6 Axle": "axle46", "Oversized": "oversize",
}

# Map pipeline vehicle_type (COCO-ish) -> toll display class.
VEHICLE_TYPE_TO_CLASS = {
    "car": "Car / Jeep", "motorcycle": "Car / Jeep", "motorbike": "Car / Jeep",
    "bus": "Bus", "truck": "Bus", "unknown": "Car / Jeep",
}

_PLATE_GRAMMAR = re.compile(r"^([A-Z]{2})(\d{1,2})([A-Z]{1,3})(\d{3,4})$")


def normalize_plate(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def format_plate(text: str) -> str:
    """Render 'HR26AA1000' as 'HR26 AA 1000' for display; leave others as-is."""
    norm = normalize_plate(text)
    m = _PLATE_GRAMMAR.match(norm)
    if m:
        return f"{m.group(1)}{m.group(2)} {m.group(3)} {m.group(4)}"
    return norm


# ---------- settings KV helpers ----------

def get_setting(db: Session, key: str, default=None):
    row = db.get(models.TollSetting, key)
    return row.value if row is not None else default


def set_setting(db: Session, key: str, value: dict) -> dict:
    row = db.get(models.TollSetting, key)
    if row is None:
        row = models.TollSetting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()
    return value


# ---------- rate + fastag ----------

def toll_amount_for(db: Session, cls: str) -> int:
    key = CLASS_TO_RATE_KEY.get(cls)
    if key:
        rate = db.scalar(select(models.TollRate).where(models.TollRate.key == key))
        if rate and rate.amount:
            return rate.amount
    # fallback: match by label substring
    for rate in db.scalars(select(models.TollRate)).all():
        if cls and cls.lower() in (rate.label or "").lower():
            return rate.amount
    return TOLL_BY_CLASS_FALLBACK.get(cls, TOLL_BY_CLASS_FALLBACK["Car / Jeep"])


def find_fastag(db: Session, plate: str) -> models.FastagAccount | None:
    """Match a FASTag account by normalized plate (space/format insensitive)."""
    target = normalize_plate(plate)
    for acct in db.scalars(select(models.FastagAccount)).all():
        if normalize_plate(acct.plate) == target:
            return acct
    return None


def _next_txn_id(db: Session) -> str:
    # Fixed-width zero-padded ids -> lexical max == numeric max. Order by id
    # (not ts): the latest-ts row is not necessarily the highest-numbered one.
    row = db.scalar(
        select(models.TollTransaction.id).order_by(models.TollTransaction.id.desc()).limit(1)
    )
    n = max(int(re.sub(r"\D", "", row)) + 1, 10200001) if row else 10200001
    return "TXN" + str(n).zfill(8)


def deduct_toll(
    db: Session,
    *,
    plate: str,
    cls: str,
    lane: str,
    speed: int = 0,
    plate_image: str | None = None,
    confidence: float | None = None,
    recognition_id: int | None = None,
) -> dict:
    """Resolve rate, apply FASTag rules, persist a transaction, upsert vehicle.

    FASTag rules mirror the original toll-plaza logic:
      no account -> Violation; blacklisted or low balance -> Failed;
      else deduct -> Paid.
    """
    amount = toll_amount_for(db, cls)
    acct = find_fastag(db, plate)

    mode, status, tag = "Violation", "Violation", None
    if acct is None:
        mode, status = "Violation", "Violation"
    elif acct.status == "Blacklisted":
        mode, status, tag = "FASTag", "Failed", acct.tag_id
    elif acct.balance < amount:
        mode, status, tag = "FASTag", "Failed", acct.tag_id
    else:
        acct.balance -= amount
        acct.updated_at = datetime.now(timezone.utc)
        mode, status, tag = "FASTag", "Paid", acct.tag_id

    now = datetime.now(timezone.utc)
    txn_id = _next_txn_id(db)
    reg = format_plate(plate)
    txn = models.TollTransaction(
        id=txn_id,
        ts=now,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S"),
        lane=lane,
        reg=reg,
        cls=cls,
        tag=tag,
        speed=speed or 0,
        amount=amount,
        mode=mode,
        status=status,
        plate_image=plate_image,
        confidence=confidence,
        recognition_id=recognition_id,
    )
    db.add(txn)

    # upsert vehicle
    veh = db.scalar(select(models.Vehicle).where(models.Vehicle.plate == reg))
    if veh is None:
        db.add(models.Vehicle(plate=reg, cls=cls, last_seen=now))
    else:
        veh.cls, veh.last_seen = cls, now
    db.commit()

    return {
        "id": txn_id,
        "date": txn.date,
        "time": txn.time,
        "lane": lane,
        "reg": reg,
        "cls": cls,
        "tag": tag,
        "speed": speed or 0,
        "amount": amount,
        "mode": mode,
        "status": status,
        "plate_image": plate_image,
        "confidence": confidence,
        "balance": max(0, acct.balance) if acct else None,
    }


# ---------- notifications ----------

def push_notif(db: Session, kind: str, title: str, body: str = "") -> None:
    db.add(models.Notification(kind=kind, title=title, body=body))
    db.commit()


# ---------- pipeline bridge ----------

def _save_plate_image(plate_bytes: bytes | None, plate: str, txn_hint: str) -> str | None:
    if not plate_bytes:
        return None
    settings = get_settings()
    plates_dir = Path(settings.toll_storage_dir) / "plates"
    plates_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9]", "", plate) or "plate"
    fname = f"{safe}-{txn_hint}.jpg"
    (plates_dir / fname).write_bytes(plate_bytes)
    return f"/storage/plates/{fname}"


def on_recognition(db: Session, rec, camera, plate_bytes: bytes | None = None) -> None:
    """Convert an ingested recognition into a toll transaction + SSE push.

    Called from the ingest endpoint after the Recognition row is committed.
    Never raises into the ingest path — failures are logged and swallowed so a
    tolling bug can't break recognition storage.
    """
    try:
        lane = getattr(camera, "lane", "") or "Lane 1"
        cls = VEHICLE_TYPE_TO_CLASS.get(
            (rec.vehicle_type or "unknown").lower(), "Car / Jeep"
        )
        speed = int(rec.speed_kmh) if rec.speed_kmh else 0
        plate_image = _save_plate_image(plate_bytes, rec.plate_text, str(rec.id))

        broadcast("detect", {
            "plate": format_plate(rec.plate_text),
            "lane": lane,
            "camera_id": rec.camera_id,
            "ts": int(datetime.now(timezone.utc).timestamp() * 1000),
            "confidence": rec.plate_confidence,
        })

        txn = deduct_toll(
            db,
            plate=rec.plate_text,
            cls=cls,
            lane=lane,
            speed=speed,
            plate_image=plate_image,
            confidence=rec.plate_confidence,
            recognition_id=rec.id,
        )
        broadcast("transaction", txn)

        # speed threshold notification
        thresholds = get_setting(db, "thresholds", {}) or {}
        limit = thresholds.get("speedKmh")
        if limit and speed > int(limit):
            push_notif(
                db, "warn", "Speed Threshold Exceeded",
                f"Vehicle {txn['reg']} on {lane} clocked {speed} km/h (limit {limit}).",
            )
    except Exception:  # noqa: BLE001 — never break ingest
        logger.exception("toll on_recognition hook failed for recognition %s", getattr(rec, "id", "?"))
