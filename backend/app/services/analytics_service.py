from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracking import EmailEvent
from app.models.contacts import Contact
from app.models.campaigns import Campaign
from app.models.enums import EventType, ContactStatus
from app.schemas.analytics import (
    AnalyticsTimeSeriesPoint,
    CampaignAnalyticsResponse,
    CampaignPerformanceItem,
    DashboardAnalyticsResponse,
    TopCampaignsResponse,
)
from app.utils.s3 import upload_report_csv_to_s3

ANALYTICS_CACHE_TTL_SECONDS = 300


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


async def _campaign_exists(org_id: UUID, campaign_id: UUID, db: AsyncSession) -> bool:
    campaign = await db.scalar(select(Campaign.id).where(Campaign.id == campaign_id, Campaign.org_id == org_id))
    return campaign is not None


async def _event_counts(
    org_id: UUID,
    db: AsyncSession,
    campaign_id: UUID | None = None,
) -> dict[EventType, int]:
    query = (
        select(EmailEvent.event_type, func.count(EmailEvent.id))
        .join(Campaign, Campaign.id == EmailEvent.campaign_id)
        .where(Campaign.org_id == org_id)
        .group_by(EmailEvent.event_type)
    )
    if campaign_id is not None:
        query = query.where(EmailEvent.campaign_id == campaign_id)
    result = await db.execute(query)
    return {event_type: int(count) for event_type, count in result.all()}


def _campaign_response(campaign_id: UUID, counts: dict[EventType, int]) -> CampaignAnalyticsResponse:
    sent = counts.get(EventType.SENT, 0)
    delivered = counts.get(EventType.DELIVERED, 0)
    opened = counts.get(EventType.OPENED, 0)
    clicked = counts.get(EventType.CLICKED, 0)
    bounced = counts.get(EventType.BOUNCED, 0)
    complained = counts.get(EventType.COMPLAINED, 0)
    unsubscribed = counts.get(EventType.UNSUBSCRIBED, 0)
    return CampaignAnalyticsResponse(
        campaign_id=campaign_id,
        sent=sent,
        delivered=delivered,
        opened=opened,
        clicked=clicked,
        bounced=bounced,
        complained=complained,
        unsubscribed=unsubscribed,
        open_rate=_rate(opened, delivered),
        click_rate=_rate(clicked, delivered),
        bounce_rate=_rate(bounced, sent),
        complaint_rate=_rate(complained, sent),
        unsubscribe_rate=_rate(unsubscribed, delivered),
    )


async def get_campaign_analytics(
    org_id: UUID,
    campaign_id: UUID,
    db: AsyncSession,
    redis: Redis,
) -> CampaignAnalyticsResponse:
    cache_key = f"campaign_analytics:{campaign_id}"
    cached = await redis.get(cache_key)
    if isinstance(cached, bytes):
        cached = cached.decode("utf-8")
    if isinstance(cached, str):
        return CampaignAnalyticsResponse.model_validate_json(cached)

    if not await _campaign_exists(org_id, campaign_id, db):
        raise ValueError("NOT_FOUND")

    response = _campaign_response(campaign_id, await _event_counts(org_id, db, campaign_id))
    await redis.setex(cache_key, ANALYTICS_CACHE_TTL_SECONDS, response.model_dump_json())
    return response


async def get_dashboard_analytics(
    org_id: UUID,
    db: AsyncSession,
    redis: Redis,
) -> DashboardAnalyticsResponse:
    cache_key = f"dashboard_analytics:{org_id}"
    cached = await redis.get(cache_key)
    if isinstance(cached, bytes):
        cached = cached.decode("utf-8")
    if isinstance(cached, str):
        return DashboardAnalyticsResponse.model_validate_json(cached)

    total_contacts = int(
        await db.scalar(select(func.count(Contact.id)).where(Contact.org_id == org_id)) or 0
    )
    active_contacts = int(
        await db.scalar(
            select(func.count(Contact.id)).where(
                Contact.org_id == org_id,
                Contact.status == ContactStatus.ACTIVE,
            )
        )
        or 0
    )
    total_campaigns = int(
        await db.scalar(select(func.count(Campaign.id)).where(Campaign.org_id == org_id)) or 0
    )
    counts = await _event_counts(org_id, db)
    total_sent = counts.get(EventType.SENT, 0)
    total_opens = counts.get(EventType.OPENED, 0)
    total_clicks = counts.get(EventType.CLICKED, 0)
    total_delivered = counts.get(EventType.DELIVERED, 0)
    response = DashboardAnalyticsResponse(
        total_contacts=total_contacts,
        active_contacts=active_contacts,
        total_campaigns=total_campaigns,
        total_sent=total_sent,
        total_opens=total_opens,
        total_clicks=total_clicks,
        avg_open_rate=_rate(total_opens, total_delivered),
        avg_click_rate=_rate(total_clicks, total_delivered),
    )
    await redis.setex(cache_key, ANALYTICS_CACHE_TTL_SECONDS, response.model_dump_json())
    return response


async def get_top_campaigns(
    org_id: UUID,
    limit: int,
    db: AsyncSession,
) -> TopCampaignsResponse:
    sent_count = func.sum(case((EmailEvent.event_type == EventType.SENT, 1), else_=0))
    delivered_count = func.sum(case((EmailEvent.event_type == EventType.DELIVERED, 1), else_=0))
    opened_count = func.sum(case((EmailEvent.event_type == EventType.OPENED, 1), else_=0))
    clicked_count = func.sum(case((EmailEvent.event_type == EventType.CLICKED, 1), else_=0))
    result = await db.execute(
        select(
            Campaign.id,
            Campaign.name,
            Campaign.created_at,
            sent_count.label("sent"),
            delivered_count.label("delivered"),
            opened_count.label("opened"),
            clicked_count.label("clicked"),
        )
        .join(EmailEvent, EmailEvent.campaign_id == Campaign.id)
        .where(Campaign.org_id == org_id)
        .group_by(Campaign.id, Campaign.name, Campaign.created_at)
        .having(sent_count > 0)
    )
    items = [
        CampaignPerformanceItem(
            campaign_id=campaign_id,
            campaign_name=name,
            sent=int(sent or 0),
            open_rate=_rate(int(opened or 0), int(delivered or 0)),
            click_rate=_rate(int(clicked or 0), int(delivered or 0)),
            created_at=created_at,
        )
        for campaign_id, name, created_at, sent, delivered, opened, clicked in result.all()
    ]
    items.sort(key=lambda item: (item.open_rate, item.click_rate), reverse=True)
    return TopCampaignsResponse(items=items[:limit])


async def _event_timeseries(
    org_id: UUID,
    event_type: EventType,
    days: int,
    db: AsyncSession,
) -> list[AnalyticsTimeSeriesPoint]:
    now = datetime.now(timezone.utc)
    start_at = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
    day_bucket = func.date_trunc("day", EmailEvent.occurred_at).label("day")
    result = await db.execute(
        select(day_bucket, func.count(EmailEvent.id))
        .join(Campaign, Campaign.id == EmailEvent.campaign_id)
        .where(
            Campaign.org_id == org_id,
            EmailEvent.event_type == event_type,
            EmailEvent.occurred_at >= start_at,
        )
        .group_by(day_bucket)
        .order_by(day_bucket.asc())
    )
    return [
        AnalyticsTimeSeriesPoint(timestamp=timestamp, value=int(value))
        for timestamp, value in result.all()
    ]


async def get_open_timeseries(
    org_id: UUID,
    days: int,
    db: AsyncSession,
) -> list[AnalyticsTimeSeriesPoint]:
    return await _event_timeseries(org_id, EventType.OPENED, days, db)


async def get_click_timeseries(
    org_id: UUID,
    days: int,
    db: AsyncSession,
) -> list[AnalyticsTimeSeriesPoint]:
    return await _event_timeseries(org_id, EventType.CLICKED, days, db)


async def export_campaign_report_csv(
    org_id: UUID,
    campaign_id: UUID,
    db: AsyncSession,
) -> str:
    if not await _campaign_exists(org_id, campaign_id, db):
        raise ValueError("NOT_FOUND")

    event_flags = [
        ("sent", EventType.SENT),
        ("delivered", EventType.DELIVERED),
        ("opened", EventType.OPENED),
        ("clicked", EventType.CLICKED),
        ("bounced", EventType.BOUNCED),
        ("complained", EventType.COMPLAINED),
        ("unsubscribed", EventType.UNSUBSCRIBED),
    ]
    columns = [
        Contact.email,
        *[
            func.max(case((EmailEvent.event_type == event_type, 1), else_=0)).label(label)
            for label, event_type in event_flags
        ],
    ]
    result = await db.execute(
        select(*columns)
        .join(EmailEvent, EmailEvent.contact_id == Contact.id)
        .join(Campaign, Campaign.id == EmailEvent.campaign_id)
        .where(
            Contact.org_id == org_id,
            Campaign.org_id == org_id,
            EmailEvent.campaign_id == campaign_id,
        )
        .group_by(Contact.email)
        .order_by(Contact.email.asc())
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email", *[label for label, _ in event_flags]])
    for row in result.all():
        email, *values = row
        writer.writerow([email, *[bool(value) for value in values]])

    return await upload_report_csv_to_s3(
        output.getvalue().encode("utf-8"),
        f"campaign-{campaign_id}-report.csv",
    )
