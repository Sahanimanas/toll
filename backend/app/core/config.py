from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ANPR_", env_file=".env", extra="ignore")

    app_name: str = "ANPR Platform"
    api_v1_prefix: str = "/api/v1"

    # Security
    secret_key: str = "dev-only-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    ingest_api_key: str = "dev-only-ingest-key-change-me"

    # Infrastructure
    database_url: str = "postgresql+psycopg://anpr:anpr@localhost:5432/anpr"
    redis_url: str = "redis://localhost:6379/0"
    evidence_dir: str = "./data/evidence"

    # Live MJPEG restream (dashboard live view)
    stream_fps: int = 30
    stream_max_width: int = 960
    stream_max_viewers: int = 4

    # Dev convenience: create tables at startup instead of requiring Alembic.
    auto_create_tables: bool = True

    # --- Toll layer (MLFF tolling on top of ANPR) ---
    # Public storage for plate crops (served at /storage) and the demo video
    # folder (served at /videos). Empty videos dir -> resolved to the sibling
    # toll-plaza/videos at startup.
    toll_storage_dir: str = "./storage"
    toll_videos_dir: str = ""
    toll_enabled: bool = True

    # Bootstrap admin (created on first startup if no users exist)
    first_admin_email: str = "admin@example.com"
    first_admin_password: str = "admin12345"

    cors_origins: list[str] = ["http://localhost:8080", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
