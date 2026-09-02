# API Reference

Base URL: `/api/v1`. Interactive OpenAPI docs at `/docs`.

Authentication: `Authorization: Bearer <access_token>` for user endpoints;
`X-API-Key: <ingest key>` for pipeline endpoints.

Paginated responses share the envelope:

```json
{ "items": [...], "total": 1234, "page": 1, "page_size": 50 }
```

## Auth

| Method | Path            | Notes                                            |
| ------ | --------------- | ------------------------------------------------ |
| POST   | `/auth/login`   | OAuth2 form (`username`, `password`) → token pair |
| POST   | `/auth/refresh` | `{ "refresh_token": "..." }` → new token pair     |
| GET    | `/auth/me`      | Current user                                     |

## Users (admin only)

| Method | Path          | Notes                                   |
| ------ | ------------- | --------------------------------------- |
| GET    | `/users`      | Paginated list                          |
| POST   | `/users`      | `email`, `password`, `role`, `full_name` |
| PATCH  | `/users/{id}` | Partial update; `password` re-hashes    |
| DELETE | `/users/{id}` | Deactivates (soft)                      |

## Cameras

| Method | Path             | Roles           | Notes                                |
| ------ | ---------------- | --------------- | ------------------------------------ |
| GET    | `/cameras`       | any             | `?active_only=true` filter           |
| GET    | `/cameras/{id}`  | any             |                                      |
| GET    | `/cameras/{id}/stream` | any       | Live MJPEG restream (see below)      |
| GET    | `/cameras/{id}/snapshot` | any     | Latest single annotated JPEG frame (see below) |
| POST   | `/cameras`       | admin, operator | `config` holds tuning (see below)    |
| POST   | `/cameras/test`  | admin, operator | Probe a stream URL (see below)       |
| PATCH  | `/cameras/{id}`  | admin, operator |                                      |
| DELETE | `/cameras/{id}`  | admin           | Deactivates (soft)                   |

Camera `config` keys used by the platform: `speed_limit_kmh` (alerting),
`meters_per_pixel` (speed estimation calibration).

`POST /cameras/test` takes `{"stream_url": "..."}` (RTSP, HTTP(S) MJPEG,
file path, or device index — same values accepted by `rtsp_url`) and tries
to open it server-side and decode one frame. Always returns `200` with
`{ok, detail, width, height, latency_ms}` — `ok: false` carries the
connection error in `detail`. `501` if OpenCV is not installed. Nothing is
saved; used by the dashboard camera form's Test button.

`/cameras/{id}/stream` returns `multipart/x-mixed-replace` MJPEG that renders
in a plain `<img>` tag. Because image tags cannot send headers, it also
accepts the access token as `?token=<jwt>`. The preview is downscaled
(`ANPR_STREAM_MAX_WIDTH`) and throttled (`ANPR_STREAM_FPS`); concurrent
viewers are capped (`ANPR_STREAM_MAX_VIEWERS`). Errors: `503` all viewer
slots busy, and (fallback path only) `502` camera unreachable, `501` OpenCV
not installed.

When the pipeline is feeding annotated frames for the camera, both `/stream`
and `/snapshot` serve those frames directly — no camera connection, no decode,
overlays already baked in (green vehicle box, amber plate box, plate-text
label, drawn by the pipeline on the exact frame it detected on). When no fresh
pipeline frame exists, `/stream` falls back to a direct RTSP restream with
server-drawn overlays from the camera's last ~6 s of recognitions.

`/cameras/{id}/snapshot` returns the single latest annotated JPEG (`image/jpeg`,
`Cache-Control: no-store`); `503` if the pipeline isn't feeding this camera.
The dashboard's canvas live view polls it so each fetch shows the newest frame
rather than a buffered/stale one. Same auth as `/stream` (bearer or `?token=`).

## Recognitions

| Method | Path                          | Notes                                       |
| ------ | ----------------------------- | ------------------------------------------- |
| GET    | `/recognitions`               | Filters: `plate` (substring), `camera_id`, `vehicle_type`, `min_confidence`, `date_from`, `date_to`; sorted newest first |
| GET    | `/recognitions/{id}`          |                                             |
| GET    | `/recognitions/{id}/evidence` | JPEG; `?kind=full` (default) or `?kind=plate` |

## Ingest (X-API-Key)

| Method | Path                   | Notes                                            |
| ------ | ---------------------- | ------------------------------------------------ |
| POST   | `/ingest/recognitions` | multipart: `payload` (JSON string), optional `frame` and `plate` JPEGs |
| GET    | `/ingest/cameras`      | Active camera list for pipeline workers          |
| POST   | `/ingest/detections`   | Current-frame detection boxes for the live-view overlay (in-memory, ~3 s TTL, nothing persisted) |
| POST   | `/ingest/frame`        | multipart: `camera_id` (form), `frame` (annotated JPEG). Newest annotated live-view frame; cached in-memory (~5 s TTL), served by `/cameras/{id}/snapshot` and `/stream`. Nothing persisted |

`payload` schema: `camera_id`, `plate_text`, `plate_confidence` (0–1),
`ocr_raw`, `vehicle_type`, `vehicle_confidence`, `speed_kmh?`, `direction`,
`track_id`, `bbox`, `captured_at` (ISO-8601).

## Watchlist

| Method | Path              | Roles           |
| ------ | ----------------- | --------------- |
| GET    | `/watchlist`      | any             |
| POST   | `/watchlist`      | admin, operator |
| DELETE | `/watchlist/{id}` | admin, operator |

## Alerts

| Method | Path                | Roles           | Notes                                |
| ------ | ------------------- | --------------- | ------------------------------------ |
| GET    | `/alerts`           | any             | Filters: `acknowledged`, `severity`  |
| POST   | `/alerts/{id}/ack`  | admin, operator |                                      |

## Stats & health

| Method | Path             | Notes                                          |
| ------ | ---------------- | ---------------------------------------------- |
| GET    | `/stats/summary` | Today/total counts, open alerts, per-camera    |
| GET    | `/health`        | Unauthenticated liveness probe                 |
