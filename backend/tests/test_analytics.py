from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import patch

import pytest

from app.models.campaigns import Campaign
from app.models.contacts import Contact
from app.models.core import User
from app.models.enums import CampaignStatus, ContactSource, ContactStatus, EventType, UserRole
from app.models.tracking import EmailEvent
from app.services.analytics_service import get_campaign_analytics
from app.utils.security import hash_password


@pytest.fixture()
async def analytics_seed(db_session, seed_user: User) -> dict[str, object]:
    contacts = [
        Contact(
            org_id=seed_user.org_id,
            email=f"analytics-{index}-{uuid4().hex}@example.com",
            first_name=f"Contact {index}",
            status=ContactStatus.ACTIVE if index < 3 else ContactStatus.UNSUBSCRIBED,
            custom_fields={},
            source=ContactSource.MANUAL,
        )
        for index in range(4)
    ]
    db_session.add_all(contacts)
    await db_session.flush()

    campaign_a = Campaign(
        org_id=seed_user.org_id,
        name="Baseline Campaign",
        subject="Baseline",
        from_name="Analytics Team",
        from_email="analytics@example.com",
        status=CampaignStatus.SENT,
        created_by=seed_user.id,
    )
    campaign_b = Campaign(
        org_id=seed_user.org_id,
        name="High Open Campaign",
        subject="Winner",
        from_name="Analytics Team",
        from_email="analytics@example.com",
        status=CampaignStatus.SENT,
        created_by=seed_user.id,
    )
    empty_campaign = Campaign(
        org_id=seed_user.org_id,
        name="Empty Campaign",
        subject="Empty",
        from_name="Analytics Team",
        from_email="analytics@example.com",
        status=CampaignStatus.DRAFT,
        created_by=seed_user.id,
    )
    db_session.add_all([campaign_a, campaign_b, empty_campaign])
    await db_session.flush()

    now = datetime.now(timezone.utc)
    events = [
        (contacts[0], campaign_a, EventType.SENT, now - timedelta(days=2)),
        (contacts[0], campaign_a, EventType.DELIVERED, now - timedelta(days=2)),
        (contacts[0], campaign_a, EventType.OPENED, now - timedelta(days=1)),
        (contacts[0], campaign_a, EventType.CLICKED, now - timedelta(days=1)),
        (contacts[1], campaign_a, EventType.SENT, now - timedelta(days=2)),
        (contacts[1], campaign_a, EventType.DELIVERED, now - timedelta(days=2)),
        (contacts[1], campaign_a, EventType.OPENED, now),
        (contacts[2], campaign_a, EventType.SENT, now - timedelta(days=2)),
        (contacts[2], campaign_a, EventType.DELIVERED, now - timedelta(days=2)),
        (contacts[2], campaign_a, EventType.UNSUBSCRIBED, now),
        (contacts[3], campaign_a, EventType.SENT, now - timedelta(days=2)),
        (contacts[3], campaign_a, EventType.BOUNCED, now - timedelta(days=1)),
        (contacts[3], campaign_a, EventType.COMPLAINED, now - timedelta(days=1)),
        (contacts[0], campaign_b, EventType.SENT, now - timedelta(days=1)),
        (contacts[0], campaign_b, EventType.DELIVERED, now - timedelta(days=1)),
        (contacts[0], campaign_b, EventType.OPENED, now - timedelta(days=1)),
    ]
    db_session.add_all(
        [
            EmailEvent(
                contact_id=contact.id,
                campaign_id=campaign.id,
                event_type=event_type,
                occurred_at=occurred_at,
                metadata_={},
            )
            for contact, campaign, event_type, occurred_at in events
        ]
    )
    await db_session.commit()
    await db_session.refresh(campaign_a)
    await db_session.refresh(campaign_b)
    await db_session.refresh(empty_campaign)

    return {
        "user": seed_user,
        "contacts": contacts,
        "campaign_a": campaign_a,
        "campaign_b": campaign_b,
        "empty_campaign": empty_campaign,
    }


@pytest.fixture()
async def analytics_auth_headers(async_client, analytics_seed) -> dict[str, str]:
    user = analytics_seed["user"]
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "password123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_campaign_analytics_aggregation(async_client, analytics_auth_headers, analytics_seed):
    campaign = analytics_seed["campaign_a"]

    response = await async_client.get(f"/api/v1/analytics/campaigns/{campaign.id}", headers=analytics_auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["sent"] == 4
    assert body["delivered"] == 3
    assert body["opened"] == 2
    assert body["clicked"] == 1
    assert body["bounced"] == 1
    assert body["complained"] == 1
    assert body["unsubscribed"] == 1
    assert body["open_rate"] == 0.6667
    assert body["click_rate"] == 0.3333
    assert body["bounce_rate"] == 0.25
    assert body["complaint_rate"] == 0.25
    assert body["unsubscribe_rate"] == 0.3333


async def test_dashboard_analytics(async_client, analytics_auth_headers, analytics_seed):
    response = await async_client.get("/api/v1/analytics/dashboard", headers=analytics_auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_contacts"] == 4
    assert body["active_contacts"] == 3
    assert body["total_campaigns"] == 3
    assert body["total_sent"] == 5
    assert body["total_opens"] == 3
    assert body["total_clicks"] == 1
    assert body["avg_open_rate"] == 0.75
    assert body["avg_click_rate"] == 0.25


async def test_top_campaigns_ordering(async_client, analytics_auth_headers, analytics_seed):
    response = await async_client.get("/api/v1/analytics/campaigns/top", headers=analytics_auth_headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["campaign_id"] == str(analytics_seed["campaign_b"].id)
    assert items[1]["campaign_id"] == str(analytics_seed["campaign_a"].id)
    assert all(item["sent"] > 0 for item in items)


async def test_open_timeseries_generation(async_client, analytics_auth_headers):
    response = await async_client.get("/api/v1/analytics/timeseries/opens?days=7", headers=analytics_auth_headers)

    assert response.status_code == 200
    assert sum(point["value"] for point in response.json()) == 3


async def test_click_timeseries_generation(async_client, analytics_auth_headers):
    response = await async_client.get("/api/v1/analytics/timeseries/clicks?days=7", headers=analytics_auth_headers)

    assert response.status_code == 200
    assert sum(point["value"] for point in response.json()) == 1


async def test_analytics_caching(db_session, redis_client, analytics_seed):
    campaign = analytics_seed["campaign_a"]
    user = analytics_seed["user"]

    first = await get_campaign_analytics(user.org_id, campaign.id, db_session, redis_client)
    db_session.add(
        EmailEvent(
            contact_id=analytics_seed["contacts"][0].id,
            campaign_id=campaign.id,
            event_type=EventType.OPENED,
            metadata_={},
        )
    )
    await db_session.commit()
    second = await get_campaign_analytics(user.org_id, campaign.id, db_session, redis_client)

    assert first.opened == 2
    assert second.opened == 2
    assert await redis_client.ttl(f"campaign_analytics:{campaign.id}") > 0


@patch("app.services.analytics_service.upload_report_csv_to_s3")
async def test_csv_export_generation(mock_upload, async_client, analytics_auth_headers, analytics_seed):
    mock_upload.return_value = "https://example.com/report.csv"
    campaign = analytics_seed["campaign_a"]

    response = await async_client.post(f"/api/v1/analytics/campaigns/{campaign.id}/export", headers=analytics_auth_headers)

    assert response.status_code == 200
    assert response.json()["download_url"] == "https://example.com/report.csv"
    uploaded_bytes = mock_upload.call_args.args[0]
    csv_text = uploaded_bytes.decode("utf-8")
    assert "email,sent,delivered,opened,clicked,bounced,complained,unsubscribed" in csv_text


async def test_rbac_protection(async_client, db_session, analytics_seed):
    viewer = User(
        org_id=analytics_seed["user"].org_id,
        email=f"analytics-viewer-{uuid4().hex}@example.com",
        password_hash=hash_password("password123"),
        full_name="Analytics Viewer",
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(viewer)
    await db_session.commit()
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": viewer.email, "password": "password123"},
    )

    response = await async_client.get(
        "/api/v1/analytics/dashboard",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 200


async def test_divide_by_zero_safety(async_client, analytics_auth_headers, analytics_seed):
    campaign = analytics_seed["empty_campaign"]

    response = await async_client.get(f"/api/v1/analytics/campaigns/{campaign.id}", headers=analytics_auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["sent"] == 0
    assert body["open_rate"] == 0.0
    assert body["click_rate"] == 0.0
    assert body["bounce_rate"] == 0.0
    assert body["complaint_rate"] == 0.0
    assert body["unsubscribe_rate"] == 0.0


async def test_analytics_routes_authenticated(async_client, analytics_seed):
    campaign = analytics_seed["campaign_a"]

    dashboard = await async_client.get("/api/v1/analytics/dashboard")
    campaign_report = await async_client.get(f"/api/v1/analytics/campaigns/{campaign.id}")

    assert dashboard.status_code == 401
    assert campaign_report.status_code == 401
