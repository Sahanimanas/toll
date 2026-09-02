"""Read/report endpoints: transactions, audit, violations, report, nms,
equipment-history, dashboard, notifications."""

import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.toll import models
from app.toll.api.deps import auth_required
from app.toll.nms import build_equipment_history, build_nms
from app.toll.reports import build_report

router = APIRouter(dependencies=[Depends(auth_required)])


# ---------- transactions ----------

def _txn_out(t: models.TollTransaction) -> dict:
    return {"id": t.id, "date": t.date, "time": t.time, "lane": t.lane,
            "reg": t.reg, "cls": t.cls, "tag": t.tag, "speed": t.speed,
            "amount": t.amount, "mode": t.mode, "status": t.status,
            "plate_image": t.plate_image, "confidence": t.confidence}


@router.get("/api/transactions")
def transactions(
    db: Session = Depends(get_db),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = None, lane: str | None = None, cls: str | None = None,
    status: str | None = None, reg: str | None = None, txn: str | None = None,
):
    q = select(models.TollTransaction)
    if from_:
        q = q.where(models.TollTransaction.date >= from_)
    if to:
        q = q.where(models.TollTransaction.date <= to)
    if lane and lane != "All Lanes":
        q = q.where(models.TollTransaction.lane == lane)
    if cls and cls != "All Classes":
        q = q.where(models.TollTransaction.cls == cls)
    if status and status != "All Status":
        q = q.where(models.TollTransaction.status == status)
    if reg:
        q = q.where(func.upper(models.TollTransaction.reg).like(f"%{reg.upper()}%"))
    if txn:
        q = q.where(models.TollTransaction.id.like(f"%{txn.upper()}%"))
    rows = db.scalars(q.order_by(models.TollTransaction.ts.desc())).all()
    return {"total": len(rows), "items": [_txn_out(t) for t in rows]}


# ---------- audit ----------

def _audit_out(r: models.ReconRow) -> dict:
    return {"aid": r.aid, "txn": r.txn, "vrn": r.vrn, "amount": r.amount,
            "bank": r.bank, "ref": r.ref, "sent": r.sent, "settled": r.settled,
            "tagBal": r.tag_bal, "status": r.status}


@router.get("/api/audit")
def audit(
    db: Session = Depends(get_db),
    status: str | None = None, bank: str | None = None,
    date: str | None = None, q: str | None = None,
):
    rows = db.scalars(select(models.ReconRow)).all()
    if status and status != "All Status":
        rows = [r for r in rows if r.status == status]
    if bank and bank != "All Banks":
        rows = [r for r in rows if r.bank == bank]
    if date:
        rows = [r for r in rows if r.sent.startswith(date)]
    if q:
        Q = q.upper()
        rows = [r for r in rows if Q in r.txn or Q in r.vrn.upper() or Q in (r.ref or "").upper()]
    return {"total": len(rows), "items": [_audit_out(r) for r in rows]}


@router.post("/api/audit/{aid}/retry")
def audit_retry(aid: str, db: Session = Depends(get_db)):
    r = db.get(models.ReconRow, aid)
    if r is None:
        raise HTTPException(404, "Not found")
    r.status = "Success"
    r.ref = "NPCI" + str(8000000000 + random.randint(0, 9999)).zfill(10)
    r.settled = r.sent
    r.tag_bal = "₹" + str(1000 + random.randint(0, 499))
    db.commit()
    return _audit_out(r)


@router.post("/api/audit/resync-failed")
def audit_resync(db: Session = Depends(get_db)):
    failed = db.scalars(select(models.ReconRow).where(models.ReconRow.status == "Failed")).all()
    for r in failed:
        r.status = "Success"
        r.ref = "NPCI" + str(8000000000 + random.randint(0, 9999)).zfill(10)
        r.settled = r.sent
        r.tag_bal = "₹" + str(1000 + random.randint(0, 499))
    db.commit()
    return {"count": len(failed)}


# ---------- violations ----------

def _vio_out(v: models.Violation) -> dict:
    return {"id": v.id, "vrn": v.vrn, "date": v.date, "time": v.time,
            "lane": v.lane, "type": v.type, "speed": v.speed, "fine": v.fine,
            "status": v.status}


@router.get("/api/violations")
def violations(db: Session = Depends(get_db), type: str | None = None, q: str | None = None):
    rows = db.scalars(select(models.Violation)).all()
    if type and type != "All Types":
        rows = [v for v in rows if v.type == type]
    if q:
        rows = [v for v in rows if q.upper() in v.vrn.upper()]
    return {"total": len(rows), "items": [_vio_out(v) for v in rows]}


@router.patch("/api/violations/{vid}")
async def violation_patch(vid: str, request: Request, db: Session = Depends(get_db)):
    v = db.get(models.Violation, vid)
    if v is None:
        raise HTTPException(404, "Not found")
    body = await request.json()
    if body.get("status"):
        v.status = body["status"]
    db.commit()
    return _vio_out(v)


# ---------- report ----------

@router.get("/api/report")
def report(type: str | None = None, from_: str | None = Query(default=None, alias="from"),
           to: str | None = None, lane: str | None = None, cls: str | None = None,
           shift: str | None = None):
    if not type:
        raise HTTPException(400, "type required")
    out = build_report(type, from_ or "", to or "", lane or "", cls or "", shift or "")
    out["generatedAt"] = int(datetime.now(timezone.utc).timestamp() * 1000)
    return out


# ---------- nms / equipment ----------

@router.get("/api/nms")
def nms():
    return build_nms()


@router.get("/api/equipment-history")
def equipment_history(
    from_: str | None = Query(default=None, alias="from"), to: str | None = None,
    equipment: str | None = None, lane: str | None = None,
    cls: str | None = None, reg: str | None = None,
):
    if not from_ or not to or not equipment or equipment == "— Select Equipment —":
        raise HTTPException(400, "Date From, Date To and Equipment are required")
    items = build_equipment_history(from_, to, equipment, lane or "", cls or "", reg or "")
    return {"total": len(items), "items": items}


# ---------- dashboard ----------

def _anpr_stats(db: Session) -> dict:
    rows = db.scalars(select(models.TollTransaction)).all()
    stats = {"total": len(rows), "revenue": 0, "paid": 0, "violations": 0,
             "failed": 0, "exempted": 0}
    for t in rows:
        stats["revenue"] += t.amount or 0
        if t.status == "Paid":
            stats["paid"] += 1
        elif t.status == "Violation":
            stats["violations"] += 1
        elif t.status == "Failed":
            stats["failed"] += 1
        elif t.status == "Exempted":
            stats["exempted"] += 1
    return stats


_DASHBOARD_BLOB = {
    "kpis": {
        "revenue": "₹24.8L", "revenueDelta": "+12.4%", "vehicles": "12,840",
        "vehiclesDelta": "+8.2%", "transactions": "12,284", "transactionsDelta": "+6.1%",
        "violations": 556, "violationsDelta": "-3.2%", "activeLanes": "4 / 4",
        "failed": 38, "failedDelta": "-18.4%",
    },
    "hourly": [620, 780, 540, 690, 880, 1020, 1240, 1380, 940],
    "revenueTrend": [3.1, 3.4, 3.6, 3.2, 3.7, 3.9, 4.1],
    "classes": [
        {"name": "Car / Jeep", "value": 38, "color": "#2a4cdb"},
        {"name": "LCV / Mini Bus", "value": 23, "color": "#5fa8e8"},
        {"name": "Bus / Truck", "value": 16, "color": "#5cc26a"},
        {"name": "3-Axle Vehicle", "value": 11, "color": "#e8a52f"},
        {"name": "Over Sized", "value": 12, "color": "#e0464b"},
    ],
    "equipment": [
        {"name": "Camera", "ic": "📷", "total": 9, "active": 8, "inactive": 1},
        {"name": "RFID", "ic": "📡", "total": 5, "active": 4, "inactive": 1},
        {"name": "RADAR", "ic": "▣", "total": 4, "active": 4, "inactive": 0},
        {"name": "LiDAR", "ic": "⚡", "total": 4, "active": 3, "inactive": 1},
        {"name": "ANPR", "ic": "☷", "total": 9, "active": 7, "inactive": 2},
        {"name": "Lane Controllers", "ic": "🚦", "total": 4, "active": 4, "inactive": 0},
    ],
    "lanes": [
        {"name": "Lane 1 — Entry", "vh": 342, "rev": "₹84.2K", "status": "Active", "state": "ok"},
        {"name": "Lane 2 — Entry", "vh": 298, "rev": "₹71.6K", "status": "Active", "state": "ok"},
        {"name": "Lane 3 — Exit", "vh": 226, "rev": "₹54.4K", "status": "Active", "state": "ok"},
        {"name": "Lane 4 — Exit", "vh": 0, "rev": "₹0", "status": "Offline", "state": "err"},
    ],
    "laneEquip": [
        {"dir": "LHS", "lane": "Lane 1", "anpr": 1, "rfid": 1, "radar": 1, "lidar": 1, "lc": 1, "status": ["healthy", "Healthy"]},
        {"dir": "LHS", "lane": "Lane 2", "anpr": 1, "rfid": 1, "radar": 1, "lidar": 0, "lc": 1, "status": ["degraded", "Degraded"]},
        {"dir": "RHS", "lane": "Lane 3", "anpr": 1, "rfid": 0, "radar": 1, "lidar": 1, "lc": 1, "status": ["degraded", "Degraded"]},
        {"dir": "RHS", "lane": "Lane 4", "anpr": 0, "rfid": 1, "radar": 0, "lidar": 0, "lc": 1, "status": ["critical", "Critical"]},
        {"dir": "MID", "lane": "Mid-1", "anpr": 1, "rfid": 1, "radar": 1, "lidar": 1, "lc": 1, "status": ["healthy", "Healthy"]},
    ],
}


@router.get("/api/dashboard")
def dashboard():
    return _DASHBOARD_BLOB


def _fmt_rev(v: int) -> str:
    return ("₹" + f"{v/100000:.1f}" + "L") if v >= 100000 else ("₹" + f"{v:,}")


@router.get("/api/dashboard/live")
def dashboard_live(db: Session = Depends(get_db)):
    s = _anpr_stats(db)
    return {
        "ts": int(datetime.now(timezone.utc).timestamp() * 1000),
        "kpis": {
            "revenue": {"value": _fmt_rev(s["revenue"]), "delta": 0},
            "vehicles": {"value": f"{s['total']:,}", "delta": 0},
            "txn": {"value": f"{s['paid']:,}", "delta": 0},
            "violations": {"value": str(s["violations"]), "delta": 0},
            "lanes": {"value": "4 / 4", "delta": 100},
            "failed": {"value": str(s["failed"]), "delta": 0},
        },
    }


@router.get("/api/dashboard/panels")
def dashboard_panels(db: Session = Depends(get_db)):
    s = _anpr_stats(db)
    labels = ["00", "03", "06", "09", "12", "15", "18", "21"]
    buckets = [0] * 8
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    rows = db.scalars(select(models.TollTransaction)).all()
    recent = [t for t in rows if t.ts and t.ts.replace(tzinfo=timezone.utc) >= cutoff] if rows else []
    src = recent or rows
    for t in src:
        if t.ts:
            buckets[min(7, t.ts.hour // 3)] += 1
    peak_lbl = labels[buckets.index(max(buckets))] + ":00" if any(buckets) else "00:00"

    # accuracy per lane (avg confidence)
    conf_by_lane: dict[str, list[float]] = {}
    for t in rows:
        if t.confidence is not None:
            conf_by_lane.setdefault(t.lane or "Lane 1", []).append(t.confidence)
    acc_labels = list(conf_by_lane.keys()) or ["Lane 1"]
    anpr_acc = [round(sum(v) / len(v) * 100, 1) for v in conf_by_lane.values()] or [0]
    rfid_acc = [min(100, v + 6) for v in anpr_acc]
    avg_anpr = sum(anpr_acc) / (len(anpr_acc) or 1)

    total = s["total"] or 1

    def pct(n):
        return f"{(n/total)*100:.1f}%"

    notifs = db.scalars(
        select(models.Notification).order_by(models.Notification.id.desc()).limit(5)
    ).all()
    alerts = [{
        "type": "err" if n.kind == "error" else ("warn" if n.kind == "warn" else "ok"),
        "ic": "📷" if n.kind == "error" else ("⚠" if n.kind == "warn" else "✓"),
        "title": n.title, "sub": n.body,
        "time": n.time.isoformat() if n.time else "",
    } for n in notifs]

    return {
        "volume": {k: {"data": buckets, "labels": labels, "peak": peak_lbl, "delta": 0, "total": s["total"]}
                   for k in ["Hourly", "Daily", "Last 7 Days", "Weekly", "Monthly"]},
        "accuracy": {"rfid": rfid_acc, "anpr": anpr_acc, "labels": acc_labels,
                     "avgRfid": round(min(100, avg_anpr + 6), 1), "avgAnpr": round(avg_anpr, 1)},
        "eticket": [
            {"type": "ok", "ic": "✓", "title": "Accepted", "sub": "Paid via FASTag / valid tags",
             "num": f"{s['paid']:,}", "pct": pct(s["paid"]), "color": "var(--green)"},
            {"type": "err", "ic": "✕", "title": "Rejected", "sub": "Violation — no tag / blacklisted",
             "num": f"{s['violations']:,}", "pct": pct(s["violations"]), "color": "var(--red)"},
            {"type": "warn", "ic": "!", "title": "Exempted", "sub": "Govt / emergency vehicles",
             "num": f"{s['exempted']:,}", "pct": pct(s["exempted"]), "color": "var(--amber)"},
        ],
        "alerts": alerts,
        "revenue": {"total": _fmt_rev(s["revenue"]),
                    "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]},
    }


# ---------- notifications ----------

_NOTIF_TEMPLATES = [
    ("error", "HARDWARE DOWN: Boom Barrier", "Motor fault detected in Boom Barrier at Lane 3. Gate is stuck open."),
    ("error", "Traffic Light Malfunction", "Overhead Lane Signal at Lane 1 is unresponsive. Stuck on RED."),
    ("warn", "High CPU Utilization", "Plaza Server CPU running at 98% utilization. Frames processing delayed."),
    ("warn", "Camera Feed Degraded", "ANPR Camera at Lane 4 dropping frames. Check network link."),
    ("error", "RFID Reader Offline", "RFID reader at Lane 2 not responding. Last seen 4 minutes ago."),
    ("info", "Daily Sync Completed", "Transaction reconciliation with NPCI completed. 12,284 records."),
    ("warn", "Disk Space Low", "Edge node /var partition at 87%. Archive older recordings."),
    ("error", "LiDAR Sensor Drift", "Lane 3 LiDAR reporting outside calibration tolerance."),
]


def _ensure_notifs(db: Session):
    if db.scalar(select(func.count(models.Notification.id))):
        return
    now = datetime.now(timezone.utc)
    for i, (kind, title, body) in enumerate(_NOTIF_TEMPLATES):
        db.add(models.Notification(kind=kind, title=title, body=body,
                                   time=now - timedelta(minutes=i + 1), read=False))
    db.commit()


@router.get("/api/notifications")
def notifications(db: Session = Depends(get_db)):
    _ensure_notifs(db)
    rows = db.scalars(select(models.Notification).order_by(models.Notification.id.desc())).all()
    items = [{"id": n.id, "kind": n.kind, "title": n.title, "body": n.body,
              "time": n.time.isoformat() if n.time else "", "read": n.read} for n in rows]
    return {"unread": sum(1 for n in rows if not n.read), "items": items}


@router.post("/api/notifications/read-all")
def notifications_read_all(db: Session = Depends(get_db)):
    for n in db.scalars(select(models.Notification)).all():
        n.read = True
    db.commit()
    return {"ok": True}


@router.post("/api/notifications/clear")
def notifications_clear(db: Session = Depends(get_db)):
    for n in db.scalars(select(models.Notification)).all():
        db.delete(n)
    db.commit()
    return {"ok": True}
