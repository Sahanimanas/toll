import io
import json
from datetime import datetime, timezone

from tests.conftest import INGEST_KEY


def _make_camera(client, admin_headers, name="Gate-1", config=None):
    response = client.post(
        "/api/v1/cameras",
        json={
            "name": name,
            "location": "North gate",
            "rtsp_url": "rtsp://cam.example/stream",
            "config": config or {},
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _payload(camera_id, plate="MH12AB1234", speed=None):
    return {
        "camera_id": camera_id,
        "plate_text": plate,
        "plate_confidence": 0.91,
        "vehicle_type": "car",
        "vehicle_confidence": 0.88,
        "speed_kmh": speed,
        "track_id": "trk001",
        "bbox": {"x1": 10, "y1": 20, "x2": 200, "y2": 180},
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def test_ingest_requires_api_key(client, admin_headers):
    camera_id = _make_camera(client, admin_headers, name="KeyTest")
    response = client.post(
        "/api/v1/ingest/recognitions",
        data={"payload": json.dumps(_payload(camera_id))},
    )
    assert response.status_code == 401


def test_ingest_and_search(client, admin_headers):
    camera_id = _make_camera(client, admin_headers, name="Search-Cam")
    response = client.post(
        "/api/v1/ingest/recognitions",
        data={"payload": json.dumps(_payload(camera_id, plate="mh12ab1234"))},
        files={"frame": ("frame.jpg", io.BytesIO(b"\xff\xd8fakejpeg"), "image/jpeg")},
        headers={"X-API-Key": INGEST_KEY},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["plate_text"] == "MH12AB1234"  # normalized to uppercase
    assert body["has_evidence"] is True

    search = client.get(
        "/api/v1/recognitions",
        params={"plate": "MH12", "camera_id": camera_id},
        headers=admin_headers,
    )
    assert search.status_code == 200
    result = search.json()
    assert result["total"] >= 1
    assert any(item["plate_text"] == "MH12AB1234" for item in result["items"])

    evidence = client.get(
        f"/api/v1/recognitions/{body['id']}/evidence", headers=admin_headers
    )
    assert evidence.status_code == 200
    assert evidence.content.startswith(b"\xff\xd8")


def test_ingest_unknown_camera(client):
    response = client.post(
        "/api/v1/ingest/recognitions",
        data={"payload": json.dumps(_payload(999999))},
        headers={"X-API-Key": INGEST_KEY},
    )
    assert response.status_code == 404


def test_watchlist_alert(client, admin_headers):
    camera_id = _make_camera(client, admin_headers, name="Watch-Cam")
    client.post(
        "/api/v1/watchlist",
        json={"plate_text": "ka05mn7788", "reason": "stolen", "severity": "critical"},
        headers=admin_headers,
    )
    response = client.post(
        "/api/v1/ingest/recognitions",
        data={"payload": json.dumps(_payload(camera_id, plate="KA05MN7788"))},
        headers={"X-API-Key": INGEST_KEY},
    )
    assert response.status_code == 201

    alerts = client.get(
        "/api/v1/alerts", params={"acknowledged": False}, headers=admin_headers
    ).json()
    watchlist_alerts = [a for a in alerts["items"] if a["type"] == "watchlist"]
    assert watchlist_alerts, "expected a watchlist alert"
    assert "KA05MN7788" in watchlist_alerts[0]["message"]

    ack = client.post(
        f"/api/v1/alerts/{watchlist_alerts[0]['id']}/ack", headers=admin_headers
    )
    assert ack.status_code == 200
    assert ack.json()["acknowledged"] is True


def test_speed_alert(client, admin_headers):
    camera_id = _make_camera(
        client, admin_headers, name="Speed-Cam", config={"speed_limit_kmh": 80}
    )
    response = client.post(
        "/api/v1/ingest/recognitions",
        data={"payload": json.dumps(_payload(camera_id, plate="DL8CAF5031", speed=132.0))},
        headers={"X-API-Key": INGEST_KEY},
    )
    assert response.status_code == 201

    alerts = client.get("/api/v1/alerts", headers=admin_headers).json()
    speed_alerts = [
        a for a in alerts["items"] if a["type"] == "speed" and "DL8CAF5031" in a["message"]
    ]
    assert speed_alerts, "expected a speed alert"
    assert speed_alerts[0]["severity"] == "critical"  # 132 > 80 * 1.5


def test_stats_summary(client, admin_headers):
    response = client.get("/api/v1/stats/summary", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["recognitions_total"] >= 1
    assert body["active_cameras"] >= 1
