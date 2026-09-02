import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(f"ANPR_{name}", default)


@dataclass
class PipelineConfig:
    # Use 127.0.0.1, not "localhost": on Windows localhost resolves to ::1 as
    # well as 127.0.0.1, and a server bound to IPv4 only leaves the IPv6
    # attempt to be silently dropped — every request then stalls ~2s before
    # falling back. That is fatal here, where live frames are pushed per frame.
    backend_url: str = field(default_factory=lambda: _env("BACKEND_URL", "http://127.0.0.1:8000"))
    ingest_api_key: str = field(default_factory=lambda: _env("INGEST_API_KEY", "dev-only-ingest-key-change-me"))
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL", "redis://localhost:6379/0"))
    region: str = field(default_factory=lambda: _env("PIPELINE_REGION", "IN"))
    min_ocr_confidence: float = field(
        default_factory=lambda: float(_env("PIPELINE_MIN_OCR_CONFIDENCE", "0.60"))
    )
    # Multi-frame consensus: a read below min_ocr_confidence still publishes
    # if the SAME text is read this many times within the window and each
    # read clears the lower consensus floor. One sharp frame is rare on a
    # moving vehicle; agreement across frames is strong evidence.
    consensus_min_confidence: float = field(
        default_factory=lambda: float(_env("PIPELINE_CONSENSUS_MIN_CONFIDENCE", "0.45"))
    )
    consensus_reads: int = field(
        default_factory=lambda: int(_env("PIPELINE_CONSENSUS_READS", "2"))
    )
    consensus_window_seconds: float = field(
        default_factory=lambda: float(_env("PIPELINE_CONSENSUS_WINDOW_SECONDS", "10"))
    )
    # Ignore full-frame plate detections whose center lies in this top strip
    # of the frame: camera OSD overlays (clock, camera name) live there and
    # constantly trigger the plate detector; real plates don't.
    ignore_top_ratio: float = field(
        default_factory=lambda: float(_env("PIPELINE_IGNORE_TOP_RATIO", "0.08"))
    )
    dedup_ttl_seconds: int = field(
        default_factory=lambda: int(_env("PIPELINE_DEDUP_TTL_SECONDS", "30"))
    )
    # Attempting a plate read on every unpublished track on every frame is the
    # dominant cost in a busy scene: each attempt is a plate-detector pass plus
    # an OCR pass, and vehicles that never yield a valid plate (parked cars,
    # distant traffic, signage) never publish — so they retry forever and drag
    # the whole camera down to a few fps. Attempts are throttled per track and
    # capped per frame instead; a vehicle in view for a second still gets
    # several chances.
    plate_retry_seconds: float = field(
        default_factory=lambda: float(_env("PIPELINE_PLATE_RETRY_SECONDS", "0.5"))
    )
    max_plate_attempts_per_frame: int = field(
        default_factory=lambda: int(_env("PIPELINE_MAX_PLATE_ATTEMPTS", "2"))
    )
    spool_dir: str = field(default_factory=lambda: _env("PIPELINE_SPOOL_DIR", "./data/spool"))
    # Compute device for AI backends: "auto" / "cpu" / "cuda" / "cuda:N".
    device: str = field(default_factory=lambda: _env("PIPELINE_DEVICE", "auto"))
    # Detection backends: "auto" tries YOLO then falls back to motion detection.
    vehicle_detector: str = field(default_factory=lambda: _env("PIPELINE_VEHICLE_DETECTOR", "auto"))
    plate_detector: str = field(default_factory=lambda: _env("PIPELINE_PLATE_DETECTOR", "auto"))
    ocr_engine: str = field(default_factory=lambda: _env("PIPELINE_OCR_ENGINE", "auto"))
    vehicle_model_path: str = field(default_factory=lambda: _env("PIPELINE_VEHICLE_MODEL", "yolov8n.pt"))
    plate_model_path: str = field(default_factory=lambda: _env("PIPELINE_PLATE_MODEL", "models/plate.pt"))
    # YOLO confidence gates. Kept low for moving vehicles: plates on a moving
    # car are blurrier and partly occluded, so a low detector gate keeps them
    # in play — the multi-frame consensus gate below filters false reads, not
    # the detector. Raise on a static/clean-plate deployment to cut noise.
    vehicle_conf: float = field(default_factory=lambda: float(_env("PIPELINE_VEHICLE_CONF", "0.30")))
    plate_conf: float = field(default_factory=lambda: float(_env("PIPELINE_PLATE_CONF", "0.25")))
    # YOLO inference size (longest side). Frames are downscaled to this
    # before detection, so it caps range: at 640 a 4K frame shrinks 6x and
    # distant plates vanish. Plates get a larger default; raise further on
    # GPU for more range, lower on CPU for speed.
    vehicle_imgsz: int = field(default_factory=lambda: int(_env("PIPELINE_VEHICLE_IMGSZ", "640")))
    plate_imgsz: int = field(default_factory=lambda: int(_env("PIPELINE_PLATE_IMGSZ", "1280")))
    # When no vehicle is detected, also try plate detection on the full frame
    # (close-up/cropped/parked vehicles). Costs one extra detector pass on
    # vehicle-less frames only.
    full_frame_plates: bool = field(
        default_factory=lambda: _env("PIPELINE_FULL_FRAME_PLATES", "1").lower()
        in ("1", "true", "yes")
    )
    # Cap on frames processed per second per camera (live-edge reads mean an
    # uncapped worker burns the whole GPU for redundant frames). Per-camera
    # override: cameras.config["process_fps"].
    max_process_fps: float = field(
        default_factory=lambda: float(_env("PIPELINE_MAX_FPS", "15"))
    )
    # Legacy knob: process every Nth read frame. The fps cap above is the
    # intended load control now; stride stays for file-source thinning.
    frame_stride: int = field(default_factory=lambda: int(_env("PIPELINE_FRAME_STRIDE", "1")))
    camera_refresh_seconds: int = field(
        default_factory=lambda: int(_env("PIPELINE_CAMERA_REFRESH_SECONDS", "60"))
    )
    # Live-view frames the pipeline ships to the backend (annotated, downscaled
    # JPEG). These are the exact frames detection ran on, so the box is always
    # on the right frame. Set width to 0 to disable pushing frames (falls back
    # to the backend's direct RTSP restream).
    stream_max_width: int = field(default_factory=lambda: int(_env("PIPELINE_STREAM_MAX_WIDTH", "960")))
    stream_jpeg_quality: int = field(default_factory=lambda: int(_env("PIPELINE_STREAM_JPEG_QUALITY", "75")))
