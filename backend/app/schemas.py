from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# --- Auth ---


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Users ---


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = ""
    role: str = Field(default="viewer", pattern="^(admin|operator|viewer)$")
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = Field(default=None, pattern="^(admin|operator|viewer)$")
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# --- Cameras ---


class CameraBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: str = ""
    rtsp_url: str = Field(min_length=1, max_length=500)
    direction: str = ""
    lane: str = ""
    latitude: float | None = None
    longitude: float | None = None
    config: dict = Field(default_factory=dict)
    is_active: bool = True


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    rtsp_url: str | None = None
    direction: str | None = None
    lane: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    config: dict | None = None
    is_active: bool | None = None


class CameraOut(CameraBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class DetectionBoxIn(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    kind: str = Field(default="vehicle", pattern="^(vehicle|plate)$")
    label: str = Field(default="", max_length=32)


class LiveDetectionsIn(BaseModel):
    camera_id: int
    boxes: list[DetectionBoxIn] = Field(default_factory=list, max_length=32)


class StreamTestRequest(BaseModel):
    stream_url: str = Field(min_length=1, max_length=500)


class StreamTestResult(BaseModel):
    ok: bool
    detail: str = ""
    width: int | None = None
    height: int | None = None
    latency_ms: int | None = None


# --- Recognitions ---


class RecognitionIngest(BaseModel):
    camera_id: int
    plate_text: str = Field(min_length=2, max_length=20)
    plate_confidence: float = Field(ge=0.0, le=1.0)
    ocr_raw: str = ""
    vehicle_type: str = "unknown"
    vehicle_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    speed_kmh: float | None = Field(default=None, ge=0.0, le=400.0)
    direction: str = ""
    track_id: str = ""
    bbox: dict = Field(default_factory=dict)
    captured_at: datetime


class RecognitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    camera_id: int
    plate_text: str
    plate_confidence: float
    vehicle_type: str
    vehicle_confidence: float
    speed_kmh: float | None
    direction: str
    track_id: str
    bbox: dict
    has_evidence: bool = False
    captured_at: datetime
    created_at: datetime


# --- Watchlist ---


class WatchlistCreate(BaseModel):
    plate_text: str = Field(min_length=2, max_length=20)
    reason: str = ""
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    is_active: bool = True


class WatchlistOut(WatchlistCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by: int | None
    created_at: datetime


# --- Alerts ---


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    recognition_id: int
    watchlist_id: int | None
    type: str
    severity: str
    message: str
    acknowledged: bool
    acknowledged_by: int | None
    created_at: datetime


# --- Stats ---


class StatsSummary(BaseModel):
    recognitions_today: int
    recognitions_total: int
    open_alerts: int
    active_cameras: int
    per_camera_today: dict[str, int]
