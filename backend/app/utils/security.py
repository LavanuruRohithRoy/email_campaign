from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.config import settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(data: dict[str, str], expires_delta: timedelta) -> str:
    payload: dict[str, str | datetime] = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        if not isinstance(decoded, dict):
            raise ValueError("Invalid payload type")
        return decoded
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid token", "code": "INVALID_TOKEN"},
        ) from exc
