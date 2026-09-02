# Tech Stack

Everything the ANPR platform is built with, layer by layer. Versions marked
"pinned" come from requirements/package files; others are what the current
dev environment runs.

## AI / Recognition pipeline (`pipeline/`)

| Technology | Version | Role |
| --- | --- | --- |
| Python | 3.11 | Pipeline runtime |
| Ultralytics YOLOv8 | 8.4 | Vehicle detection (`yolov8n.pt`, COCO classes) and plate detection (`models/plate.pt`, [Koushim/yolov8-license-plate-detection](https://huggingface.co/Koushim/yolov8-license-plate-detection), MIT) |
| PyTorch | 2.12 (+cu126) | Inference backend for YOLO and EasyOCR; CUDA on NVIDIA GPUs, CPU fallback |
| EasyOCR | 1.7 | Plate character recognition (Tesseract as fallback engine) |
| OpenCV | ≥4.9 (headless) | RTSP/H.265 capture, classical-CV fallbacks (MOG2 motion detection, contour plate finder), image enhancement, perspective correction |
| NumPy | ≥1.26 | Array plumbing between stages |
| requests | ≥2.31 | Publishing recognitions to the backend (with disk spool for outages) |
| Redis client | ≥5.0 | Cross-worker plate dedup (in-memory fallback without Redis) |

Every AI stage is pluggable via `build_*` factories with `auto` mode:
YOLO → motion detection, plate YOLO → contour heuristic, EasyOCR →
Tesseract → disabled. The pipeline runs on any machine; accuracy scales
with what's installed.

## Backend API (`backend/`)

| Technology | Version | Role |
| --- | --- | --- |
| FastAPI | ≥0.115 | REST API (`/api/v1`), OpenAPI docs at `/docs` |
| Uvicorn | ≥0.30 | ASGI server |
| SQLAlchemy | 2.0 | ORM (typed `Mapped` models) |
| Alembic | ≥1.13 | Schema migrations (hand-written; auto-create is dev-only) |
| Pydantic | v2 | Request/response schemas, settings via pydantic-settings |
| PostgreSQL | 16 (Docker) / SQLite (dev & tests) | Primary datastore |
| PyJWT + passlib/bcrypt | ≥2.8 / ≥1.7 | JWT auth (access + refresh) and password hashing; role-based access control (admin/operator/viewer) |
| OpenCV (headless) | ≥4.9 | Live MJPEG restream of camera feeds with recognition-box overlays |
| Redis | 7 (optional) | Reserved for cross-instance state; backend runs without it |

## Dashboard (`dashboard/`)

| Technology | Version | Role |
| --- | --- | --- |
| React | 18.3 | UI (SPA) |
| TypeScript | 5.5 (strict) | Type safety |
| Vite | 5.4 | Dev server (proxies `/api` → backend :8000) and production build |
| React Router | 6.26 | Client-side routing |
| nginx | alpine (Docker) | Serves the built SPA and proxies the API in deployment |

No UI component library — hand-rolled CSS (`src/styles.css`), no websockets
(pages poll the REST API).

## Infrastructure & tooling

| Technology | Role |
| --- | --- |
| Docker Compose | Full-stack deployment: postgres, redis, backend, pipeline, dashboard (`docker-compose.yml`; `docker-compose.gpu.yml` adds a CUDA pipeline image) |
| NVIDIA CUDA | GPU inference (dev machine: GTX 1650 4 GB, driver 581.x, cu126 wheels) |
| pytest | Backend + pipeline test suites — SQLite/in-memory only, no infra needed |
| Git | Version control |
| Windows `.cmd` scripts | One-click local launch (`start-all.cmd`, `scripts/run-*.cmd`) |

## Protocols & camera integration

| Technology | Role |
| --- | --- |
| RTSP over TCP | Camera video ingest (H.264/H.265 via OpenCV/FFmpeg) |
| ONVIF (SOAP, WS-UsernameToken digest) | Stream URI discovery on IP cameras |
| MJPEG (`multipart/x-mixed-replace`) | Browser-compatible live restream in a plain `<img>` tag |
| HTTP digest auth | Camera web endpoints |

## Processing profile: how frames become recognitions

Per camera, one worker thread runs this loop:

1. **Capture at the live edge** — a grabber thread consumes the RTSP stream
   at camera rate (~25 fps) *without decoding*; the worker always decodes
   the newest frame, so processing lag can never accumulate.
2. **Pace to the fps cap** — recognition runs at **15 fps per camera** by
   default (`ANPR_PIPELINE_MAX_FPS`, per-camera override `process_fps` in
   the dashboard's camera modal, clamped 1–60). Frames above the cap are
   skipped, not queued.
3. **Detect** — vehicle YOLO at inference size **640** (cars are large
   targets); plate YOLO at **1280** (`ANPR_PIPELINE_PLATE_IMGSZ` — the
   range lever: at 640 a 4K frame shrinks 6× and plates beyond ~2–3 m fall
   under the ~40 px detection floor; 1280 roughly doubles usable range,
   1920 on GPU for maximum). If no vehicle is found, plate detection runs
   on the full frame (close-up/parked vehicles), ignoring the top 8 % strip
   where camera OSD text lives.
4. **Read & gate** — plate crop → perspective correction → enhancement →
   EasyOCR → region grammar normalization (IN state-code validation,
   confusion-pair coercion, embedded-plate extraction). Publishes on one
   read ≥ 0.60 confidence, or on **multi-frame consensus**: the same text
   read ≥ 2× within 10 s at ≥ 0.45.
5. **Publish** — once per vehicle pass (30 s dedup per plate+camera), with
   full-frame + plate-crop JPEG evidence; detection boxes are also pushed
   every processed frame for the live-view overlay (in-memory, 3 s TTL).

### Frame-rate summary

| Path | Rate | Knob |
| --- | --- | --- |
| Camera → grabber | camera native (~25 fps) | camera Streams settings |
| Recognition processing | 15 fps/camera default | `ANPR_PIPELINE_MAX_FPS` / per-camera `process_fps` |
| Live MJPEG restream | 30 fps cap = full camera rate | `ANPR_STREAM_FPS` / per-camera `live_fps` |
| Overlay box refresh | every processed frame (≤ 3 s TTL) | — |

### GPU configuration

- Device selection is `auto` (`ANPR_PIPELINE_DEVICE`): CUDA when available,
  CPU otherwise; explicit `cuda` fails fast if missing. FP16 is enabled
  automatically on CUDA.
- All three models (vehicle YOLO, plate YOLO, EasyOCR) share the GPU; the
  detectors are instantiated **per camera worker** (single instances are not
  thread-safe across camera threads).
- Reference dev machine: **NVIDIA GTX 1650 4 GB** (driver 581.x, PyTorch
  cu126 wheels): 4 cameras at the caps above ≈ 40–50 % GPU utilization,
  ~350 MB VRAM; plate-shown → recognition ≈ 1–2 s end-to-end.
- CPU-only fallback works unchanged at roughly 1–2 processed fps per camera
  (Docker CPU image), with classical-CV fallbacks if the AI extras aren't
  installed at all.

## Data flow in one line

RTSP camera → pipeline (capture → enhance → YOLO vehicle → track → YOLO
plate → OCR → validate/consensus → dedup) → FastAPI ingest (`X-API-Key`)
→ PostgreSQL/SQLite + evidence JPEGs → React dashboard (JWT) + live MJPEG
overlay.
