from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.config import settings
from app.dependencies import get_redis, get_current_user
from app.models.core import User


async def check_login_rate_limit(ip: str, redis: Redis) -> None:
    key = f"login_attempts:{ip}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS)
    if count > settings.RATE_LIMIT_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail={"detail": "Too many login attempts. Try again later.", "code": "RATE_LIMIT_EXCEEDED"},
            headers={"Retry-After": str(settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS)},
        )


async def reset_login_rate_limit(ip: str, redis: Redis) -> None:
    await redis.delete(f"login_attempts:{ip}")


def ip_rate_limit(limit: int | None = None, window: int | None = None):
    """Factory dependency for IP-based rate limiting.

    Usage: Depends(ip_rate_limit()) or Depends(ip_rate_limit(limit=10, window=60))
    """
    lim = limit or settings.RATE_LIMIT_WEBHOOK_PER_MINUTE
    win = window or 60

    async def _dep(request: Request, redis: Redis = Depends(get_redis)) -> None:
        ip = (
            request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
        )
        # x-forwarded-for may contain comma-separated list
        ip = ip.split(",")[0].strip()
        key = f"rl:ip:{ip}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, win)
        if count > lim:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"detail": "Too many requests", "code": "RATE_LIMIT_EXCEEDED"},
                headers={"Retry-After": str(win)},
            )

    return _dep


def user_rate_limit(limit: int = 100, window: int = 60):
    """Factory dependency for user-based rate limiting."""

    async def _dep(current_user: User = Depends(get_current_user), redis: Redis = Depends(get_redis)) -> None:
        key = f"rl:user:{current_user.id}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"detail": "Too many requests for user", "code": "RATE_LIMIT_EXCEEDED"},
                headers={"Retry-After": str(window)},
            )

    return _dep


def org_rate_limit(limit: int = 1000, window: int = 3600):
    """Factory dependency for organisation-wide rate limiting."""

    async def _dep(current_user: User = Depends(get_current_user), redis: Redis = Depends(get_redis)) -> None:
        key = f"rl:org:{current_user.org_id}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"detail": "Organisation rate limit exceeded", "code": "RATE_LIMIT_EXCEEDED"},
                headers={"Retry-After": str(window)},
            )

    return _dep
