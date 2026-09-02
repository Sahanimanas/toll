# Architecture

## System overview

```
IP Cameras (RTSP/GigE)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│ pipeline/  (one CameraWorker thread per camera)      │
│                                                      │
│  capture → enhance → vehicle detect → track          │
│     → plate detect → perspective correction          │
│     → plate enhance → OCR → normalize/validate       │
│     → confidence gate → duplicate filter (Redis)     │
│     → speed estimate → publish (HTTP + disk spool)   │
└───────────────┬─────────────────────────────────────┘
                │ POST /api/v1/ingest/recognitions (X-API-Key)
                ▼
┌─────────────────────────────────────────────────────┐
│ backend/  (FastAPI)                                  │
│  ingest → evidence storage → alert engine            │
│  REST API: auth/users/cameras/recognitions/          │
│            watchlist/alerts/stats                    │
└───────┬───────────────────────┬─────────────────────┘
        │ PostgreSQL            │ evidence volume (JPEG)
        ▼                       ▼
┌──────────────┐        ┌──────────────┐
│ dashboard/   │◀──JWT──│  operators   │
└──────────────┘        └──────────────┘
```

Redis serves duplicate suppression for the pipeline (atomic `SET NX EX`) and
is available to the backend for future pub/sub (live alert push).

## Design decisions

**Pluggable AI backends.** Vehicle detection, plate detection, and OCR are
each behind a small interface with an `auto` builder: YOLO/EasyOCR when
installed (GPU-capable), classical CV fallbacks (MOG2 motion detection,
contour plate localization, Tesseract) otherwise. This lets the same codebase
run on a GPU edge box and a CPU-only dev laptop, and lets models be upgraded
via configuration only (`ANPR_PIPELINE_VEHICLE_DETECTOR`, `..._PLATE_DETECTOR`,
`..._OCR_ENGINE`).

**Push ingest with disk spool.** The pipeline pushes recognitions to the
backend over HTTP with the evidence JPEGs attached. If the backend is
unreachable, events are spooled to disk and replayed on the next successful
publish — a network outage never loses recognitions. 4xx responses are
treated as permanent failures and dropped (they would never succeed).

**Evidence storage.** JPEGs live on a filesystem volume under
`YYYY/MM/DD/<uuid>.jpg`; the database stores paths relative to the evidence
root, so storage can be moved/mounted elsewhere without data migration.
Retrieval goes through the API with path-traversal protection.

**Alert engine.** Runs inside the ingest transaction so a recognition and its
alerts commit atomically. Current rules: watchlist exact-match and per-camera
speed limit (`config.speed_limit_kmh`). New rule types plug into
`backend/app/services/alert_engine.py`.

**Tracking & dedup.** An IOU tracker maintains vehicle identity across frames
(one publish per vehicle pass), and Redis-based dedup suppresses the same
plate on the same camera within a TTL window — together these prevent the
classic ANPR flood of duplicate reads.

**Live view.** The pipeline is the single owner of the camera connection. It
draws detection boxes onto the *exact* frame it ran detection on, downscales
and JPEG-encodes it, and pushes that finished frame to the backend
(`POST /api/v1/ingest/frame`), which caches the newest frame per camera in
memory. The dashboard's canvas view polls `GET /cameras/{id}/snapshot` and
paints each frame as it arrives — because it fetches (not buffers) the newest
frame, it never shows a stale frame the way a plain MJPEG `<img>` can, and
because the box is baked into the frame it was detected on, the overlay is
never on the wrong frame. This replaced an earlier design where the backend
opened a *second* RTSP connection and redrew boxes on frames it decoded
itself: that doubled camera load, paid a full 4K decode per viewer, and let
boxes drift onto frames they were never computed for. The backend still
restreams RTSP directly (`GET /cameras/{id}/stream`) as a fallback when no
fresh pipeline frame exists (dev, or a camera the pipeline isn't covering).

**Speed estimation.** Planar approximation from track history using the
camera's calibrated `meters_per_pixel`. Adequate for alerting; certified
enforcement requires per-site homography, which slots into
`pipeline/anpr_pipeline/speed.py`.

## Database scale plan

The `recognitions` table is designed for hundreds of millions of rows:

- Indexes: `(plate_text)`, `(captured_at)`, `(camera_id, captured_at)` cover
  the dashboard's search patterns.
- Growth path: convert to PostgreSQL declarative partitioning by month on
  `captured_at` once volume warrants (the schema keeps `captured_at` in every
  hot query to enable partition pruning).
- Retention: evidence JPEGs dominate storage; prune with a scheduled job that
  deletes files older than the retention window and nulls the paths.

## Security model

- JWT access tokens (30 min) + refresh tokens (7 days); bcrypt password hashes.
- RBAC: `admin` (everything), `operator` (cameras, watchlist, ack alerts),
  `viewer` (read-only).
- Pipeline↔backend uses a separate static API key (`X-API-Key`) — machine
  identity is never a user account.
- Audit log records every mutating admin/operator action.
- Evidence endpoint validates paths against the evidence root (no traversal).
- Live-view stream endpoint accepts the access token via `?token=` (image
  tags cannot send headers); it is read-only, short-lived (30-min token), and
  the only endpoint that does. Camera RTSP credentials never reach the
  browser — the backend restreams as MJPEG.
- SQL injection prevented by SQLAlchemy bound parameters throughout; XSS by
  React's default escaping; CORS restricted to configured origins.
