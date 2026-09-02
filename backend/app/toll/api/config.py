"""Configuration CRUD: rfid-config, toll-rates, lanes, system-settings,
system-users, thresholds, anpr-cameras."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.toll import models
from app.toll.api.deps import auth_required
from app.toll.service import get_setting, set_setting

router = APIRouter(dependencies=[Depends(auth_required)])

RESOLUTIONS = ["4K UHD", "1440P", "1080P", "720P", "480P"]


def _clamp(v, lo, hi):
    try:
        return max(lo, min(hi, int(float(v))))
    except (TypeError, ValueError):
        return lo


# ---------- rfid-config + rates ----------

def _rate_out(r: models.TollRate) -> dict:
    return {"id": r.id, "key": r.key, "label": r.label, "sub": r.sub,
            "icon": r.icon, "amount": r.amount}


@router.get("/api/rfid-config")
def get_rfid(db: Session = Depends(get_db)):
    rates = db.scalars(select(models.TollRate).order_by(models.TollRate.id)).all()
    return {"rfid": get_setting(db, "rfid_config", {}), "rates": [_rate_out(r) for r in rates]}


@router.put("/api/rfid-config")
async def put_rfid(request: Request, db: Session = Depends(get_db)):
    b = await request.json()
    r = dict(get_setting(db, "rfid_config", {}) or {})
    if "npciHost" in b:      r["npciHost"] = str(b["npciHost"])
    if "timeoutMs" in b:     r["timeoutMs"] = _clamp(b["timeoutMs"], 100, 60000)
    if "readRatePct" in b:   r["readRatePct"] = _clamp(b["readRatePct"], 0, 100)
    if "retryAttempts" in b: r["retryAttempts"] = _clamp(b["retryAttempts"], 0, 10)
    if "autoBlacklist" in b: r["autoBlacklist"] = bool(b["autoBlacklist"])
    if "dedupFilter" in b:   r["dedupFilter"] = bool(b["dedupFilter"])
    return set_setting(db, "rfid_config", r)


@router.put("/api/toll-rates/{rid}")
async def put_rate(rid: int, request: Request, db: Session = Depends(get_db)):
    rate = db.get(models.TollRate, rid)
    if rate is None:
        raise HTTPException(404, "not found")
    b = await request.json()
    if b.get("amount") is not None:
        rate.amount = _clamp(b["amount"], 0, 100000)
    if b.get("label") is not None:
        rate.label = str(b["label"])
    if b.get("sub") is not None:
        rate.sub = str(b["sub"])
    db.commit()
    return _rate_out(rate)


# ---------- lanes ----------

def _lane_out(l: models.Lane) -> dict:
    return {"id": l.id, "name": l.name, "direction": l.direction, "speed": l.speed,
            "headway": l.headway, "toll": l.toll, "active": l.active}


@router.get("/api/lanes")
def get_lanes(db: Session = Depends(get_db)):
    return [_lane_out(l) for l in db.scalars(select(models.Lane).order_by(models.Lane.id)).all()]


@router.put("/api/lanes/{lid}")
async def put_lane(lid: int, request: Request, db: Session = Depends(get_db)):
    l = db.get(models.Lane, lid)
    if l is None:
        raise HTTPException(404, "not found")
    b = await request.json()
    if b.get("name") is not None:      l.name = str(b["name"])
    if b.get("direction") is not None: l.direction = "Exit" if b["direction"] == "Exit" else "Entry"
    if b.get("speed") is not None:     l.speed = _clamp(b["speed"], 0, 200)
    if b.get("headway") is not None:   l.headway = _clamp(b["headway"], 0, 500)
    if b.get("toll") is not None:      l.toll = _clamp(b["toll"], 0, 100000)
    if b.get("active") is not None:    l.active = bool(b["active"])
    db.commit()
    return _lane_out(l)


# ---------- system settings ----------

@router.get("/api/system-settings")
def get_system_settings(db: Session = Depends(get_db)):
    return get_setting(db, "system_settings", {})


@router.put("/api/system-settings")
async def put_system_settings(request: Request, db: Session = Depends(get_db)):
    b = await request.json()
    s = dict(get_setting(db, "system_settings", {}) or {})
    g = dict(s.get("general", {}))
    f = dict(s.get("features", {}))
    if isinstance(b.get("general"), dict):
        bg = b["general"]
        if bg.get("plazaName") is not None:     g["plazaName"] = str(bg["plazaName"])
        if bg.get("plazaCode") is not None:     g["plazaCode"] = str(bg["plazaCode"])
        if bg.get("timeZone") is not None:      g["timeZone"] = str(bg["timeZone"])
        if bg.get("retentionDays") is not None: g["retentionDays"] = _clamp(bg["retentionDays"], 1, 3650)
        if bg.get("reportEmail") is not None:   g["reportEmail"] = str(bg["reportEmail"])
    if isinstance(b.get("features"), dict):
        for k in ["autoViolation", "bankSync", "cctvRecording", "nightMode",
                  "smsAlerts", "maintenance", "debugLogging"]:
            if b["features"].get(k) is not None:
                f[k] = bool(b["features"][k])
    s["general"], s["features"] = g, f
    return set_setting(db, "system_settings", s)


# ---------- system users (over toll_users) ----------

def _project_user(u: models.TollUser) -> dict:
    username = u.username or (u.email.split("@")[0] if u.email else (u.name or "user").lower().replace(" ", "."))
    return {"id": u.id, "name": u.name or "", "username": username,
            "role": u.role or "Operator", "email": u.email or "",
            "last": u.last or "—", "status": u.status or "Active"}


def _apply_user_patch(u: models.TollUser, b: dict):
    if b.get("name") is not None:     u.name = str(b["name"])
    if b.get("username") is not None: u.username = str(b["username"])
    if b.get("role") is not None:     u.role = str(b["role"])
    if b.get("email") is not None:    u.email = str(b["email"])
    if b.get("status") is not None:   u.status = "Inactive" if b["status"] == "Inactive" else "Active"
    if b.get("last") is not None:     u.last = str(b["last"])


@router.get("/api/system-users")
def get_system_users(db: Session = Depends(get_db)):
    return [_project_user(u) for u in db.scalars(select(models.TollUser)).all()]


@router.post("/api/system-users")
async def post_system_user(request: Request, db: Session = Depends(get_db)):
    b = await request.json()
    u = models.TollUser(id=str(uuid.uuid4()), role="Operator", status="Active",
                        last="—", plaza="NH-48 Gurugram", color="#2563eb")
    _apply_user_patch(u, b)
    db.add(u)
    db.commit()
    return _project_user(u)


@router.put("/api/system-users/{uid}")
async def put_system_user(uid: str, request: Request, db: Session = Depends(get_db)):
    u = db.get(models.TollUser, uid)
    if u is None:
        raise HTTPException(404, "not found")
    _apply_user_patch(u, await request.json())
    db.commit()
    return _project_user(u)


@router.delete("/api/system-users/{uid}")
def delete_system_user(uid: str, db: Session = Depends(get_db)):
    u = db.get(models.TollUser, uid)
    if u is None:
        raise HTTPException(404, "not found")
    db.delete(u)
    db.commit()
    return {"ok": True}


# ---------- thresholds + comm ----------

@router.get("/api/thresholds")
def get_thresholds(db: Session = Depends(get_db)):
    return {"thresholds": get_setting(db, "thresholds", {}), "comm": get_setting(db, "comm", {})}


@router.put("/api/thresholds")
async def put_thresholds(request: Request, db: Session = Depends(get_db)):
    b = await request.json()
    t = dict(get_setting(db, "thresholds", {}) or {})
    c = dict(get_setting(db, "comm", {}) or {})
    if isinstance(b.get("thresholds"), dict):
        bt = b["thresholds"]
        if bt.get("speedKmh") is not None:          t["speedKmh"] = _clamp(bt["speedKmh"], 40, 100)
        if bt.get("violationPct") is not None:      t["violationPct"] = _clamp(bt["violationPct"], 1, 20)
        if bt.get("failedTxn") is not None:         t["failedTxn"] = _clamp(bt["failedTxn"], 1, 50)
        if bt.get("cameraDowntimeMin") is not None: t["cameraDowntimeMin"] = _clamp(bt["cameraDowntimeMin"], 1, 30)
        if bt.get("rfidReadRatePct") is not None:   t["rfidReadRatePct"] = _clamp(bt["rfidReadRatePct"], 80, 100)
        if bt.get("pingTimeoutMs") is not None:     t["pingTimeoutMs"] = _clamp(bt["pingTimeoutMs"], 50, 500)
    if isinstance(b.get("comm"), dict):
        bc = b["comm"]
        if bc.get("alertEmails") is not None:        c["alertEmails"] = str(bc["alertEmails"])
        if bc.get("smsNumbers") is not None:         c["smsNumbers"] = str(bc["smsNumbers"])
        if bc.get("webhookUrl") is not None:         c["webhookUrl"] = str(bc["webhookUrl"])
        if bc.get("emailAlertsEnabled") is not None: c["emailAlertsEnabled"] = bool(bc["emailAlertsEnabled"])
    set_setting(db, "thresholds", t)
    set_setting(db, "comm", c)
    return {"thresholds": t, "comm": c}


# ---------- anpr-cameras ----------

def _anpr_cam_out(c: models.AnprCameraCfg) -> dict:
    return {"id": c.id, "kind": c.kind, "lane": c.lane, "role": c.role,
            "label": c.label, "zone": c.zone, "ip": c.ip,
            "resolution": c.resolution, "framerate": c.framerate, "active": c.active}


def _sanitize_anpr(b: dict, cam: models.AnprCameraCfg):
    if b.get("kind") is not None:       cam.kind = "Surveillance" if b["kind"] == "Surveillance" else "ANPR"
    if b.get("lane") is not None:       cam.lane = str(b["lane"])
    if b.get("role") is not None:       cam.role = "Rear" if b["role"] == "Rear" else "Front"
    if b.get("label") is not None:      cam.label = str(b["label"])
    if b.get("zone") is not None:       cam.zone = str(b["zone"])
    if b.get("ip") is not None:         cam.ip = str(b["ip"])
    if b.get("resolution") is not None: cam.resolution = str(b["resolution"])
    if b.get("framerate") is not None:  cam.framerate = _clamp(b["framerate"], 1, 120)
    if b.get("active") is not None:     cam.active = bool(b["active"])


@router.get("/api/anpr-cameras")
def get_anpr_cameras(db: Session = Depends(get_db)):
    items = db.scalars(select(models.AnprCameraCfg).order_by(models.AnprCameraCfg.id)).all()
    return {"items": [_anpr_cam_out(c) for c in items], "resolutions": RESOLUTIONS}


@router.post("/api/anpr-cameras")
async def post_anpr_camera(request: Request, db: Session = Depends(get_db)):
    cam = models.AnprCameraCfg(lane="Lane 1", role="Front", ip="",
                               resolution="1080P", framerate=25, active=True)
    _sanitize_anpr(await request.json(), cam)
    db.add(cam)
    db.commit()
    return _anpr_cam_out(cam)


@router.put("/api/anpr-cameras/{cid}")
async def put_anpr_camera(cid: int, request: Request, db: Session = Depends(get_db)):
    cam = db.get(models.AnprCameraCfg, cid)
    if cam is None:
        raise HTTPException(404, "not found")
    _sanitize_anpr(await request.json(), cam)
    db.commit()
    return _anpr_cam_out(cam)


@router.delete("/api/anpr-cameras/{cid}")
def delete_anpr_camera(cid: int, db: Session = Depends(get_db)):
    cam = db.get(models.AnprCameraCfg, cid)
    if cam is None:
        raise HTTPException(404, "not found")
    db.delete(cam)
    db.commit()
    return {"ok": True}
