"""Compat auth: POST /api/auth/login (JSON) -> {token, user}."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.session import get_db
from app.toll import models
from app.toll.api.deps import auth_required, create_toll_token

router = APIRouter(prefix="/api/auth", tags=["toll-auth"])


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    username = (body or {}).get("username", "")
    password = (body or {}).get("password", "")

    user = db.scalar(select(models.TollUser).where(models.TollUser.username == username))
    if user is None:  # allow login by email too
        user = db.scalar(select(models.TollUser).where(models.TollUser.email == username))

    if (user is None or not user.hashed_password
            or not verify_password(password, user.hashed_password)):
        return JSONResponse(status_code=401, content={"error": "Invalid credentials"})
    if user.status != "Active":
        return JSONResponse(status_code=403, content={"error": "Account disabled"})

    token = create_toll_token(user.id)
    return {
        "token": token,
        "user": {"name": user.name, "username": user.username, "role": "admin"},
    }


@router.post("/logout")
def logout(user=Depends(auth_required)):
    # Stateless JWT — nothing to revoke server-side; client drops the token.
    return {"ok": True}
