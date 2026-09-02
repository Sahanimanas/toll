"""Network-management (NMS) + equipment-history synthesizers for
GET /api/nms and GET /api/equipment-history — ported from the Node backend."""

import random
from datetime import datetime

DEVS = ["ANPR Camera Front", "ANPR Camera Rear", "RFID Reader", "Lidar Sensor",
        "Radar Sensor", "LPC Camera", "Solar Controller", "LPU Controller"]

LANES = [
    {"id": "LN-001", "name": "Lane 1", "dir": "Entry (Gurugram → Delhi)", "offline": [], "degraded": []},
    {"id": "LN-002", "name": "Lane 2", "dir": "Entry (Gurugram → Delhi)", "offline": [], "degraded": [2]},
    {"id": "LN-003", "name": "Lane 3", "dir": "Exit (Delhi → Gurugram)", "offline": [], "degraded": [1]},
    {"id": "LN-004", "name": "Lane 4", "dir": "Exit (Delhi → Gurugram)", "offline": [0, 1, 2, 5, 7], "degraded": []},
]


def _pad(n, w=2):
    return str(n).zfill(w)


def build_nms() -> dict:
    d = datetime.now()
    ok_ts = f"{_pad(d.hour)}:{_pad(d.minute)}:{_pad(d.second)}"
    warn_ts = f"{_pad(d.hour)}:{_pad((d.minute+58)%60)}:{_pad((d.second+30)%60)}"
    err_ts = f"{_pad(d.hour-1 if d.hour>0 else 23)}:{_pad((d.minute+38)%60)}:14"

    lanes = []
    for lidx, L in enumerate(LANES):
        devices = []
        for idx, name in enumerate(DEVS):
            ip = f"192.168.{lidx+1}.{11+idx}"
            status, latency, ts = "ok", 3 + random.randint(0, 19), ok_ts
            if idx in L["offline"]:
                status, latency, ts = "err", None, err_ts
            elif idx in L["degraded"]:
                status, latency, ts = "warn", 4 + random.randint(0, 14), warn_ts
            devices.append({"name": name, "ip": ip, "latency": latency, "ts": ts, "status": status})
        online = sum(1 for x in devices if x["status"] == "ok")
        errs = sum(1 for x in devices if x["status"] == "err")
        if errs:
            state = "err" if errs >= 3 else "warn"
        elif any(x["status"] == "warn" for x in devices):
            state = "warn"
        else:
            state = "ok"
        lanes.append({**L, "devices": devices, "online": online, "total": len(devices), "state": state})

    all_devs = [x for L in lanes for x in L["devices"]]
    totals = {
        "online": sum(1 for x in all_devs if x["status"] == "ok"),
        "degraded": sum(1 for x in all_devs if x["status"] == "warn"),
        "offline": sum(1 for x in all_devs if x["status"] == "err"),
        "total": len(all_devs),
    }
    health = round((totals["online"] / totals["total"]) * 100)
    return {"lanes": lanes, "totals": totals, "health": health, "lastScan": ok_ts}


PREFIX = ["HR26", "DL01", "MH04", "UP32", "PB10", "GJ01", "RJ14", "KA09"]
CLASSES = ["Car / Jeep", "LCV", "Bus", "3-Axle", "Oversized"]
EH_LANES = ["Lane 1", "Lane 2", "Lane 3", "Lane 4", "Lane 5"]
STATES = ["OK", "OK", "OK", "OK", "OK", "Low Conf", "OK", "OK", "Error", "OK"]


def _plate(seed: int) -> str:
    p = PREFIX[seed % len(PREFIX)]
    ll = chr(65 + (seed * 3) % 26) + chr(65 + (seed * 7) % 26)
    return f"{p} {ll} {1000 + (seed * 131) % 9000}"


def build_equipment_history(frm: str, to: str, equipment: str,
                            lane: str = "", cls: str = "", reg: str = "") -> list[dict]:
    items = []
    for i in range(50):
        date = frm if i % 2 == 0 else to
        h, m, s = _pad((i * 3) % 24), _pad((i * 7) % 60), _pad((i * 11) % 60)
        conf = 70 + (i * 17) % 30
        if equipment == "ANPR":
            value = _plate(i)
        elif equipment == "RFID":
            value = "TAG" + _pad(400000000 + i * 17, 9)
        elif equipment == "Lidar":
            value = f"{4.5 + (i % 30)/10} m"
        elif equipment == "4D Radar":
            value = f"{45 + (i*3) % 50} km/h"
        else:
            value = "—"
        items.append({
            "id": "EQR" + _pad(900000 + i, 7),
            "timestamp": f"{date} {h}:{m}:{s}",
            "equipment": equipment,
            "lane": EH_LANES[i % len(EH_LANES)],
            "reg": _plate(i),
            "cls": CLASSES[i % len(CLASSES)],
            "value": value, "conf": conf,
            "status": STATES[i % len(STATES)],
        })
    if lane and lane != "All Lanes":
        items = [r for r in items if r["lane"] == lane]
    if cls and cls != "All Classes":
        items = [r for r in items if r["cls"] == cls]
    if reg:
        items = [r for r in items if reg.upper() in r["reg"].upper()]
    return items
