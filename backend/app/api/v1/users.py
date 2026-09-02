from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import ROLE_ADMIN, hash_password, require_roles
from app.db import models
from app.db.session import get_db
from app.services.audit import audit

router = APIRouter(prefix="/users", tags=["users"])
admin_only = Depends(require_roles(ROLE_ADMIN))


@router.get("", response_model=schemas.Page[schemas.UserOut], dependencies=[admin_only])
def list_users(page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    page, page_size = max(page, 1), min(max(page_size, 1), 200)
    total = db.scalar(select(func.count(models.User.id))) or 0
    items = db.scalars(
        select(models.User)
        .order_by(models.User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return schemas.Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=schemas.UserOut, status_code=201)
def create_user(
    body: schemas.UserCreate,
    db: Session = Depends(get_db),
    actor=Depends(require_roles(ROLE_ADMIN)),
):
    if db.scalar(select(models.User).where(models.User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = models.User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=body.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit(db, actor.id, "user.create", f"users/{user.id}", {"email": user.email})
    return user


@router.patch("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    body: schemas.UserUpdate,
    db: Session = Depends(get_db),
    actor=Depends(require_roles(ROLE_ADMIN)),
):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    data = body.model_dump(exclude_unset=True)
    if "password" in data:
        user.hashed_password = hash_password(data.pop("password"))
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    audit(db, actor.id, "user.update", f"users/{user.id}", data)
    return user


@router.delete("/{user_id}", status_code=204)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor=Depends(require_roles(ROLE_ADMIN)),
):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == actor.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate yourself")
    user.is_active = False
    db.commit()
    audit(db, actor.id, "user.deactivate", f"users/{user.id}", {})
