from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.campaigns import Campaign
from app.models.contacts import Contact, ContactList, ContactListMember, Segment, SuppressionList
from app.models.core import Organisation, User
from app.models.enums import ContactSource, EventType, SuppressionReason, UserRole
from app.models.tracking import EmailEvent
from app.utils.security import hash_password


@pytest.fixture()
async def seed_org(db_session, seed_user) -> Organisation:
    result = await db_session.execute(select(Organisation).where(Organisation.id == seed_user.org_id))
    organisation = result.scalar_one()
    return organisation


@pytest.fixture()
async def seed_list(db_session, seed_org: Organisation) -> ContactList:
    contact_list = ContactList(org_id=seed_org.id, name="Main List", description="Primary list")
    db_session.add(contact_list)
    await db_session.commit()
    await db_session.refresh(contact_list)
    return contact_list


@pytest.fixture()
async def manager_auth_headers(async_client, seed_user) -> dict[str, str]:
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": seed_user.email, "password": "password123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_contact(db_session, org_id, email: str, *, first_name: str | None = None, last_name: str | None = None) -> Contact:
    contact = Contact(
        org_id=org_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone="1234567890",
        source=ContactSource.MANUAL,
        custom_fields={"city": "Bangalore"},
    )
    db_session.add(contact)
    await db_session.commit()
    await db_session.refresh(contact)
    return contact


async def _create_campaign(db_session, org_id, created_by: User, name: str) -> Campaign:
    campaign = Campaign(
        org_id=org_id,
        name=name,
        subject="Welcome",
        from_name="Team",
        from_email="team@example.com",
        created_by=created_by.id,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


async def test_create_list(async_client, seed_user, seed_org, manager_auth_headers):
    response = await async_client.post("/api/v1/lists", json={"name": "Customers"}, headers=manager_auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "Customers"
    assert body["contact_count"] == 0


async def test_get_lists(async_client, seed_user, seed_org, db_session, manager_auth_headers):
    list_one = ContactList(org_id=seed_org.id, name="List One")
    list_two = ContactList(org_id=seed_org.id, name="List Two")
    db_session.add_all([list_one, list_two])
    await db_session.commit()

    response = await async_client.get("/api/v1/lists", headers=manager_auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2


async def test_create_contact_manual(async_client, seed_user, seed_org, manager_auth_headers):
    response = await async_client.post(
        "/api/v1/contacts",
        json={"email": "john@example.com", "first_name": "John", "phone": "9876543210"},
        headers=manager_auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "john@example.com"
    assert body["status"] == "active"


async def test_duplicate_contact(async_client, seed_user, seed_org, manager_auth_headers):
    first = await async_client.post(
        "/api/v1/contacts",
        json={"email": "duplicate@example.com", "first_name": "Dup"},
        headers=manager_auth_headers,
    )
    assert first.status_code == 201

    second = await async_client.post(
        "/api/v1/contacts",
        json={"email": "duplicate@example.com", "first_name": "Dup 2"},
        headers=manager_auth_headers,
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "DUPLICATE_EMAIL"


async def test_suppressed_contact(async_client, seed_user, seed_org, db_session, manager_auth_headers):
    suppressed = SuppressionList(
        org_id=seed_org.id,
        email="blocked@example.com",
        reason=SuppressionReason.MANUAL,
        added_by=seed_user.id,
    )
    db_session.add(suppressed)
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/contacts",
        json={"email": "blocked@example.com", "first_name": "Blocked"},
        headers=manager_auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "EMAIL_SUPPRESSED"


async def test_get_contact_detail(async_client, seed_user, seed_org, seed_list, db_session, manager_auth_headers):
    contact = await _create_contact(db_session, seed_org.id, "detail@example.com", first_name="Detail")
    db_session.add(ContactListMember(contact_id=contact.id, list_id=seed_list.id))
    campaign = await _create_campaign(db_session, seed_org.id, seed_user, "Welcome Campaign")
    db_session.add(
        EmailEvent(
            contact_id=contact.id,
            campaign_id=campaign.id,
            event_type=EventType.OPENED,
            ip_address="127.0.0.1",
            user_agent="pytest",
            metadata_={"source": "test"},
        )
    )
    await db_session.commit()

    response = await async_client.get(f"/api/v1/contacts/{contact.id}", headers=manager_auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "detail@example.com"
    assert body["list_memberships"]
    assert body["event_history"]
    assert "password_hash" not in body


async def test_csv_preview(async_client, seed_user, seed_org, seed_list, manager_auth_headers):
    csv_bytes = b"email,first_name,last_name\nalpha@example.com,Alpha,One\nbeta@example.com,Beta,Two\n"
    response = await async_client.post(
        f"/api/v1/lists/{seed_list.id}/import/preview",
        files={"file": ("contacts.csv", csv_bytes, "text/csv")},
        headers=manager_auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["headers"] == ["email", "first_name", "last_name"]
    assert len(body["preview_rows"]) == 2
    assert body["total_rows"] == 2


async def test_import_job_starts(async_client, seed_user, seed_org, seed_list, manager_auth_headers):
    csv_bytes = b"email,first_name,last_name\nalpha@example.com,Alpha,One\n"
    response = await async_client.post(
        f"/api/v1/lists/{seed_list.id}/import",
        data={"column_mapping": json.dumps({"email": "email", "first_name": "first_name", "last_name": "last_name"})},
        files={"file": ("contacts.csv", csv_bytes, "text/csv")},
        headers=manager_auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["status"] in {"pending", "processing"}


async def test_segment_create(async_client, seed_user, seed_org, manager_auth_headers):
    response = await async_client.post(
        "/api/v1/segments",
        json={
            "name": "Active contacts",
            "rules": {
                "operator": "AND",
                "conditions": [{"field": "status", "operator": "equals", "value": "active"}],
            },
        },
        headers=manager_auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Active contacts"


async def test_segment_count(async_client, seed_user, seed_org, db_session, manager_auth_headers):
    await _create_contact(db_session, seed_org.id, "segment1@example.com")
    await _create_contact(db_session, seed_org.id, "segment2@example.com")

    segment = Segment(
        org_id=seed_org.id,
        name="Active segment",
        rules={
            "operator": "AND",
            "conditions": [{"field": "status", "operator": "equals", "value": "active"}],
        },
    )
    db_session.add(segment)
    await db_session.commit()
    await db_session.refresh(segment)

    response = await async_client.get(f"/api/v1/segments/{segment.id}/count", headers=manager_auth_headers)
    assert response.status_code == 200
    assert response.json()["count"] >= 0


async def test_viewer_cannot_create_list(async_client, seed_user, seed_org, db_session):
    viewer_email = f"viewer-{uuid4().hex}@example.com"
    viewer = User(
        org_id=seed_org.id,
        email=viewer_email,
        password_hash=hash_password("password123"),
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(viewer)
    await db_session.commit()

    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": viewer_email, "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = await async_client.post(
        "/api/v1/lists",
        json={"name": "Should fail"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403