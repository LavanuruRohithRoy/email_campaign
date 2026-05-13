from __future__ import annotations

import logging
from uuid import UUID

from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)


async def invalidate_analytics_cache(org_id: UUID, campaign_id: UUID | None = None) -> None:
    keys = [f"dashboard_analytics:{org_id}"]
    if campaign_id is not None:
        keys.append(f"campaign_analytics:{campaign_id}")

    redis = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        await redis.delete(*keys)
    except Exception as exc:
        logger.warning("Failed to invalidate analytics cache for keys=%s error=%s", keys, exc)
    finally:
        await redis.close()
