from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.models.campaign_recipients import CampaignRecipient
from app.models.campaigns import Campaign, CampaignSend, Template
from app.models.contacts import Contact, ContactList, ContactListMember
from app.models.core import Organisation, User
from app.models.enums import CampaignStatus, ContactSource, ContactStatus, EventType, SendStatus, UserRole
from app.models.tracking import EmailEvent
from app.utils.security import hash_password
from app.workers.scheduler import check_scheduled_campaigns
from app.workers.send_worker import process_send_message


@pytest.fixture()
async def seed_full_campaign(db_session) -> Campaign:
    org = Organisation(name="M5 Org")
    db_session.add(org)
    await db_session.flush()

    user = User(
        org_id=org.id,
        email=f"m5-admin-{uuid4().hex}@example.com",
        password_hash=hash_password("password123"),
        full_name="M5 Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    contact_list = ContactList(org_id=org.id, name="M5 List", tags=[])
    db_session.add(contact_list)
    await db_session.flush()

    contact = Contact(
        org_id=org.id,
        email="recipient@example.com",
        first_name="Recipient",
        last_name="User",
        status=ContactStatus.ACTIVE,
        custom_fields={},
        source=ContactSource.MANUAL,
    )
    db_session.add(contact)
    await db_session.flush()

    db_session.add(ContactListMember(contact_id=contact.id, list_id=contact_list.id))

    template = Template(
        org_id=org.id,
        name="M5 Template",
        category="General",
        blocks={"schemaVersion": 11, "body": {"rows": []}},
        html="<html><body>Hello {{first_name}} {{last_name}} {{email}} <a href='https://example.com'>Link</a> {{unsubscribe_url}}</body></html>",
        thumbnail_url=None,
    )
    db_session.add(template)
    await db_session.flush()

    campaign = Campaign(
        org_id=org.id,
        name="M5 Campaign",
        subject="M5 Subject",
        preview_text="Preview",
        from_name="Sender",
        from_email="sender@example.com",
        reply_to="reply@example.com",
        status=CampaignStatus.DRAFT,
        template_id=template.id,
        created_by=user.id,
    )
    db_session.add(campaign)
    await db_session.flush()

    db_session.add(
        CampaignRecipient(
            campaign_id=campaign.id,
            target_type="list",
            target_id=contact_list.id,
            is_exclusion=False,
        )
    )
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


@pytest.fixture()
async def sending_auth_headers(async_client, db_session, seed_full_campaign: Campaign) -> dict[str, str]:
    user = await db_session.get(User, seed_full_campaign.created_by)
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "password123"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@patch("app.utils.ses.sqs_client.send_message")
async def test_send_now_success(mock_send_message, async_client, sending_auth_headers, seed_full_campaign: Campaign):
    mock_send_message.return_value = {}
    response = await async_client.post(
        f"/api/v1/campaigns/{seed_full_campaign.id}/send",
        headers=sending_auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sending"
    assert body["queued"] > 0


async def test_send_no_template(async_client, sending_auth_headers, seed_full_campaign: Campaign, db_session):
    seed_full_campaign.template_id = None
    await db_session.commit()
    response = await async_client.post(
        f"/api/v1/campaigns/{seed_full_campaign.id}/send",
        headers=sending_auth_headers,
    )
    assert response.status_code == 422


async def test_send_no_recipients(async_client, sending_auth_headers, seed_full_campaign: Campaign, db_session):
    await db_session.execute(
        delete(CampaignRecipient).where(CampaignRecipient.campaign_id == seed_full_campaign.id)
    )
    await db_session.commit()
    response = await async_client.post(
        f"/api/v1/campaigns/{seed_full_campaign.id}/send",
        headers=sending_auth_headers,
    )
    assert response.status_code == 422


async def test_pause_campaign(async_client, sending_auth_headers, seed_full_campaign: Campaign, db_session):
    seed_full_campaign.status = CampaignStatus.SENDING
    await db_session.commit()
    response = await async_client.post(
        f"/api/v1/campaigns/{seed_full_campaign.id}/pause",
        headers=sending_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "paused"


@patch("app.utils.ses.sqs_client.send_message")
async def test_resume_campaign(mock_send_message, async_client, sending_auth_headers, seed_full_campaign: Campaign, db_session):
    mock_send_message.return_value = {}
    seed_full_campaign.status = CampaignStatus.PAUSED
    await db_session.flush()
    contact_id = await db_session.scalar(
        select(Contact.id).where(Contact.org_id == seed_full_campaign.org_id).limit(1)
    )
    db_session.add(
        CampaignSend(
            campaign_id=seed_full_campaign.id,
            contact_id=contact_id,
            status=SendStatus.QUEUED,
        )
    )
    await db_session.commit()
    response = await async_client.post(
        f"/api/v1/campaigns/{seed_full_campaign.id}/resume",
        headers=sending_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "sending"


async def test_get_progress(async_client, sending_auth_headers, seed_full_campaign: Campaign, db_session):
    contact = await db_session.scalar(select(Contact).where(Contact.org_id == seed_full_campaign.org_id).limit(1))
    db_session.add(
        CampaignSend(
            campaign_id=seed_full_campaign.id,
            contact_id=contact.id,
            status=SendStatus.SENT,
        )
    )
    await db_session.commit()
    response = await async_client.get(
        f"/api/v1/campaigns/{seed_full_campaign.id}/progress",
        headers=sending_auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "sent" in body
    assert "status" in body


@patch("app.utils.ses.ses_client.send_email")
async def test_test_send(mock_send_email, async_client, sending_auth_headers, seed_full_campaign: Campaign):
    mock_send_email.return_value = {"MessageId": "fake-id"}
    response = await async_client.post(
        f"/api/v1/campaigns/{seed_full_campaign.id}/test-send",
        json={"email_addresses": ["a@test.com", "b@test.com"]},
        headers=sending_auth_headers,
    )
    assert response.status_code == 200


@patch("app.workers.send_worker.send_email_via_ses")
async def test_process_send_message(mock_send_email, seed_full_campaign: Campaign, db_session):
    mock_send_email.return_value = "fake-msg-id"
    contact = await db_session.scalar(select(Contact).where(Contact.org_id == seed_full_campaign.org_id).limit(1))
    db_session.add(
        CampaignSend(
            campaign_id=seed_full_campaign.id,
            contact_id=contact.id,
            status=SendStatus.QUEUED,
        )
    )
    seed_full_campaign.status = CampaignStatus.SENDING
    await db_session.commit()

    should_delete = await process_send_message(
        {
            "receipt_handle": "receipt",
            "body": {
                "campaign_id": str(seed_full_campaign.id),
                "contact_id": str(contact.id),
                "org_id": str(seed_full_campaign.org_id),
            },
        },
        db_session,
    )
    assert should_delete is True

    refreshed_send = await db_session.scalar(
        select(CampaignSend).where(
            CampaignSend.campaign_id == seed_full_campaign.id,
            CampaignSend.contact_id == contact.id,
        )
    )
    assert refreshed_send is not None
    assert refreshed_send.status == SendStatus.SENT
    event = await db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.campaign_id == seed_full_campaign.id,
            EmailEvent.contact_id == contact.id,
            EmailEvent.event_type == EventType.SENT,
        )
    )
    assert event is not None


async def test_process_send_message_paused_keeps_queue(seed_full_campaign: Campaign, db_session):
    contact = await db_session.scalar(select(Contact).where(Contact.org_id == seed_full_campaign.org_id).limit(1))
    db_session.add(
        CampaignSend(
            campaign_id=seed_full_campaign.id,
            contact_id=contact.id,
            status=SendStatus.QUEUED,
        )
    )
    seed_full_campaign.status = CampaignStatus.PAUSED
    await db_session.commit()
    should_delete = await process_send_message(
        {
            "receipt_handle": "receipt",
            "body": {
                "campaign_id": str(seed_full_campaign.id),
                "contact_id": str(contact.id),
                "org_id": str(seed_full_campaign.org_id),
            },
        },
        db_session,
    )
    assert should_delete is False


@patch("app.workers.scheduler.enqueue_campaign")
async def test_scheduler_triggers_due(mock_enqueue_campaign, db_session, seed_full_campaign: Campaign):
    seed_full_campaign.status = CampaignStatus.SCHEDULED
    seed_full_campaign.scheduled_at = datetime.now(timezone.utc) - timedelta(seconds=60)
    await db_session.commit()
    await check_scheduled_campaigns(db_session)
    assert mock_enqueue_campaign.call_count >= 1
    assert any(call.args[1] == seed_full_campaign.id for call in mock_enqueue_campaign.call_args_list)
