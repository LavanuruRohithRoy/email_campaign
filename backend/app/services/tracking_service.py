from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EventType, TokenType
from app.models.tracking import EmailEvent, TrackingToken

logger = logging.getLogger(__name__)


async def resolve_token(token: str, expected_type: TokenType, db: AsyncSession) -> TrackingToken | None:
    result = await db.execute(
        select(TrackingToken).where(
            TrackingToken.token == token,
            TrackingToken.token_type == expected_type,
        )
    )
    return result.scalar_one_or_none()


async def record_open(token: str, ip_address: str, user_agent: str, db: AsyncSession) -> bool:
    tracking = await resolve_token(token, TokenType.OPEN, db)
    if not tracking:
        logger.warning("Invalid open token: %s", token)
        return False

    existing = await db.execute(
        select(EmailEvent).where(
            EmailEvent.contact_id == tracking.contact_id,
            EmailEvent.campaign_id == tracking.campaign_id,
            EmailEvent.event_type == EventType.OPENED,
        )
    )
    if existing.scalar_one_or_none():
        return True

    db.add(
        EmailEvent(
            contact_id=tracking.contact_id,
            campaign_id=tracking.campaign_id,
            event_type=EventType.OPENED,
            occurred_at=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_={},
        )
    )
    await db.commit()
    logger.info("Open recorded contact=%s campaign=%s", tracking.contact_id, tracking.campaign_id)
    return True


async def record_click(token: str, ip_address: str, user_agent: str, db: AsyncSession) -> str | None:
    tracking = await resolve_token(token, TokenType.CLICK, db)
    if not tracking or not tracking.target_url:
        logger.warning("Invalid click token: %s", token)
        return None

    db.add(
        EmailEvent(
            contact_id=tracking.contact_id,
            campaign_id=tracking.campaign_id,
            event_type=EventType.CLICKED,
            occurred_at=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_={"url": tracking.target_url},
        )
    )
    await db.commit()
    logger.info("Click recorded contact=%s url=%s", tracking.contact_id, tracking.target_url)
    return tracking.target_url
