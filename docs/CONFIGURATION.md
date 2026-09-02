# Configuration

All settings are environment variables. Backend variables use the `ANPR_`
prefix and can also come from a `.env` file.

## Backend

| Variable                          | Default                     | Purpose                                    |
| --------------------------------- | --------------------------- | ------------------------------------------ |
| `ANPR_SECRET_KEY`                 | dev value — **change**      | JWT signing key                            |
| `ANPR_INGEST_API_KEY`             | dev value — **change**      | Pipeline→backend auth                      |
| `ANPR_ACCESS_TOKEN_EXPIRE_MINUTES`| `30`                        | Access token lifetime                      |
| `ANPR_REFRESH_TOKEN_EXPIRE_MINUTES`| `10080`                    | Refresh token lifetime (7 days)            |
| `ANPR_DATABASE_URL`               | local Postgres              | SQLAlchemy URL (`postgresql+psycopg://…`)  |
| `ANPR_REDIS_URL`                  | `redis://localhost:6379/0`  | Redis                                      |
| `ANPR_EVIDENCE_DIR`               | `./data/evidence`           | Evidence JPEG root                         |
| `ANPR_AUTO_CREATE_TABLES`         | `true`                      | Dev convenience; use Alembic in production |
| `ANPR_FIRST_ADMIN_EMAIL/PASSWORD` | dev values — **change**     | Bootstrap admin (created if no users exist)|
| `ANPR_CORS_ORIGINS`               | localhost origins           | JSON list of allowed origins               |
| `ANPR_STREAM_FPS`                 | `30`                        | Live-view MJPEG frame rate cap (30 ≥ camera fps = unthrottled) |
| `ANPR_STREAM_MAX_WIDTH`           | `960`                       | Live-view frames downscaled to this width  |
| `ANPR_STREAM_MAX_VIEWERS`         | `4`                         | Concurrent live-view connections cap       |

## Pipeline

| Variable                            | Default                    | Purpose                                     |
| ----------------------------------- | -------------------------- | ------------------------------------------- |
| `ANPR_BACKEND_URL`                  | `http://localhost:8000`    | Backend base URL                            |
| `ANPR_INGEST_API_KEY`               | dev value — **change**     | Must match backend                          |
| `ANPR_REDIS_URL`                    | `redis://localhost:6379/0` | Dedup store (falls back to in-memory)       |
| `ANPR_PIPELINE_REGION`              | `IN`                       | Plate grammar: `IN`, `EU`, `GENERIC`        |
| `ANPR_PIPELINE_MIN_OCR_CONFIDENCE`  | `0.60`                     | Reject reads below this confidence          |
| `ANPR_PIPELINE_DEDUP_TTL_SECONDS`   | `30`                       | Same plate+camera suppression window        |
| `ANPR_PIPELINE_FRAME_STRIDE`        | `1`                        | Legacy: process every Nth read frame (fps cap supersedes it) |
| `ANPR_PIPELINE_DEVICE`              | `auto`                     | AI compute device: `auto` / `cpu` / `cuda` / `cuda:N`. `auto` falls back to CPU; explicit `cuda` fails fast if unavailable |
| `ANPR_PIPELINE_VEHICLE_DETECTOR`    | `auto`                     | `auto` / `yolo` / `motion`                  |
| `ANPR_PIPELINE_PLATE_DETECTOR`      | `auto`                     | `auto` / `yolo` / `contour`                 |
| `ANPR_PIPELINE_OCR_ENGINE`          | `auto`                     | `auto` / `easyocr` / `tesseract`            |
| `ANPR_PIPELINE_VEHICLE_MODEL`       | `yolov8n.pt`               | Vehicle YOLO weights                        |
| `ANPR_PIPELINE_PLATE_MODEL`         | `models/plate.pt`          | Plate YOLO weights                          |
| `ANPR_PIPELINE_VEHICLE_CONF`        | `0.30`                     | Vehicle YOLO confidence gate (low for moving/occluded vehicles; consensus filters false reads) |
| `ANPR_PIPELINE_PLATE_CONF`          | `0.25`                     | Plate YOLO confidence gate (kept low so blurry moving plates stay in play; raise for static/clean-plate sites) |
| `ANPR_PIPELINE_VEHICLE_IMGSZ`       | `640`                      | Vehicle YOLO inference size (longest side)  |
| `ANPR_PIPELINE_PLATE_IMGSZ`         | `1280`                     | Plate YOLO inference size — the range lever: frames are downscaled to this before detection, so small/distant plates vanish at 640 on a 4K stream; raise to 1920 on GPU for more range |
| `ANPR_PIPELINE_FULL_FRAME_PLATES`   | `1`                        | When no vehicle is detected, also run plate detection on the whole frame (close-up/cropped/parked vehicles); `0` disables |
| `ANPR_PIPELINE_MAX_FPS`             | `15`                       | Default per-camera recognition fps cap (see `process_fps`) |
| `ANPR_PIPELINE_STREAM_MAX_WIDTH`    | `960`                      | Width the pipeline downscales annotated live-view frames to before shipping them to the backend; `0` disables frame push (falls back to backend RTSP restream) |
| `ANPR_PIPELINE_STREAM_JPEG_QUALITY` | `75`                       | JPEG quality of annotated live-view frames  |
| `ANPR_PIPELINE_SPOOL_DIR`           | `./data/spool`             | Offline event spool                         |
| `ANPR_PIPELINE_CAMERA_REFRESH_SECONDS` | `60`                    | Camera list re-fetch interval               |

## Per-camera configuration (`cameras.config` JSON)

| Key               | Used by             | Purpose                                 |
| ----------------- | ------------------- | --------------------------------------- |
| `speed_limit_kmh` | backend alert engine| Speed violation alerts                  |
| `meters_per_pixel`| pipeline speed      | Speed estimation calibration            |
| `process_fps`     | pipeline worker     | Recognition frames/sec cap for this camera (default `ANPR_PIPELINE_MAX_FPS` = 15) |
| `live_fps`        | backend live stream | Live-view fps for this camera — caps both the pipeline-frame stream and the RTSP fallback (default `ANPR_STREAM_FPS` = 30 = full rate, clamped 1–30; note the pipeline-frame path is also bounded by `process_fps`) |

All per-camera keys are editable from the dashboard's camera Add/Edit modal.

## Camera field guidance (high-speed capture)

For reliable OCR at speed, configure the physical cameras with:

- Shutter ≤ 1/1000 s (1/2000 s for >120 km/h) to eliminate motion blur;
  compensate with gain/IR rather than slower shutter.
- Plate height ≥ 25–30 px in the image at the capture line; choose lens/ROI
  accordingly.
- H.264/H.265 at high bitrate or MJPEG on the capture stream; avoid
  aggressive compression on the ANPR stream (use a second stream for viewing).
- Mount 20–30° maximum vertical angle to the plate; the pipeline's perspective
  correction handles small skews only.
- IR illumination + day/night cut filter for 24/7 operation.
