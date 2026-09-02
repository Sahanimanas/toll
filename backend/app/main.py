import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db import models
from app.db.session import Base, SessionLocal, engine

# Import toll models so their tables are registered on Base.metadata before
# create_all runs, and the compat router + seed for the tolling layer.
from app.toll import models as toll_models  # noqa: F401
from app.toll.api.router import toll_router
from app.toll.paths import videos_dir
from app.toll.seed import seed_toll

logger = logging.getLogger(__name__)


def bootstrap_admin() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        if db.scalar(select(models.User).limit(1)) is None:
            db.add(
                models.User(
                    email=settings.first_admin_email,
                    hashed_password=hash_password(settings.first_admin_password),
                    full_name="Administrator",
                    role="admin",
                )
            )
            db.commit()
            logger.warning(
                "Created bootstrap admin %s — change its password immediately.",
                settings.first_admin_email,
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    bootstrap_admin()
    if settings.toll_enabled:
        with SessionLocal() as db:
            seed_toll(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/api/v1/health", tags=["health"])
    def health():
        return {"status": "ok", "service": settings.app_name, "version": "0.1.0"}

    if settings.toll_enabled:
        # Toll compat API (absolute /api/... paths matching the toll frontend).
        app.include_router(toll_router)

        # Public static: plate crops (/storage) and demo/camera videos (/videos).
        storage_dir = Path(settings.toll_storage_dir)
        (storage_dir / "plates").mkdir(parents=True, exist_ok=True)
        app.mount("/storage", StaticFiles(directory=str(storage_dir)), name="storage")

        vids = videos_dir()
        if vids.exists():
            app.mount("/videos", StaticFiles(directory=str(vids)), name="videos")
        else:
            logger.warning("toll videos dir not found: %s (/videos disabled)", vids)

    return app


app = create_app()
