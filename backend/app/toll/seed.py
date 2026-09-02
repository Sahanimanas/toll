"""Idempotent toll-domain seed: rates, lanes, FASTag accounts, users, config
blobs, camera-config rows, a demo video camera for the pipeline, and sample
transactions/audit/violations so the frontend pages aren't empty on first run.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db import models as core_models
from app.toll import models
from app.toll.paths import DEMO_VIDEO, demo_video_path

logger = logging.getLogger(__name__)


def _pad(n, w=2):
    return str(int(n)).zfill(w)


def _plate(seed: int) -> str:
    P = ["HR26", "DL01", "MH04", "UP32", "PB10", "GJ01", "RJ14", "KA09",
         "TN22", "WB04", "KL07", "BR05"]
    p = P[seed % len(P)]
    ll = chr(65 + (seed * 3) % 26) + chr(65 + (seed * 7) % 26)
    return f"{p} {ll} {1000 + (seed * 131) % 9000}"


def _date_of(i: int) -> str:
    months = [("01", 31), ("02", 28), ("03", 31)]
    m = months[i % 3]
    return f"2025-{m[0]}-{_pad(1 + (i*7) % m[1])}"


def _seed_rates(db: Session):
    if db.scalar(select(func.count(models.TollRate.id))):
        return
    rows = [
        ("car", "Car / Jeep", "2-axle", "🚗", 185),
        ("lcv", "LCV / Mini Bus", "2-axle light", "🚐", 285),
        ("bus", "Bus / Truck", "2-axle heavy", "🚌", 445),
        ("axle3", "3-Axle", "3-axle", "🚛", 685),
        ("axle46", "4-6 Axle", "4-6 axle", "🚚", 985),
        ("oversize", "Oversized (7+)", "7+ axle", "🚜", 1485),
    ]
    for i, (key, label, sub, icon, amount) in enumerate(rows, 1):
        db.add(models.TollRate(id=i, key=key, label=label, sub=sub, icon=icon, amount=amount))


def _seed_lanes(db: Session):
    if db.scalar(select(func.count(models.Lane.id))):
        return
    for i, (direction, active) in enumerate(
        [("Entry", True), ("Entry", True), ("Exit", True), ("Exit", False)], 1
    ):
        db.add(models.Lane(id=i, name=f"Lane {i}", direction=direction,
                           speed=60, headway=10, toll=185, active=active))


def _seed_fastag(db: Session):
    if db.scalar(select(func.count(models.FastagAccount.id))):
        return
    rows = [
        ("TAG400000000", "HR26 AA 1000", "HDFC", 1500, "Active"),
        ("TAG400000017", "DL01 DH 1131", "SBI", 2300, "Active"),
        ("TAG400000034", "MH04 GO 1262", "ICICI", 800, "LowBalance"),
        ("TAG400000051", "UP32 JV 1393", "AXIS", 50, "LowBalance"),
        ("TAG400000068", "PB10 MC 1524", "PNB", 3200, "Active"),
    ]
    for tag, plate, bank, bal, status in rows:
        db.add(models.FastagAccount(tag_id=tag, plate=plate, bank=bank,
                                    balance=bal, status=status))


def _seed_users(db: Session):
    if db.scalar(select(func.count(models.TollUser.id))):
        return
    # Primary admin — this is what the frontend Login uses (admin / 12345678).
    db.add(models.TollUser(
        id=str(uuid.uuid4()), name="Flow Admin", username="admin",
        email="admin@mlff.gov.in", role="Super Admin", plaza="NH-48 Gurugram",
        hashed_password=hash_password("12345678"), last="—", status="Active",
        color="#2a4cdb",
    ))
    seed = [
        ("Rakesh Kumar", "rakesh.kumar", "rakesh.k@nhai.gov.in", "Operator", "Active"),
        ("Priya Sharma", "priya.sharma", "priya.s@nhai.gov.in", "Supervisor", "Active"),
        ("Amit Verma", "amit.verma", "amit.v@nhai.gov.in", "Operator", "Inactive"),
        ("Neha Singh", "neha.singh", "neha.s@nhai.gov.in", "Report Manager", "Active"),
    ]
    for name, uname, email, role, status in seed:
        db.add(models.TollUser(
            id=str(uuid.uuid4()), name=name, username=uname, email=email,
            role=role, plaza="NH-48 Gurugram", hashed_password="", last="—",
            status=status, color="#2563eb",
        ))


def _seed_settings(db: Session):
    defaults = {
        "system_settings": {
            "general": {
                "plazaName": "NH-48 Gurugram Toll Plaza",
                "plazaCode": "NHAI-NH48-GGN-01",
                "timeZone": "Asia/Kolkata (IST +05:30)",
                "retentionDays": 365,
                "reportEmail": "toll.nhai.nh48@gov.in",
            },
            "features": {
                "autoViolation": True, "bankSync": True, "cctvRecording": True,
                "nightMode": True, "smsAlerts": False, "maintenance": False,
                "debugLogging": False,
            },
        },
        "rfid_config": {
            "npciHost": "https://npci.org.in/fastag/api/v2", "timeoutMs": 3000,
            "readRatePct": 95, "retryAttempts": 3, "autoBlacklist": True,
            "dedupFilter": True,
        },
        "thresholds": {
            "speedKmh": 60, "violationPct": 5, "failedTxn": 10,
            "cameraDowntimeMin": 5, "rfidReadRatePct": 95, "pingTimeoutMs": 100,
        },
        "comm": {
            "alertEmails": "toll.ops@nhai.gov.in", "smsNumbers": "+91-98765XXXXX",
            "webhookUrl": "https://hooks.nhai.gov.in/mlff/alerts",
            "emailAlertsEnabled": True,
        },
    }
    for key, value in defaults.items():
        if db.get(models.TollSetting, key) is None:
            db.add(models.TollSetting(key=key, value=value))


def _seed_anpr_cameras(db: Session):
    if db.scalar(select(func.count(models.AnprCameraCfg.id))):
        return
    nid = 1
    for lane in range(1, 5):
        hi = lane <= 2
        for role in ("Front", "Rear"):
            db.add(models.AnprCameraCfg(
                id=nid, kind="ANPR", lane=f"Lane {lane}", role=role,
                ip=f"192.168.{lane}.{11 if role=='Front' else 12}",
                resolution="4K UHD" if hi else "1080P",
                framerate=30 if hi else 25, active=lane != 4,
            ))
            nid += 1
    for label, zone, ip, resn, fr in [
        ("Surveillance 1", "Plaza Overview", "192.168.10.1", "4K UHD", 25),
        ("Surveillance 2", "Entry Zone", "192.168.10.2", "1080P", 25),
    ]:
        db.add(models.AnprCameraCfg(id=nid, kind="Surveillance", label=label,
                                    zone=zone, ip=ip, resolution=resn,
                                    framerate=fr, active=True))
        nid += 1


def _seed_txns(db: Session):
    if db.scalar(select(func.count(models.TollTransaction.id))):
        return
    CLASSES = [("Car / Jeep", 185), ("LCV", 285), ("Bus", 445),
               ("3-Axle", 685), ("Oversized", 985), ("Car / Jeep", 255)]
    STATES = ["Paid", "Paid", "Paid", "Paid", "Paid", "Paid", "Failed", "Pending", "Exempted"]
    LANES = ["Lane 1", "Lane 2", "Lane 3", "Lane 4", "Lane 5"]
    for i in range(120):
        cls, amt = CLASSES[i % len(CLASSES)]
        state = STATES[i % len(STATES)]
        db.add(models.TollTransaction(
            id="TXN" + _pad(100000 + i, 8),
            ts=datetime(2025, 3, 30, (i * 13) % 24, (i * 29) % 60, (i * 17) % 60, tzinfo=timezone.utc),
            date=_date_of(i),
            time=f"{_pad((i*13)%24)}:{_pad((i*29)%60)}:{_pad((i*17)%60)}",
            lane=LANES[i % len(LANES)], reg=_plate(i), cls=cls,
            tag="TAG" + _pad(400000000 + i * 17, 9), speed=45 + (i * 7) % 50,
            amount=0 if state == "Exempted" else amt,
            mode="Exempted" if state == "Exempted" else ("Cash" if i % 17 == 0 else "FASTag"),
            status=state,
        ))


def _seed_audit(db: Session):
    if db.scalar(select(func.count(models.ReconRow.aid))):
        return
    BANKS = ["NPCI/HDFC", "NPCI/SBI", "NPCI/ICICI", "NPCI/AXIS", "NPCI/PNB"]
    AMOUNTS = [185, 285, 445, 685, 985, 255]
    STATUSES = ["Success"] * 7 + ["Pending", "Failed", "Success"]

    def ts(base, off):
        h = (6 + (base + off) // 12) % 24
        m = (base * 3 + off * 2) % 60
        return f"2025-03-30  {_pad(h)}:{_pad(m)}"

    for i in range(120):
        st = STATUSES[i % len(STATUSES)]
        db.add(models.ReconRow(
            aid="AUD" + _pad(200000 + i, 6), txn="TXN" + _pad(100000 + i, 8),
            vrn=_plate(i), amount=AMOUNTS[i % len(AMOUNTS)], bank=BANKS[i % len(BANKS)],
            ref="—" if st == "Failed" else "NPCI" + _pad(8000000000 + i * 7, 10),
            sent=ts(6, i), settled=ts(7, i + 2) if st == "Success" else "—",
            tag_bal="—" if st == "Failed" else f"₹{1000 + i*23}", status=st,
        ))


def _seed_violations(db: Session):
    if db.scalar(select(func.count(models.Violation.id))):
        return
    TYPES = [("No FASTag", 500), ("Speeding", 1000), ("No FASTag", 500),
             ("Wrong Lane", 250), ("Axle Violation", 2000), ("Speeding", 1500),
             ("No FASTag", 500), ("Wrong Lane", 250), ("Axle Violation", 2000),
             ("Speeding", 1200), ("No FASTag", 500), ("Wrong Lane", 250),
             ("Axle Violation", 2000), ("Speeding", 1100)]
    STATES = ["Pending", "Pending", "Accepted", "Rejected", "Pending", "Accepted",
              "Pending", "Exempted", "Pending", "Accepted", "Pending", "Rejected",
              "Exempted", "Pending"]
    LANES = ["Lane 1", "Lane 2", "Lane 3", "Lane 4", "Lane 5"]
    for i, (k, fine) in enumerate(TYPES):
        db.add(models.Violation(
            id="VIO-" + _pad(i + 1, 3), vrn=_plate(i), date="2025-03-30",
            time=f"{_pad(20 - i//3)}:{_pad((45 - i*3 + 60) % 60)}:{_pad((12 + i*7) % 60)}",
            lane=LANES[i % len(LANES)], type=k,
            speed=90 + (i * 3) % 30 if k == "Speeding" else None,
            fine=fine, status=STATES[i % len(STATES)],
        ))


def _seed_demo_camera(db: Session):
    """Register a Camera the pipeline reads from the bundled demo video.

    rtsp_url is the ABSOLUTE mp4 path (VideoSource supports file sources) so
    the pipeline can open it from its own cwd; the browser plays the same file
    via /videos/<name> (config.browser_url).
    """
    video_path = demo_video_path()
    # process_fps caps how many frames/sec are detected on. The live view only
    # shows frames the pipeline processed, so a low cap makes the feed choppy;
    # keep it at the footage's frame rate and let the pipeline drop frames if
    # the GPU can't keep up (playback stays real-time either way).
    config = {"browser_url": f"/videos/{DEMO_VIDEO}", "res": "1080P",
              "fps": 25, "type": "ANPR", "process_fps": 25}
    existing = db.scalar(
        select(core_models.Camera).where(core_models.Camera.name == "ANPR Demo Feed")
    )
    if existing is not None:
        # Repair stale values from an earlier seed (relative path, low fps cap).
        if existing.rtsp_url != video_path:
            existing.rtsp_url = video_path
        if (existing.config or {}).get("process_fps") != config["process_fps"]:
            existing.config = {**(existing.config or {}), **config}
        return
    db.add(core_models.Camera(
        name="ANPR Demo Feed", location="Plaza Overview", rtsp_url=video_path,
        direction="Entry", lane="Lane 1", config=config, is_active=True,
    ))


def seed_toll(db: Session) -> None:
    _seed_rates(db)
    _seed_lanes(db)
    _seed_fastag(db)
    _seed_users(db)
    _seed_settings(db)
    _seed_anpr_cameras(db)
    _seed_txns(db)
    _seed_audit(db)
    _seed_violations(db)
    _seed_demo_camera(db)
    db.commit()
    logger.info("toll seed complete")
