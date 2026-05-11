from __future__ import annotations

from fastapi import HTTPException
from redis.asyncio import Redis


async def check_login_rate_limit(ip: str, redis: Redis) -> None:
    key = f"login_attempts:{ip}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 900)
    if count > 5:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again in 15 minutes.",
            headers={"Retry-After": "900"},
        )


async def reset_login_rate_limit(ip: str, redis: Redis) -> None:
    await redis.delete(f"login_attempts:{ip}")
