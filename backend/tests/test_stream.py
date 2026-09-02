"""Live-stream endpoint tests. The MJPEG source is mocked so tests run
without OpenCV or a reachable camera (repo rule: no infra in tests)."""

import pytest

from app.api.v1 import cameras as cameras_module
from app.services.stream import StreamLimitExceeded, StreamUnavailable

FRAME = b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: 4\r\n\r\nJPEG\r\n"


class FakeStream:
    instances: list["FakeStream"] = []

    def __init__(self, source_url: str, overlay_provider=None, fps=None):
        self.source_url = source_url
        self.overlay_provider = overlay_provider
        self.fps = fps
        self.closed = False
        FakeStream.instances.append(self)

    def __iter__(self):
        return iter([FRAME, FRAME])

    def close(self):
        self.closed = True


@pytest.fixture()
def stream_camera_id(client, admin_headers):
    response = client.post(
        "/api/v1/cameras",
        json={"name": "stream-cam", "rtsp_url": "rtsp://example/stream"},
        headers=admin_headers,
    )
    if response.status_code == 409:  # already created by an earlier test in the session
        cams = client.get("/api/v1/cameras?page_size=500", headers=admin_headers).json()
        return next(c["id"] for c in cams["items"] if c["name"] == "stream-cam")
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_stream_requires_auth(client, stream_camera_id):
    assert client.get(f"/api/v1/cameras/{stream_camera_id}/stream").status_code == 401


def test_stream_rejects_garbage_query_token(client, stream_camera_id):
    response = client.get(f"/api/v1/cameras/{stream_camera_id}/stream?token=not-a-jwt")
    assert response.status_code == 401


def test_stream_unknown_camera_404(client, admin_headers):
    assert client.get("/api/v1/cameras/999999/stream", headers=admin_headers).status_code == 404


def test_stream_with_query_token(client, admin_token, stream_camera_id, monkeypatch):
    monkeypatch.setattr(cameras_module, "MjpegStream", FakeStream)
    response = client.get(f"/api/v1/cameras/{stream_camera_id}/stream?token={admin_token}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert response.content == FRAME + FRAME
    assert FakeStream.instances[-1].closed  # background task released the source


def test_stream_with_bearer_header_and_viewer_role(
    client, viewer_headers, stream_camera_id, monkeypatch
):
    monkeypatch.setattr(cameras_module, "MjpegStream", FakeStream)
    response = client.get(
        f"/api/v1/cameras/{stream_camera_id}/stream", headers=viewer_headers
    )
    assert response.status_code == 200


def test_stream_uses_per_camera_live_fps(client, admin_headers, admin_token, monkeypatch):
    monkeypatch.setattr(cameras_module, "MjpegStream", FakeStream)
    response = client.post(
        "/api/v1/cameras",
        json={"name": "fps-cam", "rtsp_url": "rtsp://example/fps", "config": {"live_fps": 15}},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    camera_id = response.json()["id"]
    response = client.get(f"/api/v1/cameras/{camera_id}/stream?token={admin_token}")
    assert response.status_code == 200
    assert FakeStream.instances[-1].fps == 15


def test_stream_unreachable_camera_502(client, admin_headers, stream_camera_id, monkeypatch):
    def boom(source_url, overlay_provider=None, fps=None):
        raise StreamUnavailable(source_url)

    monkeypatch.setattr(cameras_module, "MjpegStream", boom)
    response = client.get(
        f"/api/v1/cameras/{stream_camera_id}/stream", headers=admin_headers
    )
    assert response.status_code == 502


def test_stream_viewer_limit_503(client, admin_headers, stream_camera_id, monkeypatch):
    def full(source_url, overlay_provider=None, fps=None):
        raise StreamLimitExceeded("full")

    monkeypatch.setattr(cameras_module, "MjpegStream", full)
    response = client.get(
        f"/api/v1/cameras/{stream_camera_id}/stream", headers=admin_headers
    )
    assert response.status_code == 503


# --- live-view overlays ---


def test_overlay_provider_returns_recent_boxes(client, admin_headers, stream_camera_id):
    import json
    from datetime import datetime, timezone

    payload = {
        "camera_id": stream_camera_id,
        "plate_text": "MH12AB1234",
        "plate_confidence": 0.9,
        "bbox": {"x1": 10, "y1": 20, "x2": 200, "y2": 220,
                 "plate": {"x1": 60, "y1": 150, "x2": 160, "y2": 190}},
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    response = client.post(
        "/api/v1/ingest/recognitions",
        data={"payload": json.dumps(payload)},
        headers={"X-API-Key": "test-ingest-key"},
    )
    assert response.status_code == 201, response.text

    provider = cameras_module.recent_recognition_overlays(stream_camera_id)
    overlays = provider()
    assert any(
        o["label"] == "MH12AB1234"
        and o["vehicle"] == (10, 20, 200, 220)
        and o["plate"] == (60, 150, 160, 190)
        for o in overlays
    ), overlays


def test_overlay_provider_ignores_other_cameras(client, admin_headers):
    provider = cameras_module.recent_recognition_overlays(999999)
    assert provider() == []


def test_live_detection_boxes_flow_to_overlay(client, stream_camera_id):
    response = client.post(
        "/api/v1/ingest/detections",
        json={
            "camera_id": stream_camera_id,
            "boxes": [
                {"x1": 5, "y1": 6, "x2": 100, "y2": 60, "kind": "vehicle", "label": "car"},
                {"x1": 30, "y1": 40, "x2": 90, "y2": 55, "kind": "plate"},
            ],
        },
        headers={"X-API-Key": "test-ingest-key"},
    )
    assert response.status_code == 204, response.text

    provider = cameras_module.recent_recognition_overlays(stream_camera_id)
    overlays = provider()
    assert {"vehicle": (5, 6, 100, 60), "label": "car"} in overlays
    assert {"plate": (30, 40, 90, 55), "label": ""} in overlays


def test_live_detections_require_ingest_key(client):
    response = client.post(
        "/api/v1/ingest/detections", json={"camera_id": 1, "boxes": []}
    )
    assert response.status_code == 401


def test_live_boxes_expire():
    from app.services import live_boxes

    live_boxes.set_boxes(424242, [{"x1": 1, "y1": 1, "x2": 2, "y2": 2, "kind": "vehicle"}])
    assert live_boxes.get_boxes(424242)
    key = 424242
    at, boxes = live_boxes._boxes[key]
    live_boxes._boxes[key] = (at - live_boxes.LIVE_BOX_TTL_SECONDS - 1, boxes)
    assert live_boxes.get_boxes(key) == []


# --- POST /cameras/test (stream connectivity probe) ---


def test_stream_test_requires_auth(client):
    response = client.post("/api/v1/cameras/test", json={"stream_url": "rtsp://example/"})
    assert response.status_code == 401


def test_stream_test_forbidden_for_viewer(client, viewer_headers):
    response = client.post(
        "/api/v1/cameras/test",
        json={"stream_url": "rtsp://example/"},
        headers=viewer_headers,
    )
    assert response.status_code == 403


def test_stream_test_success(client, admin_headers, monkeypatch):
    seen = {}

    def fake_probe(url):
        seen["url"] = url
        return {"ok": True, "detail": "Stream opened, first frame decoded",
                "width": 1920, "height": 1080, "latency_ms": 120}

    monkeypatch.setattr(cameras_module, "probe_stream", fake_probe)
    response = client.post(
        "/api/v1/cameras/test",
        json={"stream_url": "https://example.com/cam.mjpg"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["width"] == 1920
    assert seen["url"] == "https://example.com/cam.mjpg"


def test_stream_test_unreachable_reports_ok_false(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        cameras_module,
        "probe_stream",
        lambda url: {"ok": False, "detail": f"could not open stream {url!r}"},
    )
    response = client.post(
        "/api/v1/cameras/test",
        json={"stream_url": "rtsp://10.0.0.99/"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "could not open" in body["detail"]


def test_stream_test_without_opencv_501(client, admin_headers, monkeypatch):
    def no_cv2(url):
        raise ImportError("No module named 'cv2'")

    monkeypatch.setattr(cameras_module, "probe_stream", no_cv2)
    response = client.post(
        "/api/v1/cameras/test",
        json={"stream_url": "rtsp://example/"},
        headers=admin_headers,
    )
    assert response.status_code == 501


def test_stream_test_rejects_empty_url(client, admin_headers):
    response = client.post(
        "/api/v1/cameras/test", json={"stream_url": ""}, headers=admin_headers
    )
    assert response.status_code == 422
