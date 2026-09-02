"""/api/users CRUD (Admin page) — backed by toll_users."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.toll import models
from app.toll.api.deps import auth_required

router = APIRouter(dependencies=[Depends(auth_required)])


def _out(u: models.TollUser) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role,
            "plaza": u.plaza, "last": u.last, "status": u.status, "color": u.color,
            "username": u.username}


@router.get("/api/users")
def list_users(db: Session = Depends(get_db)):
    return [_out(u) for u in db.scalars(select(models.TollUser)).all()]


@router.post("/api/users")
async def create_user(request: Request, db: Session = Depends(get_db)):
    b = await request.json()
    u = models.TollUser(
        id=str(uuid.uuid4()), name=b.get("name", ""), email=b.get("email", ""),
        username=b.get("username", ""), role=b.get("role", "Operator"),
        plaza=b.get("plaza", "NH-48 Gurugram"), last="Never",
        status=b.get("status", "Active"), color=b.get("color", "#2563eb"),
    )
    db.add(u)
    db.commit()
    return _out(u)


@router.patch("/api/users/{uid}")
async def patch_user(uid: str, request: Request, db: Session = Depends(get_db)):
    u = db.get(models.TollUser, uid)
    if u is None:
        raise HTTPException(404, "Not found")
    b = await request.json()
    for field in ("name", "email", "username", "role", "plaza", "last", "status", "color"):
        if b.get(field) is not None:
            setattr(u, field, b[field])
    db.commit()
    return _out(u)


@router.delete("/api/users/{uid}")
def delete_user(uid: str, db: Session = Depends(get_db)):
    u = db.get(models.TollUser, uid)
    if u is None:
        raise HTTPException(404, "Not found")
    db.delete(u)
    db.commit()
    return {"ok": True}
