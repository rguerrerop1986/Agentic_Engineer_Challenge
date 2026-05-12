"""Password hashing and JWT helpers."""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.constants import UTF_8


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plain password matches the bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode(UTF_8),
        hashed_password.encode(UTF_8),
    )


def hash_password(password: str) -> str:
    """Return a bcrypt hash string suitable for storing on the user record."""
    return bcrypt.hashpw(password.encode(UTF_8), bcrypt.gensalt()).decode(UTF_8)


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """Encode a signed JWT access token with subject and expiry claims."""
    settings = get_settings()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode: dict[str, Any] = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str | None:
    """Return the JWT subject (user id as string) if the token is valid, else None."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        sub = payload.get("sub")
        if sub is None or not isinstance(sub, str):
            return None
        return sub
    except JWTError:
        return None
