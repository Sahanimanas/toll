from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Query, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
ingest_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"
ROLES = (ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject: str, token_type: str, expires_minutes: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    return _create_token(str(user_id), "access", settings.access_token_expire_minutes)


def create_refresh_token(user_id: int) -> str:
    settings = get_settings()
    return _create_token(str(user_id), "refresh", settings.refresh_token_expire_minutes)


def decode_token(token: str, expected_type: str) -> int:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    if payload.get("type") != expected_type:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
    return int(payload["sub"])


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from app.db import models

    user_id = decode_token(token, "access")
    user = db.get(models.User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or disabled")
    return user


def get_current_user_or_query_token(
    header_token: str | None = Depends(oauth2_scheme_optional),
    token: str | None = Query(default=None, description="Access token fallback"),
    db: Session = Depends(get_db),
):
    """Auth via Bearer header OR `?token=` query param.

    Only for media endpoints consumed by <img>/<video> tags, which cannot
    send an Authorization header. The header wins when both are present.
    """
    from app.db import models

    raw = header_token or token
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = decode_token(raw, "access")
    user = db.get(models.User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or disabled")
    return user


def require_roles(*roles: str):
    def dependency(user=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return dependency


def require_ingest_key(api_key: str | None = Security(ingest_key_header)) -> None:
    settings = get_settings()
    if not api_key or api_key != settings.ingest_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid ingest API key")
