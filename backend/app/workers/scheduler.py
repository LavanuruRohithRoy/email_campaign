from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models.campaigns import Campaign
from app.models.enums import CampaignStatus
from app.services.campaign_service import enqueue_campaign

logger = logging.getLogger(__name__)


async def check_scheduled_campaigns(db: AsyncSession | None = None) -> None:
    if db is not None:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Campaign).where(
                Campaign.status == CampaignStatus.SCHEDULED,
                Campaign.scheduled_at <= now,
            )
        )
        for campaign in result.scalars().all():
            try:
                await enqueue_campaign(campaign.org_id, campaign.id, db)
                logger.info("Triggered campaign %s", campaign.id)
            except Exception as exc:
                logger.error("Failed %s: %s", campaign.id, exc)
        return

    async with SessionLocal() as db_session:
        await check_scheduled_campaigns(db_session)


async def scheduler_loop() -> None:
    logger.info("Scheduler started")
    while True:
        try:
            await check_scheduled_campaigns()
        except Exception as exc:
            logger.error("Scheduler error: %s", exc)
        await asyncio.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(scheduler_loop())
