from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.campaigns import Campaign, Template
from app.models.contacts import Contact, ContactList, ContactListMember, Segment, SuppressionList
from app.models.core import User
from app.models.enums import ContactSource, ContactStatus, CampaignStatus, SuppressionReason, UserRole
from app.utils.security import hash_password


@pytest.fixture()
async def seed_campaign_manager(seed_user: User) -> User:
    return seed_user


@pytest.fixture()
async def manager_auth_headers(async_client, seed_campaign_manager: User) -> dict[str, str]:
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": seed_campaign_manager.email, "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture()
async def viewer_user(db_session, seed_campaign_manager: User) -> User:
    viewer = User(
        org_id=seed_campaign_manager.org_id,
        email=f"viewer-{uuid4().hex}@example.com",
        password_hash=hash_password("password123"),
        full_name="Viewer User",
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(viewer)
    await db_session.commit()
    await db_session.refresh(viewer)
    return viewer


@pytest.fixture()
async def viewer_auth_headers(async_client, viewer_user: User) -> dict[str, str]:
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": viewer_user.email, "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture()
async def seed_template(db_session, seed_campaign_manager: User) -> Template:
    template = Template(
        org_id=seed_campaign_manager.org_id,
        name="Campaign Template",
        category="Newsletter",
        blocks={"schemaVersion": 11, "body": {"rows": []}},
        html="<div style='font-family: Arial;'>Hello {{first_name}}</div>",
        thumbnail_url=None,
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest.fixture()
async def seed_targets(db_session, seed_campaign_manager: User) -> dict[str, object]:
    target_list = ContactList(org_id=seed_campaign_manager.org_id, name="Target List", tags=[])
    exclusion_list = ContactList(org_id=seed_campaign_manager.org_id, name="Exclusion List", tags=[])
    db_session.add_all([target_list, exclusion_list])
    await db_session.flush()

    alice = Contact(
        org_id=seed_campaign_manager.org_id,
        email="alice@example.com",
        first_name="Alice",
        last_name="Target",
        status=ContactStatus.ACTIVE,
        custom_fields={},
        source=ContactSource.MANUAL,
    )
    bob = Contact(
        org_id=seed_campaign_manager.org_id,
        email="bob@example.com",
        first_name="Bob",
        last_name="Excluded",
        status=ContactStatus.ACTIVE,
        custom_fields={},
        source=ContactSource.MANUAL,
    )
    carol = Contact(
        org_id=seed_campaign_manager.org_id,
        email="carol@example.com",
        first_name="Carol",
        last_name="Unsubscribed",
        status=ContactStatus.UNSUBSCRIBED,
        custom_fields={},
        source=ContactSource.MANUAL,
    )
    dave = Contact(
        org_id=seed_campaign_manager.org_id,
        email="dave@example.com",
        first_name="Dave",
        last_name="Suppressed",
        status=ContactStatus.ACTIVE,
        custom_fields={},
        source=ContactSource.MANUAL,
    )
    db_session.add_all([alice, bob, carol, dave])
    await db_session.flush()

    db_session.add_all(
        [
            ContactListMember(contact_id=alice.id, list_id=target_list.id),
            ContactListMember(contact_id=bob.id, list_id=target_list.id),
            ContactListMember(contact_id=carol.id, list_id=target_list.id),
            ContactListMember(contact_id=dave.id, list_id=target_list.id),
            ContactListMember(contact_id=bob.id, list_id=exclusion_list.id),
        ]
    )
    db_session.add(
        SuppressionList(
            org_id=seed_campaign_manager.org_id,
            email=dave.email,
            reason=SuppressionReason.BOUNCED,
        )
    )
    segment = Segment(
        org_id=seed_campaign_manager.org_id,
        name="Alice Segment",
        rules={
            "operator": "AND",
            "conditions": [
                {"field": "first_name", "operator": "equals", "value": "Alice"},
            ],
        },
    )
    db_session.add(segment)
    await db_session.commit()
    await db_session.refresh(target_list)
    await db_session.refresh(exclusion_list)
    await db_session.refresh(segment)
    return {
        "target_list_id": target_list.id,
        "exclusion_list_id": exclusion_list.id,
        "segment_id": segment.id,
        "expected_count": 1,
    }


@pytest.fixture()
async def seed_campaign(db_session, seed_campaign_manager: User, seed_template: Template) -> Campaign:
    campaign = Campaign(
        org_id=seed_campaign_manager.org_id,
        name="Spring Launch",
        subject="Spring Launch Subject",
        preview_text="Preview text",
        from_name="Marketing Team",
        from_email="marketing@example.com",
        reply_to="reply@example.com",
        template_id=seed_template.id,
        created_by=seed_campaign_manager.id,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


async def test_create_campaign(async_client, manager_auth_headers, seed_targets, seed_template):
    response = await async_client.post(
        "/api/v1/campaigns",
        json={
            "name": "New Campaign",
            "subject": "Hello from us",
            "preview_text": "Preview here",
            "from_name": "Marketing Team",
            "from_email": "marketing@example.com",
            "reply_to": "reply@example.com",
            "template_id": str(seed_template.id),
            "target_list_ids": [str(seed_targets["target_list_id"])],
            "target_segment_ids": [str(seed_targets["segment_id"])],
            "exclude_list_ids": [str(seed_targets["exclusion_list_id"])],
        },
        headers=manager_auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["recipient_count"] == 1


async def test_get_campaigns(async_client, manager_auth_headers, seed_campaign: Campaign, seed_campaign_manager: User, seed_template: Template, db_session):
    second_campaign = Campaign(
        org_id=seed_campaign_manager.org_id,
        name="Second Campaign",
        subject="Second Subject",
        from_name="Marketing Team",
        from_email="marketing@example.com",
        template_id=seed_template.id,
        created_by=seed_campaign_manager.id,
    )
    db_session.add(second_campaign)
    await db_session.commit()

    response = await async_client.get("/api/v1/campaigns", headers=manager_auth_headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 2


async def test_get_campaign_by_id(async_client, manager_auth_headers, seed_campaign: Campaign):
    response = await async_client.get(f"/api/v1/campaigns/{seed_campaign.id}", headers=manager_auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(seed_campaign.id)
    assert "recipient_count" in body


async def test_update_draft_campaign(async_client, manager_auth_headers, seed_campaign: Campaign):
    response = await async_client.put(
        f"/api/v1/campaigns/{seed_campaign.id}",
        json={"subject": "Updated Subject"},
        headers=manager_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["subject"] == "Updated Subject"


async def test_update_non_draft_fails(async_client, manager_auth_headers, seed_campaign: Campaign, db_session):
    seed_campaign.status = CampaignStatus.SENT
    await db_session.commit()

    response = await async_client.put(
        f"/api/v1/campaigns/{seed_campaign.id}",
        json={"subject": "Blocked"},
        headers=manager_auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "NOT_DRAFT"


async def test_delete_draft_campaign(async_client, manager_auth_headers, seed_campaign: Campaign):
    response = await async_client.delete(f"/api/v1/campaigns/{seed_campaign.id}", headers=manager_auth_headers)
    assert response.status_code == 204


async def test_delete_non_draft_fails(async_client, manager_auth_headers, seed_campaign: Campaign, db_session):
    seed_campaign.status = CampaignStatus.SENT
    await db_session.commit()

    response = await async_client.delete(f"/api/v1/campaigns/{seed_campaign.id}", headers=manager_auth_headers)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "NOT_DRAFT"


async def test_duplicate_campaign(async_client, manager_auth_headers, seed_campaign: Campaign):
    response = await async_client.post(f"/api/v1/campaigns/{seed_campaign.id}/duplicate", headers=manager_auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] != str(seed_campaign.id)
    assert "(Copy)" in body["name"]
    assert body["status"] == "draft"


async def test_set_recipients(async_client, manager_auth_headers, seed_campaign: Campaign, seed_targets):
    response = await async_client.put(
        f"/api/v1/campaigns/{seed_campaign.id}/recipients",
        json={
            "target_list_ids": [str(seed_targets["target_list_id"])],
            "target_segment_ids": [str(seed_targets["segment_id"])],
            "exclude_list_ids": [str(seed_targets["exclusion_list_id"])],
        },
        headers=manager_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["updated"] is True


async def test_recipient_count(async_client, manager_auth_headers, seed_campaign: Campaign, seed_targets):
    await async_client.put(
        f"/api/v1/campaigns/{seed_campaign.id}/recipients",
        json={
            "target_list_ids": [str(seed_targets["target_list_id"])],
            "target_segment_ids": [str(seed_targets["segment_id"])],
            "exclude_list_ids": [str(seed_targets["exclusion_list_id"])],
        },
        headers=manager_auth_headers,
    )
    response = await async_client.get(f"/api/v1/campaigns/{seed_campaign.id}/recipient-count", headers=manager_auth_headers)
    assert response.status_code == 200
    assert response.json()["estimated_count"] == 1


async def test_schedule_campaign(async_client, manager_auth_headers, seed_campaign: Campaign, seed_targets):
    await async_client.put(
        f"/api/v1/campaigns/{seed_campaign.id}/recipients",
        json={
            "target_list_ids": [str(seed_targets["target_list_id"])],
            "target_segment_ids": [str(seed_targets["segment_id"])],
            "exclude_list_ids": [str(seed_targets["exclusion_list_id"])],
        },
        headers=manager_auth_headers,
    )
    response = await async_client.post(
        f"/api/v1/campaigns/{seed_campaign.id}/schedule",
        json={
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "timezone": "Asia/Kolkata",
        },
        headers=manager_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "scheduled"


async def test_schedule_past_datetime(async_client, manager_auth_headers, seed_campaign: Campaign):
    response = await async_client.post(
        f"/api/v1/campaigns/{seed_campaign.id}/schedule",
        json={
            "scheduled_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "timezone": "Asia/Kolkata",
        },
        headers=manager_auth_headers,
    )
    assert response.status_code == 422


async def test_cancel_schedule(async_client, manager_auth_headers, seed_campaign: Campaign, seed_targets):
    await async_client.put(
        f"/api/v1/campaigns/{seed_campaign.id}/recipients",
        json={
            "target_list_ids": [str(seed_targets["target_list_id"])],
            "target_segment_ids": [str(seed_targets["segment_id"])],
            "exclude_list_ids": [str(seed_targets["exclusion_list_id"])],
        },
        headers=manager_auth_headers,
    )
    await async_client.post(
        f"/api/v1/campaigns/{seed_campaign.id}/schedule",
        json={
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "timezone": "Asia/Kolkata",
        },
        headers=manager_auth_headers,
    )
    response = await async_client.post(f"/api/v1/campaigns/{seed_campaign.id}/cancel-schedule", headers=manager_auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "draft"


async def test_test_send(async_client, manager_auth_headers, seed_campaign: Campaign):
    response = await async_client.post(
        f"/api/v1/campaigns/{seed_campaign.id}/test-send",
        json={"email_addresses": ["one@example.com", "two@example.com", "three@example.com"]},
        headers=manager_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert len(response.json()["addresses"]) == 3


async def test_test_send_too_many(async_client, manager_auth_headers, seed_campaign: Campaign):
    response = await async_client.post(
        f"/api/v1/campaigns/{seed_campaign.id}/test-send",
        json={"email_addresses": [
            "one@example.com",
            "two@example.com",
            "three@example.com",
            "four@example.com",
            "five@example.com",
            "six@example.com",
        ]},
        headers=manager_auth_headers,
    )
    assert response.status_code == 422


async def test_viewer_cannot_create(async_client, viewer_auth_headers):
    response = await async_client.post(
        "/api/v1/campaigns",
        json={
            "name": "Blocked",
            "subject": "Blocked",
            "from_name": "Team",
            "from_email": "team@example.com",
        },
        headers=viewer_auth_headers,
    )
    assert response.status_code == 403