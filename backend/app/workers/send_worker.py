from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionLocal
from app.models.campaigns import Campaign, CampaignSend, Template
from app.models.contacts import Contact, SuppressionList
from app.models.enums import CampaignStatus, ContactStatus, EventType, SendStatus
from app.models.tracking import EmailEvent
from app.utils.ses import delete_sqs_message, receive_sqs_messages, send_email_via_ses
from app.utils.token import (
    create_tracking_tokens,
    extract_links_from_html,
    inject_tracking_into_html,
    inject_unsubscribe_link,
)

logger = logging.getLogger(__name__)
_running = True


async def process_send_message(message: dict[str, object], db: AsyncSession | None = None) -> bool:
    if db is not None:
        return await _process_send_message(message, db)

    async with SessionLocal() as session:
        return await _process_send_message(message, session)


async def _process_send_message(message: dict[str, object], db: AsyncSession) -> bool:
    body = message["body"]
    if not isinstance(body, dict):
        return True

    campaign_id = UUID(str(body["campaign_id"]))
    contact_id = UUID(str(body["contact_id"]))

    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        return True
    if campaign.status == CampaignStatus.PAUSED:
        return False

    contact = await db.get(Contact, contact_id)
    is_suppressed = False
    if contact:
        suppressed = await db.scalar(
            select(SuppressionList.id).where(
                SuppressionList.org_id == contact.org_id,
                SuppressionList.email == contact.email,
            )
        )
        is_suppressed = suppressed is not None

    if not contact or is_suppressed or contact.status in (
        ContactStatus.UNSUBSCRIBED,
        ContactStatus.BOUNCED,
        ContactStatus.COMPLAINED,
    ):
        send = await db.scalar(
            select(CampaignSend).where(
                CampaignSend.campaign_id == campaign_id,
                CampaignSend.contact_id == contact_id,
            )
        )
        if send:
            send.status = SendStatus.FAILED
            await db.commit()
        return True

    template = await db.get(Template, campaign.template_id)
    if not template:
        logger.error("Template missing campaign=%s", campaign_id)
        return True

    html = template.html
    html = html.replace("{{first_name}}", contact.first_name or "")
    html = html.replace("{{last_name}}", contact.last_name or "")
    html = html.replace("{{email}}", contact.email)

    links = extract_links_from_html(html)
    tokens = await create_tracking_tokens(contact_id, campaign_id, links, db)
    click_tokens = tokens["click_tokens"]
    if not isinstance(click_tokens, dict):
        click_tokens = {}
    html = inject_tracking_into_html(
        html,
        str(tokens["open_token"]),
        {str(k): str(v) for k, v in click_tokens.items()},
        settings.APP_BASE_URL,
    )
    html = inject_unsubscribe_link(
        html,
        str(tokens["unsub_token"]),
        settings.APP_BASE_URL,
    )

    try:
        msg_id = await send_email_via_ses(
            to_address=contact.email,
            from_address=campaign.from_email,
            from_name=campaign.from_name,
            reply_to=campaign.reply_to,
            subject=campaign.subject,
            html_body=html,
            configuration_set=settings.AWS_SES_CONFIG_SET,
        )
    except Exception as exc:
        logger.error("SES failed %s: %s", contact.email, exc)
        send = await db.scalar(
            select(CampaignSend).where(
                CampaignSend.campaign_id == campaign_id,
                CampaignSend.contact_id == contact_id,
            )
        )
        if send:
            send.status = SendStatus.FAILED
            await db.commit()
        return True

    send = await db.scalar(
        select(CampaignSend).where(
            CampaignSend.campaign_id == campaign_id,
            CampaignSend.contact_id == contact_id,
        )
    )
    if send:
        send.status = SendStatus.SENT
        send.ses_message_id = msg_id
        send.sent_at = datetime.now(timezone.utc)

    db.add(
        EmailEvent(
            contact_id=contact_id,
            campaign_id=campaign_id,
            event_type=EventType.SENT,
            metadata_={"ses_message_id": msg_id},
        )
    )
    await db.commit()

    total = await db.scalar(
        select(func.count(CampaignSend.id)).where(CampaignSend.campaign_id == campaign_id)
    )
    done = await db.scalar(
        select(func.count(CampaignSend.id)).where(
            CampaignSend.campaign_id == campaign_id,
            CampaignSend.status.in_([SendStatus.SENT, SendStatus.FAILED]),
        )
    )
    if total and done and total == done:
        campaign.status = CampaignStatus.SENT
        await db.commit()
        logger.info("Campaign %s complete", campaign_id)
    return True


async def worker_loop() -> None:
    semaphore = asyncio.Semaphore(settings.WORKER_CONCURRENCY)
    logger.info("Send worker started")
    while _running:
        try:
            messages = await receive_sqs_messages(settings.AWS_SQS_SEND_QUEUE_URL)
            tasks: list[asyncio.Task[None]] = []
            for message in messages:

                async def handle(m: dict[str, object] = message) -> None:
                    async with semaphore:
                        should_delete = await process_send_message(m)
                        if should_delete:
                            await delete_sqs_message(
                                settings.AWS_SQS_SEND_QUEUE_URL,
                                str(m["receipt_handle"]),
                            )
                        await asyncio.sleep(1.0 / settings.MAX_SES_SEND_RATE)

                tasks.append(asyncio.create_task(handle()))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as exc:
            logger.error("Worker error: %s", exc)
            await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(worker_loop())
