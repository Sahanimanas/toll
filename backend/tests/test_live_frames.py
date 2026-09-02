"""Live-frame ingest + snapshot serving. The pipeline pushes annotated JPEG
frames and the dashboard reads the newest one; nothing here needs OpenCV or a
camera (repo rule: no infra in tests)."""

import pytest

INGEST_KEY = "test-ingest-key"
# A tiny but valid-enough JPEG payload; the backend stores bytes verbatim and
# never decodes them, so any non-empty blob exercises the path.
FRAME_BYTES = b"\xff\xd8\xff\xe0JFIF-fake-jpeg\xff\xd9"


@pytest.fixture()
def frame_camera_id(client, admin_headers):
    response = client.post(
        "/api/v1/cameras",
        json={"name": "frame-cam", "rtsp_url": "rtsp://example/frame"},
        headers=admin_headers,
    )
    if response.status_code == 409:
        cams = client.get("/api/v1/cameras?page_size=500", headers=admin_headers).json()
        return next(c["id"] for c in cams["items"] if c["name"] == "frame-cam")
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _post_frame(client, camera_id, data=FRAME_BYTES, key=INGEST_KEY):
    headers = {"X-API-Key": key} if key else {}
    return client.post(
        "/api/v1/ingest/frame",
        data={"camera_id": str(camera_id)},
        files={"frame": ("frame.jpg", data, "image/jpeg")},
        headers=headers,
    )


def test_ingest_frame_requires_ingest_key(client, frame_camera_id):
    assert _post_frame(client, frame_camera_id, key=None).status_code == 401


def test_ingest_frame_rejects_empty(client, frame_camera_id):
    assert _post_frame(client, frame_camera_id, data=b"").status_code == 422


def test_snapshot_returns_latest_pushed_frame(client, admin_headers, frame_camera_id):
    assert _post_frame(client, frame_camera_id).status_code == 204
    response = client.get(
        f"/api/v1/cameras/{frame_camera_id}/snapshot", headers=admin_headers
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == FRAME_BYTES


def test_snapshot_requires_auth(client, frame_camera_id):
    assert client.get(f"/api/v1/cameras/{frame_camera_id}/snapshot").status_code == 401


def test_snapshot_unknown_camera_404(client, admin_headers):
    response = client.get("/api/v1/cameras/999999/snapshot", headers=admin_headers)
    assert response.status_code == 404


def test_snapshot_503_when_no_frame(client, admin_headers):
    response = client.post(
        "/api/v1/cameras",
        json={"name": "no-frame-cam", "rtsp_url": "rtsp://example/none"},
        headers=admin_headers,
    )
    camera_id = response.json()["id"] if response.status_code == 201 else next(
        c["id"]
        for c in client.get("/api/v1/cameras?page_size=500", headers=admin_headers)
        .json()["items"]
        if c["name"] == "no-frame-cam"
    )
    response = client.get(
        f"/api/v1/cameras/{camera_id}/snapshot", headers=admin_headers
    )
    assert response.status_code == 503


def test_fresh_frame_makes_stream_use_pipeline_source(
    client, admin_headers, admin_token, frame_camera_id, monkeypatch
):
    """When a fresh pipeline frame exists, /stream serves it without opening a
    camera connection (MjpegStream must not be constructed)."""
    from app.api.v1 import cameras as cameras_module

    def fail(*args, **kwargs):
        raise AssertionError("MjpegStream should not be used when a frame is fresh")

    monkeypatch.setattr(cameras_module, "MjpegStream", fail)
    assert _post_frame(client, frame_camera_id).status_code == 204
    # The pipeline stream is endless while frames are fresh, so read just the
    # first multipart part instead of buffering the whole (infinite) body.
    with client.stream(
        "GET", f"/api/v1/cameras/{frame_camera_id}/stream?token={admin_token}"
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
        first = next(response.iter_bytes())
        assert FRAME_BYTES in first


def test_live_frames_expire():
    from app.services import live_frames

    live_frames.set_frame(515151, FRAME_BYTES)
    assert live_frames.get_frame(515151) == FRAME_BYTES
    at, data = live_frames._frames[515151]
    live_frames._frames[515151] = (at - live_frames.LIVE_FRAME_TTL_SECONDS - 1, data)
    assert live_frames.get_frame(515151) is None
    assert live_frames.has_fresh_frame(515151) is False
