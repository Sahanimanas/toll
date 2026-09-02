"""Aggregates every toll compat router. Included in the app with no extra
prefix — each router declares its own absolute /api/... paths."""

from fastapi import APIRouter

from app.toll.api import anpr, auth, cameras, config, data, users

toll_router = APIRouter()
toll_router.include_router(auth.router)
toll_router.include_router(data.router)
toll_router.include_router(config.router)
toll_router.include_router(cameras.router)
# Unauthenticated live-video media (<img> tags cannot send auth headers).
# Registered before the authed router's /api/cameras/{cid}/... routes matter
# only for path distinctness; the suffixes (.mjpg/.jpg) keep them unambiguous.
toll_router.include_router(cameras.media_router)
toll_router.include_router(users.router)
toll_router.include_router(anpr.router)
