"""Authentication: bcrypt password hashing, short-lived JWT access tokens with
long-lived refresh tokens (architecture section 6)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# auto_error=False so endpoints can serve anonymous visitors too.
bearer = HTTPBearer(auto_error=False)


def hash_password(raw: str) -> str:
    # bcrypt silently truncates past 72 bytes; refuse rather than accept a
    # password whose tail is ignored.
    if len(raw.encode("utf-8")) > 72:
        raise ValueError("password too long")
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(raw, hashed)
    except ValueError:
        return False


def _token(subject: str, kind: str, expires: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "kind": kind,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
    }
    return jwt.encode(payload, settings.wanas_secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _token(user_id, "access", timedelta(minutes=settings.access_token_minutes))


def create_refresh_token(user_id: str) -> str:
    return _token(user_id, "refresh", timedelta(days=settings.refresh_token_days))


def decode_token(token: str, *, expected_kind: str = "access") -> str:
    try:
        payload = jwt.decode(token, settings.wanas_secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    if payload.get("kind") != expected_kind:
        # A refresh token must never be usable as an access token.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return subject


def current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    if credentials is None:
        return None
    try:
        user_id = decode_token(credentials.credentials)
    except HTTPException:
        return None
    return db.get(User, user_id)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    user = db.get(User, decode_token(credentials.credentials))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
MaybeUser = Annotated[User | None, Depends(current_user_optional)]
DbSession = Annotated[Session, Depends(get_db)]
