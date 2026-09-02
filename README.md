# MLFF Tolling System

Multi-Lane Free Flow tolling for NH-48 Gurugram Plaza: live ANPR plate
recognition from camera/video feeds, automatic toll calculation with FASTag
deduction, violation/e-ticket handling, NPCI reconciliation, and an operator
console.

Self-contained — backend, AI pipeline and console all live here.

## Layout

| Directory   | What it is                                                                 |
| ----------- | -------------------------------------------------------------------------- |
| `frontend/` | Operator console — React + Vite (dashboard, live streaming, transactions, audit, e-ticket, reports, NMS, configuration) |
| `backend/`  | FastAPI REST API — ANPR platform (`app/api/v1`) + tolling layer (`app/toll`), SQLAlchemy, SQLite/Postgres |
| `pipeline/` | ANPR AI worker — capture → enhance → detect → track → plate → OCR → validate → dedup → speed → publish |
| `videos/`   | Demo footage served at `/videos` and read by the demo camera                |
| `scripts/`  | `setup.cmd`, `run-backend.cmd`, `run-pipeline.cmd`, `run-frontend.cmd`     |
| `docs/`     | Architecture / API / deployment / configuration reference                    |

## How it fits together

```
frontend (:5173) ──HTTP──► backend (:8000)
                              ├─ /api/...      toll API  (app/toll)
                              ├─ /api/v1/...   ANPR API  (app/api/v1)
                              ├─ /videos, /storage   static
                              └─ SQLite (backend/dev.db)
                                    ▲
                    recognitions (/api/v1/ingest/recognitions, X-API-Key)
                                    │
                              pipeline (YOLO + plate.pt + EasyOCR)
```

Every plate flows: **pipeline → ingest → rate lookup + FASTag deduction →
toll transaction → live SSE push + threshold alert.** The pipeline draws the
vehicle/plate boxes and the recognized text onto the frame it detected on and
ships that JPEG to the backend, which restreams it to the console's Live page
(`/api/cameras/{id}/live.mjpg`) — so the overlay can never lag the video.

## Run

```
start.cmd
```

Launches backend + pipeline + console. Console: <http://localhost:5173>
(login **admin / 12345678**). API docs: <http://localhost:8000/docs>.

Run pieces individually with `scripts\run-backend.cmd`, `scripts\run-pipeline.cmd`,
`scripts\run-frontend.cmd`. The pipeline is optional — without it the Live page
falls back to plain video with no detection overlay.

## Fresh clone

```
scripts\setup.cmd
```

Creates both virtualenvs and installs frontend deps. The venvs are build
artifacts (gitignored); the pipeline's includes torch/CUDA and is several GB.

## Config

- `backend/.env` — `ANPR_SECRET_KEY` (JWT), `ANPR_INGEST_API_KEY` (must match
  the pipeline), `ANPR_CORS_ORIGINS`, `ANPR_DATABASE_URL`. **Change the secrets
  before deploying.**
- `frontend/.env` — `VITE_BACKEND_URL` (default `http://localhost:8000`).
- Pipeline — env vars in `pipeline/anpr_pipeline/config.py` (`ANPR_PIPELINE_*`):
  OCR confidence, consensus, dedup TTL, device (`auto`/`cpu`/`cuda`), model paths.

## Tests

```
cd backend  && .venv\Scripts\python.exe -m pytest tests -q
cd pipeline && .venv\Scripts\python.exe -m pytest tests -q
cd frontend && npm run build
```

## Notes

- Toll rates, lanes, FASTag accounts, users and demo data are seeded on first
  boot (`backend/app/toll/seed.py`), including an "ANPR Demo Feed" camera bound
  to `videos/demo_video.mp4`.
- A detected plate with no FASTag account bills as a **Violation** (e-ticket) —
  that is the intended rule. Register plates under Configuration to see `Paid`.
- Auth: the console's `POST /api/auth/login` returns a JWT validated by
  `app/toll/api/deps.py`. The `/api/v1` ANPR endpoints use their own JWT/RBAC.
