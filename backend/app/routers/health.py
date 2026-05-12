from __future__ import annotations

import logging
from fastapi import APIRouter
from sqlalchemy import text

from app.database import engine
from app.dependencies import get_redis

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict[str, str]:
    # Attempt DB connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("DB readiness check failed: %s", e)
        return {"status": "error", "component": "db"}

    # Attempt Redis
    try:
        redis = await get_redis().__anext__()
        try:
            await redis.ping()
        finally:
            try:
                await redis.close()
            except Exception:
                pass
    except Exception as e:
        logger.warning("Redis readiness check failed: %s", e)
        return {"status": "error", "component": "redis"}

    return {"status": "ready"}
