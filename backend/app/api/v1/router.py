from fastapi import APIRouter

from app.api.v1 import alerts, auth, cameras, ingest, recognitions, stats, users, watchlist

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(cameras.router)
api_router.include_router(recognitions.router)
api_router.include_router(ingest.router)
api_router.include_router(watchlist.router)
api_router.include_router(alerts.router)
api_router.include_router(stats.router)
