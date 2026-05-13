from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaigns import CampaignSend
from app.models.contacts import Contact, SuppressionList
from app.models.enums import ContactStatus, EventType, SendStatus, SuppressionReason
from app.models.tracking import EmailEvent
from app.schemas.webhook import SESNotificationPayload
from app.utils.analytics_cache import invalidate_analytics_cache


async def suppress_contact(
    org_id,
    email,
    reason: SuppressionReason,
    db: AsyncSession,
) -> None:
    existing = await db.scalar(
        select(SuppressionList.id).where(
            SuppressionList.org_id == org_id,
            SuppressionList.email == email,
        )
    )
    if existing:
        return

    db.add(
        SuppressionList(
            org_id=org_id,
            email=email,
            reason=reason,
        )
    )

    contact = await db.scalar(
        select(Contact).where(
            Contact.org_id == org_id,
            Contact.email == email,
        )
    )
    if contact:
        if reason == SuppressionReason.BOUNCED:
            contact.status = ContactStatus.BOUNCED
        elif reason == SuppressionReason.COMPLAINED:
            contact.status = ContactStatus.COMPLAINED
    await db.commit()


async def record_bounce_event(campaign_id, contact_id, metadata: dict, db: AsyncSession) -> None:
    existing = await db.scalar(
        select(EmailEvent).where(
            EmailEvent.contact_id == contact_id,
            EmailEvent.campaign_id == campaign_id,
            EmailEvent.event_type == EventType.BOUNCED,
        )
    )

    send = await db.scalar(
        select(CampaignSend).where(
            CampaignSend.campaign_id == campaign_id,
            CampaignSend.contact_id == contact_id,
        )
    )
    if send:
        send.status = SendStatus.FAILED

    if existing:
        await db.commit()
        return

    db.add(
        EmailEvent(
            contact_id=contact_id,
            campaign_id=campaign_id,
            event_type=EventType.BOUNCED,
            metadata_=metadata,
        )
    )
    await db.commit()


async def record_complaint_event(campaign_id, contact_id, metadata: dict, db: AsyncSession) -> None:
    existing = await db.scalar(
        select(EmailEvent).where(
            EmailEvent.contact_id == contact_id,
            EmailEvent.campaign_id == campaign_id,
            EmailEvent.event_type == EventType.COMPLAINED,
        )
    )

    send = await db.scalar(
        select(CampaignSend).where(
            CampaignSend.campaign_id == campaign_id,
            CampaignSend.contact_id == contact_id,
        )
    )
    if send:
        send.status = SendStatus.FAILED

    if existing:
        await db.commit()
        return

    db.add(
        EmailEvent(
            contact_id=contact_id,
            campaign_id=campaign_id,
            event_type=EventType.COMPLAINED,
            metadata_=metadata,
        )
    )
    await db.commit()


async def process_bounce_notification(payload: SESNotificationPayload, db: AsyncSession) -> None:
    ses_message_id = payload.mail.messageId
    send = await db.scalar(select(CampaignSend).where(CampaignSend.ses_message_id == ses_message_id))
    if not send:
        return

    contact = await db.get(Contact, send.contact_id)
    if not contact or not payload.bounce:
        return

    diagnostic_code = None
    if payload.bounce.bouncedRecipients:
        diagnostic_code = payload.bounce.bouncedRecipients[0].diagnosticCode

    metadata = {
        "bounce_type": payload.bounce.bounceType,
        "bounce_subtype": payload.bounce.bounceSubType,
        "diagnostic": diagnostic_code,
        "ses_message_id": ses_message_id,
    }

    await record_bounce_event(send.campaign_id, send.contact_id, metadata, db)
    if payload.bounce.bounceType == "Permanent":
        await suppress_contact(contact.org_id, contact.email, SuppressionReason.BOUNCED, db)
    await invalidate_analytics_cache(contact.org_id, send.campaign_id)


async def process_complaint_notification(payload: SESNotificationPayload, db: AsyncSession) -> None:
    ses_message_id = payload.mail.messageId
    send = await db.scalar(select(CampaignSend).where(CampaignSend.ses_message_id == ses_message_id))
    if not send:
        return

    contact = await db.get(Contact, send.contact_id)
    if not contact or not payload.complaint:
        return

    metadata = {
        "feedback_type": payload.complaint.complaintFeedbackType,
        "ses_message_id": ses_message_id,
    }
    await record_complaint_event(send.campaign_id, send.contact_id, metadata, db)
    await suppress_contact(contact.org_id, contact.email, SuppressionReason.COMPLAINED, db)
    await invalidate_analytics_cache(contact.org_id, send.campaign_id)


async def process_delivery_notification(payload: SESNotificationPayload, db: AsyncSession) -> None:
    ses_message_id = payload.mail.messageId
    send = await db.scalar(select(CampaignSend).where(CampaignSend.ses_message_id == ses_message_id))
    if not send:
        return
    send.status = SendStatus.DELIVERED
    existing = await db.scalar(
        select(EmailEvent).where(
            EmailEvent.contact_id == send.contact_id,
            EmailEvent.campaign_id == send.campaign_id,
            EmailEvent.event_type == EventType.DELIVERED,
        )
    )
    if existing is None:
        db.add(
            EmailEvent(
                contact_id=send.contact_id,
                campaign_id=send.campaign_id,
                event_type=EventType.DELIVERED,
                metadata_={"ses_message_id": ses_message_id},
            )
        )
    await db.commit()
    campaign_org_id = await db.scalar(
        select(Contact.org_id).where(Contact.id == send.contact_id)
    )
    if campaign_org_id is not None:
        await invalidate_analytics_cache(campaign_org_id, send.campaign_id)


async def process_ses_notification(payload: SESNotificationPayload, db: AsyncSession) -> None:
    if payload.notificationType == "Bounce":
        await process_bounce_notification(payload, db)
    elif payload.notificationType == "Complaint":
        await process_complaint_notification(payload, db)
    elif payload.notificationType == "Delivery":
        await process_delivery_notification(payload, db)
