"""Auth for the toll compat API.

The toll frontend logs in with username/password (JSON), stores whatever token
string it gets back, and resends it as ``Authorization: Bearer <token>``. We
issue a JWT (same secret as the ANPR platform, distinct ``type=toll``) whose
subject is the string ``TollUser.id``, and validate it here.
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.toll import models


def create_toll_token(user_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "toll",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes * 48),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def _decode_toll_token(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")
    if payload.get("type") != "toll":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")
    return str(payload["sub"])


def auth_required(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.TollUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")
    token = authorization.split(" ", 1)[1].strip()
    user_id = _decode_toll_token(token)
    user = db.get(models.TollUser, user_id)
    if user is None or user.status != "Active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")
    return user
