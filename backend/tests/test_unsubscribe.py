from __future__ import annotations

import secrets
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.campaign_recipients import CampaignRecipient
from app.models.campaigns import Campaign
from app.models.contacts import Contact, ContactList, ContactListMember
from app.models.core import Organisation, User
from app.models.enums import CampaignStatus, ContactSource, ContactStatus, EventType, TokenType, UserRole
from app.models.tracking import EmailEvent, TrackingToken
from app.services.campaign_service import resolve_recipients
from app.utils.security import hash_password


@pytest.fixture()
async def unsubscribe_seed(db_session) -> dict[str, object]:
    org = Organisation(name=f"Unsub Org {uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        org_id=org.id,
        email=f"unsub-admin-{uuid4().hex}@example.com",
        password_hash=hash_password("password123"),
        full_name="Unsub Admin",
        role=UserRole.CAMPAIGN_MANAGER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    campaign = Campaign(
        org_id=org.id,
        name="Unsubscribe Campaign",
        subject="Update",
        from_name="Campaign Team",
        from_email="campaign@example.com",
        status=CampaignStatus.SENT,
        created_by=user.id,
    )
    db_session.add(campaign)
    await db_session.flush()

    contacts: dict[str, Contact] = {}
    tokens: dict[str, str] = {}
    for label, status in {
        "active": ContactStatus.ACTIVE,
        "unsubscribed": ContactStatus.UNSUBSCRIBED,
        "bounced": ContactStatus.BOUNCED,
        "complained": ContactStatus.COMPLAINED,
    }.items():
        contact = Contact(
            org_id=org.id,
            email=f"{label}-{uuid4().hex}@example.com",
            first_name=label,
            status=status,
            custom_fields={},
            source=ContactSource.MANUAL,
        )
        db_session.add(contact)
        await db_session.flush()
        token = secrets.token_urlsafe(16)
        db_session.add(
            TrackingToken(
                token=token,
                contact_id=contact.id,
                campaign_id=campaign.id,
                token_type=TokenType.UNSUBSCRIBE,
            )
        )
        contacts[label] = contact
        tokens[label] = token

    db_session.add(
        TrackingToken(
            token=f"wrong-type-{uuid4().hex}",
            contact_id=contacts["active"].id,
            campaign_id=campaign.id,
            token_type=TokenType.OPEN,
        )
    )
    await db_session.commit()

    return {
        "org_id": org.id,
        "campaign_id": campaign.id,
        "contacts": contacts,
        "tokens": tokens,
    }


async def test_valid_unsubscribe(async_client, db_session, unsubscribe_seed):
    token = unsubscribe_seed["tokens"]["active"]
    contact_id = unsubscribe_seed["contacts"]["active"].id

    response = await async_client.get(f"/unsubscribe?t={token}")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    contact = await db_session.get(Contact, contact_id)
    assert contact is not None
    await db_session.refresh(contact)
    assert contact.status == ContactStatus.UNSUBSCRIBED
    event = await db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.contact_id == contact_id,
            EmailEvent.event_type == EventType.UNSUBSCRIBED,
        )
    )
    assert event is not None
    assert event.metadata_ == {"source": "unsubscribe_link"}


async def test_repeated_unsubscribe_idempotency(async_client, db_session, unsubscribe_seed):
    token = unsubscribe_seed["tokens"]["active"]
    contact_id = unsubscribe_seed["contacts"]["active"].id

    first = await async_client.get(f"/unsubscribe?t={token}")
    second = await async_client.get(f"/unsubscribe?t={token}")

    assert first.status_code == 200
    assert second.status_code == 200
    rows = await db_session.execute(
        select(EmailEvent).where(
            EmailEvent.contact_id == contact_id,
            EmailEvent.event_type == EventType.UNSUBSCRIBED,
        )
    )
    assert len(rows.scalars().all()) == 1


async def test_invalid_token_404(async_client):
    response = await async_client.get("/unsubscribe?t=invalid-token")
    assert response.status_code == 404


async def test_preferences_fetch(async_client, unsubscribe_seed):
    token = unsubscribe_seed["tokens"]["active"]
    contact = unsubscribe_seed["contacts"]["active"]

    response = await async_client.get(f"/preferences?t={token}")

    assert response.status_code == 200
    body = response.json()
    assert body["contact_id"] == str(contact.id)
    assert body["email"] == contact.email
    assert body["unsubscribed"] is False


async def test_reactivate_unsubscribed_contact(async_client, db_session, unsubscribe_seed):
    token = unsubscribe_seed["tokens"]["unsubscribed"]
    contact_id = unsubscribe_seed["contacts"]["unsubscribed"].id

    response = await async_client.post(f"/preferences?t={token}", json={"unsubscribed": False})

    assert response.status_code == 200
    assert response.json()["status"] == ContactStatus.ACTIVE.value
    contact = await db_session.get(Contact, contact_id)
    assert contact is not None
    await db_session.refresh(contact)
    assert contact.status == ContactStatus.ACTIVE


async def test_bounced_cannot_reactivate(async_client, db_session, unsubscribe_seed):
    token = unsubscribe_seed["tokens"]["bounced"]
    contact_id = unsubscribe_seed["contacts"]["bounced"].id

    response = await async_client.post(f"/preferences?t={token}", json={"unsubscribed": False})

    assert response.status_code == 200
    contact = await db_session.get(Contact, contact_id)
    assert contact is not None
    await db_session.refresh(contact)
    assert contact.status == ContactStatus.BOUNCED


async def test_complained_cannot_reactivate(async_client, db_session, unsubscribe_seed):
    token = unsubscribe_seed["tokens"]["complained"]
    contact_id = unsubscribe_seed["contacts"]["complained"].id

    response = await async_client.post(f"/preferences?t={token}", json={"unsubscribed": False})

    assert response.status_code == 200
    contact = await db_session.get(Contact, contact_id)
    assert contact is not None
    await db_session.refresh(contact)
    assert contact.status == ContactStatus.COMPLAINED


async def test_public_routes_require_no_jwt(async_client, unsubscribe_seed):
    token = unsubscribe_seed["tokens"]["active"]

    unsubscribe_response = await async_client.get(f"/unsubscribe?t={token}")
    preferences_response = await async_client.get(f"/preferences?t={token}")

    assert unsubscribe_response.status_code == 200
    assert preferences_response.status_code == 200


async def test_campaign_resolution_excludes_unsubscribed_contacts(db_session, unsubscribe_seed):
    org_id = unsubscribe_seed["org_id"]
    campaign_id = unsubscribe_seed["campaign_id"]
    contacts = unsubscribe_seed["contacts"]

    contact_list = ContactList(org_id=org_id, name="All contacts", tags=[])
    db_session.add(contact_list)
    await db_session.flush()
    db_session.add(CampaignRecipient(campaign_id=campaign_id, target_type="list", target_id=contact_list.id, is_exclusion=False))
    for contact in contacts.values():
        db_session.add(ContactListMember(contact_id=contact.id, list_id=contact_list.id))
    await db_session.commit()

    resolved = await resolve_recipients(org_id, campaign_id, db_session)

    assert contacts["active"].id in resolved
    assert contacts["unsubscribed"].id not in resolved
    assert contacts["bounced"].id not in resolved
    assert contacts["complained"].id not in resolved
