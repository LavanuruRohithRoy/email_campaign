from __future__ import annotations

import secrets
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.campaigns import Campaign
from app.models.contacts import Contact
from app.models.core import Organisation, User
from app.models.enums import CampaignStatus, ContactSource, ContactStatus, EventType, TokenType, UserRole
from app.models.tracking import EmailEvent, TrackingToken
from app.utils.security import hash_password


@pytest.fixture()
async def seed_tracking_tokens(db_session) -> dict[str, object]:
    org = Organisation(name=f"Tracking Org {uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        org_id=org.id,
        email=f"tracking-admin-{uuid4().hex}@example.com",
        password_hash=hash_password("password123"),
        full_name="Tracking Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    contact = Contact(
        org_id=org.id,
        email=f"tracking-contact-{uuid4().hex}@example.com",
        first_name="Track",
        last_name="User",
        status=ContactStatus.ACTIVE,
        custom_fields={},
        source=ContactSource.MANUAL,
    )
    db_session.add(contact)
    await db_session.flush()

    campaign = Campaign(
        org_id=org.id,
        name="Tracking Campaign",
        subject="Track Subject",
        from_name="Tracking Team",
        from_email="tracking@example.com",
        status=CampaignStatus.SENT,
        created_by=user.id,
    )
    db_session.add(campaign)
    await db_session.flush()

    open_token = secrets.token_urlsafe(16)
    click_token = secrets.token_urlsafe(16)
    unsub_token = secrets.token_urlsafe(16)
    click_url = "https://example.com/landing"

    db_session.add_all(
        [
            TrackingToken(
                token=open_token,
                contact_id=contact.id,
                campaign_id=campaign.id,
                token_type=TokenType.OPEN,
            ),
            TrackingToken(
                token=click_token,
                contact_id=contact.id,
                campaign_id=campaign.id,
                token_type=TokenType.CLICK,
                target_url=click_url,
            ),
            TrackingToken(
                token=unsub_token,
                contact_id=contact.id,
                campaign_id=campaign.id,
                token_type=TokenType.UNSUBSCRIBE,
            ),
        ]
    )
    await db_session.commit()

    return {
        "open_token": open_token,
        "click_token": click_token,
        "unsubscribe_token": unsub_token,
        "target_url": click_url,
        "contact_id": contact.id,
        "campaign_id": campaign.id,
    }


async def test_open_pixel_returns_png(async_client, seed_tracking_tokens: dict[str, object]):
    response = await async_client.get(f"/track/open?t={seed_tracking_tokens['open_token']}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 0


async def test_open_records_event(async_client, db_session, seed_tracking_tokens: dict[str, object]):
    response = await async_client.get(f"/track/open?t={seed_tracking_tokens['open_token']}")
    assert response.status_code == 200
    event = await db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.contact_id == seed_tracking_tokens["contact_id"],
            EmailEvent.campaign_id == seed_tracking_tokens["campaign_id"],
            EmailEvent.event_type == EventType.OPENED,
        )
    )
    assert event is not None


async def test_open_dedup(async_client, db_session, seed_tracking_tokens: dict[str, object]):
    await async_client.get(f"/track/open?t={seed_tracking_tokens['open_token']}")
    await async_client.get(f"/track/open?t={seed_tracking_tokens['open_token']}")
    rows = await db_session.execute(
        select(EmailEvent).where(
            EmailEvent.contact_id == seed_tracking_tokens["contact_id"],
            EmailEvent.campaign_id == seed_tracking_tokens["campaign_id"],
            EmailEvent.event_type == EventType.OPENED,
        )
    )
    assert len(rows.scalars().all()) == 1


async def test_open_invalid_token(async_client, db_session):
    before = await db_session.execute(
        select(EmailEvent).where(EmailEvent.event_type == EventType.OPENED)
    )
    before_count = len(before.scalars().all())
    response = await async_client.get("/track/open?t=invalid-token-xyz")
    assert response.status_code == 200
    after = await db_session.execute(
        select(EmailEvent).where(EmailEvent.event_type == EventType.OPENED)
    )
    assert len(after.scalars().all()) == before_count


async def test_click_redirects(async_client, seed_tracking_tokens: dict[str, object]):
    response = await async_client.get(
        f"/track/click?t={seed_tracking_tokens['click_token']}",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == seed_tracking_tokens["target_url"]


async def test_click_records_event(async_client, db_session, seed_tracking_tokens: dict[str, object]):
    await async_client.get(
        f"/track/click?t={seed_tracking_tokens['click_token']}",
        follow_redirects=False,
    )
    event = await db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.contact_id == seed_tracking_tokens["contact_id"],
            EmailEvent.campaign_id == seed_tracking_tokens["campaign_id"],
            EmailEvent.event_type == EventType.CLICKED,
        )
    )
    assert event is not None
    assert event.metadata_.get("url") == seed_tracking_tokens["target_url"]


async def test_click_multiple_times(async_client, db_session, seed_tracking_tokens: dict[str, object]):
    for _ in range(3):
        await async_client.get(
            f"/track/click?t={seed_tracking_tokens['click_token']}",
            follow_redirects=False,
        )
    rows = await db_session.execute(
        select(EmailEvent).where(
            EmailEvent.contact_id == seed_tracking_tokens["contact_id"],
            EmailEvent.campaign_id == seed_tracking_tokens["campaign_id"],
            EmailEvent.event_type == EventType.CLICKED,
        )
    )
    assert len(rows.scalars().all()) == 3


async def test_click_invalid_token(async_client, db_session):
    before = await db_session.execute(
        select(EmailEvent).where(EmailEvent.event_type == EventType.CLICKED)
    )
    before_count = len(before.scalars().all())
    response = await async_client.get("/track/click?t=invalid-token-xyz", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/"
    after = await db_session.execute(
        select(EmailEvent).where(EmailEvent.event_type == EventType.CLICKED)
    )
    assert len(after.scalars().all()) == before_count
