from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.core import User
from app.utils.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


async def get_redis() -> AsyncGenerator[Redis, None]:
    client = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        yield client
    finally:
        await client.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid token", "code": "INVALID_TOKEN"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid token payload", "code": "INVALID_TOKEN"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid token", "code": "INVALID_TOKEN"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await db.get(User, user_uuid)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "User not found or inactive", "code": "UNAUTHORIZED"},
        )
    return user


def require_role(*roles: str) -> Callable[[User], Awaitable[User]]:
    async def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"detail": "You do not have permission to perform this action", "code": "INSUFFICIENT_PERMISSIONS"},
                headers={"X-Required-Role": str(roles)},
            )
        return current_user

    return role_dependency
