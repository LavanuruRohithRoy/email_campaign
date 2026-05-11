from __future__ import annotations

import json
import secrets
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.campaigns import Campaign, CampaignSend, Template
from app.models.contacts import Contact, SuppressionList
from app.models.core import Organisation, User
from app.models.enums import (
    CampaignStatus,
    ContactSource,
    ContactStatus,
    EventType,
    SendStatus,
    SuppressionReason,
    TokenType,
    UserRole,
)
from app.models.tracking import EmailEvent, TrackingToken
from app.utils.security import hash_password
from app.workers.send_worker import process_send_message


def _sns_envelope(message: dict[str, object], message_type: str = "Notification") -> dict[str, object]:
    return {
        "Type": message_type,
        "MessageId": str(uuid4()),
        "TopicArn": "arn:aws:sns:ap-south-1:123456789012:ses-events",
        "Message": json.dumps(message),
        "Timestamp": "2026-05-11T12:00:00Z",
    }


@pytest.fixture()
async def seed_bounce_data(db_session) -> dict[str, object]:
    org = Organisation(name=f"M7 Org {uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        org_id=org.id,
        email=f"m7-admin-{uuid4().hex}@example.com",
        password_hash=hash_password("password123"),
        full_name="M7 Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    contact = Contact(
        org_id=org.id,
        email=f"m7-contact-{uuid4().hex}@example.com",
        first_name="M7",
        last_name="Contact",
        status=ContactStatus.ACTIVE,
        custom_fields={},
        source=ContactSource.MANUAL,
    )
    db_session.add(contact)
    await db_session.flush()

    template = Template(
        org_id=org.id,
        name="M7 Template",
        category="General",
        blocks={"schemaVersion": 11, "body": {"rows": []}},
        html="<html><body>Hello {{first_name}}</body></html>",
        thumbnail_url=None,
    )
    db_session.add(template)
    await db_session.flush()

    campaign = Campaign(
        org_id=org.id,
        name="M7 Campaign",
        subject="M7 Subject",
        from_name="M7 Team",
        from_email="m7@example.com",
        status=CampaignStatus.SENT,
        template_id=template.id,
        created_by=user.id,
    )
    db_session.add(campaign)
    await db_session.flush()

    send = CampaignSend(
        campaign_id=campaign.id,
        contact_id=contact.id,
        ses_message_id=f"ses-{uuid4().hex}",
        status=SendStatus.SENT,
    )
    db_session.add(send)

    open_token = secrets.token_urlsafe(16)
    click_token = secrets.token_urlsafe(16)
    db_session.add(
        TrackingToken(
            token=open_token,
            contact_id=contact.id,
            campaign_id=campaign.id,
            token_type=TokenType.OPEN,
        )
    )
    db_session.add(
        TrackingToken(
            token=click_token,
            contact_id=contact.id,
            campaign_id=campaign.id,
            token_type=TokenType.CLICK,
            target_url="https://example.com/m7",
        )
    )
    await db_session.commit()

    return {
        "org": org,
        "contact": contact,
        "campaign": campaign,
        "send": send,
        "open_token": open_token,
        "click_token": click_token,
    }


async def test_permanent_bounce_suppresses_contact(async_client, db_session, seed_bounce_data: dict[str, object]):
    payload = {
        "notificationType": "Bounce",
        "mail": {
            "messageId": seed_bounce_data["send"].ses_message_id,
            "timestamp": "2026-05-11T12:00:00Z",
            "source": "sender@example.com",
            "destination": [seed_bounce_data["contact"].email],
        },
        "bounce": {
            "bounceType": "Permanent",
            "bounceSubType": "General",
            "bouncedRecipients": [
                {"emailAddress": seed_bounce_data["contact"].email, "diagnosticCode": "smtp; 550 user unknown"}
            ],
            "timestamp": "2026-05-11T12:00:00Z",
        },
    }
    response = await async_client.post("/webhooks/ses", json=_sns_envelope(payload))
    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    event = await db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.contact_id == seed_bounce_data["contact"].id,
            EmailEvent.campaign_id == seed_bounce_data["campaign"].id,
            EmailEvent.event_type == EventType.BOUNCED,
        )
    )
    assert event is not None

    refreshed_contact = await db_session.get(Contact, seed_bounce_data["contact"].id)
    assert refreshed_contact is not None
    await db_session.refresh(refreshed_contact)
    assert refreshed_contact.status == ContactStatus.BOUNCED

    suppression = await db_session.scalar(
        select(SuppressionList).where(
            SuppressionList.org_id == seed_bounce_data["org"].id,
            SuppressionList.email == seed_bounce_data["contact"].email,
        )
    )
    assert suppression is not None
    assert suppression.reason == SuppressionReason.BOUNCED

    refreshed_send = await db_session.get(CampaignSend, seed_bounce_data["send"].id)
    assert refreshed_send is not None
    await db_session.refresh(refreshed_send)
    assert refreshed_send.status == SendStatus.FAILED


async def test_transient_bounce_does_not_suppress(async_client, db_session, seed_bounce_data: dict[str, object]):
    payload = {
        "notificationType": "Bounce",
        "mail": {
            "messageId": seed_bounce_data["send"].ses_message_id,
            "timestamp": "2026-05-11T12:00:00Z",
            "source": "sender@example.com",
            "destination": [seed_bounce_data["contact"].email],
        },
        "bounce": {
            "bounceType": "Transient",
            "bounceSubType": "General",
            "bouncedRecipients": [{"emailAddress": seed_bounce_data["contact"].email}],
            "timestamp": "2026-05-11T12:00:00Z",
        },
    }
    response = await async_client.post("/webhooks/ses", json=_sns_envelope(payload))
    assert response.status_code == 200

    event = await db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.contact_id == seed_bounce_data["contact"].id,
            EmailEvent.event_type == EventType.BOUNCED,
        )
    )
    assert event is not None

    refreshed_contact = await db_session.get(Contact, seed_bounce_data["contact"].id)
    assert refreshed_contact is not None
    await db_session.refresh(refreshed_contact)
    assert refreshed_contact.status == ContactStatus.ACTIVE

    suppression = await db_session.scalar(
        select(SuppressionList).where(
            SuppressionList.org_id == seed_bounce_data["org"].id,
            SuppressionList.email == seed_bounce_data["contact"].email,
        )
    )
    assert suppression is None


async def test_complaint_suppresses_immediately(async_client, db_session, seed_bounce_data: dict[str, object]):
    payload = {
        "notificationType": "Complaint",
        "mail": {
            "messageId": seed_bounce_data["send"].ses_message_id,
            "timestamp": "2026-05-11T12:00:00Z",
            "source": "sender@example.com",
            "destination": [seed_bounce_data["contact"].email],
        },
        "complaint": {
            "complainedRecipients": [{"emailAddress": seed_bounce_data["contact"].email}],
            "timestamp": "2026-05-11T12:00:00Z",
            "complaintFeedbackType": "abuse",
        },
    }
    response = await async_client.post("/webhooks/ses", json=_sns_envelope(payload))
    assert response.status_code == 200

    refreshed_contact = await db_session.get(Contact, seed_bounce_data["contact"].id)
    assert refreshed_contact is not None
    await db_session.refresh(refreshed_contact)
    assert refreshed_contact.status == ContactStatus.COMPLAINED

    suppression = await db_session.scalar(
        select(SuppressionList).where(
            SuppressionList.org_id == seed_bounce_data["org"].id,
            SuppressionList.email == seed_bounce_data["contact"].email,
        )
    )
    assert suppression is not None
    assert suppression.reason == SuppressionReason.COMPLAINED

    complaint = await db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.contact_id == seed_bounce_data["contact"].id,
            EmailEvent.campaign_id == seed_bounce_data["campaign"].id,
            EmailEvent.event_type == EventType.COMPLAINED,
        )
    )
    assert complaint is not None


async def test_duplicate_sns_delivery_idempotent(async_client, db_session, seed_bounce_data: dict[str, object]):
    payload = {
        "notificationType": "Bounce",
        "mail": {
            "messageId": seed_bounce_data["send"].ses_message_id,
            "timestamp": "2026-05-11T12:00:00Z",
            "source": "sender@example.com",
            "destination": [seed_bounce_data["contact"].email],
        },
        "bounce": {
            "bounceType": "Permanent",
            "bounceSubType": "General",
            "bouncedRecipients": [{"emailAddress": seed_bounce_data["contact"].email}],
            "timestamp": "2026-05-11T12:00:00Z",
        },
    }
    envelope = _sns_envelope(payload)
    first = await async_client.post("/webhooks/ses", json=envelope)
    second = await async_client.post("/webhooks/ses", json=envelope)
    assert first.status_code == 200
    assert second.status_code == 200

    events = await db_session.execute(
        select(EmailEvent).where(
            EmailEvent.contact_id == seed_bounce_data["contact"].id,
            EmailEvent.campaign_id == seed_bounce_data["campaign"].id,
            EmailEvent.event_type == EventType.BOUNCED,
        )
    )
    assert len(events.scalars().all()) == 1

    suppressions = await db_session.execute(
        select(SuppressionList).where(
            SuppressionList.org_id == seed_bounce_data["org"].id,
            SuppressionList.email == seed_bounce_data["contact"].email,
        )
    )
    assert len(suppressions.scalars().all()) == 1


async def test_invalid_ses_message_id_handled_safely(async_client):
    payload = {
        "notificationType": "Bounce",
        "mail": {
            "messageId": "does-not-exist",
            "timestamp": "2026-05-11T12:00:00Z",
            "source": "sender@example.com",
            "destination": ["nobody@example.com"],
        },
        "bounce": {
            "bounceType": "Permanent",
            "bounceSubType": "General",
            "bouncedRecipients": [{"emailAddress": "nobody@example.com"}],
            "timestamp": "2026-05-11T12:00:00Z",
        },
    }
    response = await async_client.post("/webhooks/ses", json=_sns_envelope(payload))
    assert response.status_code == 200
    assert response.json()["status"] == "processed"


@patch("httpx.AsyncClient.get")
async def test_subscription_confirmation_handled(mock_get, async_client):
    mock_get.return_value = None
    envelope = {
        "Type": "SubscriptionConfirmation",
        "MessageId": str(uuid4()),
        "TopicArn": "arn:aws:sns:ap-south-1:123456789012:ses-events",
        "Message": "subscribe",
        "Timestamp": "2026-05-11T12:00:00Z",
        "SubscribeURL": "https://sns.ap-south-1.amazonaws.com/confirm",
    }
    response = await async_client.post("/webhooks/ses", json=envelope)
    assert response.status_code == 200
    assert response.json()["status"] == "subscription_confirmed"
    mock_get.assert_called_once_with("https://sns.ap-south-1.amazonaws.com/confirm")


@patch("app.workers.send_worker.send_email_via_ses")
async def test_worker_skips_suppressed_contacts(mock_send_email, db_session, seed_bounce_data: dict[str, object]):
    db_session.add(
        SuppressionList(
            org_id=seed_bounce_data["org"].id,
            email=seed_bounce_data["contact"].email,
            reason=SuppressionReason.BOUNCED,
        )
    )
    queued = await db_session.get(CampaignSend, seed_bounce_data["send"].id)
    assert queued is not None
    queued.status = SendStatus.QUEUED
    queued.ses_message_id = None
    campaign = await db_session.get(Campaign, seed_bounce_data["campaign"].id)
    campaign.status = CampaignStatus.SENDING
    await db_session.commit()

    should_delete = await process_send_message(
        {
            "receipt_handle": "receipt",
            "body": {
                "campaign_id": str(seed_bounce_data["campaign"].id),
                "contact_id": str(seed_bounce_data["contact"].id),
                "org_id": str(seed_bounce_data["org"].id),
            },
        },
        db_session,
    )
    assert should_delete is True
    mock_send_email.assert_not_called()

    refreshed = await db_session.get(CampaignSend, queued.id)
    assert refreshed is not None
    assert refreshed.status == SendStatus.FAILED


async def test_public_tracking_routes_unaffected(async_client, seed_bounce_data: dict[str, object]):
    open_response = await async_client.get(f"/track/open?t={seed_bounce_data['open_token']}")
    click_response = await async_client.get(
        f"/track/click?t={seed_bounce_data['click_token']}",
        follow_redirects=False,
    )
    assert open_response.status_code == 200
    assert click_response.status_code == 302
