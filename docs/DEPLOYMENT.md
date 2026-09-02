# Deployment

## Docker Compose (single host / edge box)

```bash
cp .env.example .env
# Edit .env: set ANPR_SECRET_KEY, ANPR_INGEST_API_KEY, POSTGRES_PASSWORD,
# ANPR_FIRST_ADMIN_PASSWORD to strong unique values.
docker compose up --build -d
```

Services: `postgres` (data volume `pgdata`), `redis`, `backend` (:8000),
`pipeline`, `dashboard` (nginx, :8080, proxies `/api` to backend).

The backend creates tables and the bootstrap admin automatically on first
start (`ANPR_AUTO_CREATE_TABLES=true`). For managed environments, prefer
migrations:

```bash
docker compose exec backend alembic upgrade head
```

and set `ANPR_AUTO_CREATE_TABLES=false`.

## Production AI models

The default image runs the classical-CV fallbacks. For production accuracy,
extend `pipeline/Dockerfile`:

```dockerfile
RUN pip install --no-cache-dir ultralytics easyocr
```

and mount/copy model weights:

- `ANPR_PIPELINE_VEHICLE_MODEL` — COCO-pretrained YOLO (e.g. `yolov8n.pt`,
  auto-downloaded) or a fine-tuned model.
- `ANPR_PIPELINE_PLATE_MODEL` — a licence-plate detection model
  (`models/plate.pt`); train on regional plate data.

## GPU inference (real-time / high-speed traffic)

Required for real-time recognition at highway speeds — the classical-CV
fallbacks cannot keep up with 120 km/h traffic. Prerequisite: NVIDIA driver +
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
on the host (`nvidia-smi` must work).

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
```

The overlay builds `pipeline/Dockerfile.gpu` (CUDA torch base + YOLO +
EasyOCR), reserves one GPU, sets `ANPR_PIPELINE_DEVICE=cuda:0`, and drops
`ANPR_PIPELINE_FRAME_STRIDE` to 1 (process every frame). YOLO runs FP16 on
CUDA automatically.

Verify on startup: the pipeline logs
`device: cuda:0 (<GPU name>)`, `vehicle detector: YOLO (...) on cuda:0` and
`OCR engine: EasyOCR on cuda:0`. If it logs `using cpu`, the container isn't
seeing the GPU.

Bare-metal (no Docker):

```bash
cd pipeline
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt -r requirements-gpu.txt
ANPR_PIPELINE_DEVICE=cuda:0 ANPR_PIPELINE_FRAME_STRIDE=1 python -m anpr_pipeline.main
```

Device selection (`ANPR_PIPELINE_DEVICE`): `auto` (default) uses CUDA when
available and silently falls back to CPU; an explicit `cuda`/`cuda:N` fails
fast at startup instead of silently running slow — use it in production so a
broken driver is caught immediately. Multi-GPU hosts can pin pipeline
replicas to different GPUs via `cuda:0`, `cuda:1`, …

## Scaling out

- **More cameras:** run additional `pipeline` replicas, each pointed at a
  subset of cameras (assignment strategy is the next planned feature) — dedup
  is Redis-backed so replicas coordinate correctly.
- **Backend:** stateless; scale `--workers` or replicas behind the nginx
  proxy. Evidence needs shared storage (NFS/S3-compatible mount) when the
  backend scales beyond one node.
- **Database:** enable monthly partitioning of `recognitions` when row counts
  reach the hundreds of millions (see ARCHITECTURE.md).

## Operations

- Health probe: `GET /api/v1/health`.
- Logs: all services log structured lines to stdout (`docker compose logs -f`).
- Backups: `pgdata` volume + the `evidence` volume are the state; snapshot both.
- Recognition spool: pipeline stores undeliverable events in the `spool`
  volume and replays automatically when the backend returns.
