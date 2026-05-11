from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contacts import Contact
from app.models.tracking import EmailEvent, TrackingToken
from app.models.enums import (
    TokenType,
    ContactStatus,
    EventType,
)


async def resolve_unsubscribe_token(
    token: str,
    db: AsyncSession,
) -> TrackingToken | None:
    result = await db.execute(
        select(TrackingToken).where(
            TrackingToken.token == token,
            TrackingToken.token_type == TokenType.UNSUBSCRIBE,
        )
    )
    return result.scalar_one_or_none()


async def unsubscribe_contact(
    token: str,
    db: AsyncSession,
) -> bool:
    tracking = await resolve_unsubscribe_token(token, db)
    if tracking is None:
        return False

    contact = await db.get(Contact, tracking.contact_id)
    if contact is None:
        return False

    if contact.status == ContactStatus.UNSUBSCRIBED:
        return True

    contact.status = ContactStatus.UNSUBSCRIBED
    existing_event = await db.execute(
        select(EmailEvent).where(
            EmailEvent.contact_id == tracking.contact_id,
            EmailEvent.campaign_id == tracking.campaign_id,
            EmailEvent.event_type == EventType.UNSUBSCRIBED,
        )
    )
    if existing_event.scalar_one_or_none() is None:
        db.add(
            EmailEvent(
                contact_id=tracking.contact_id,
                campaign_id=tracking.campaign_id,
                event_type=EventType.UNSUBSCRIBED,
                occurred_at=datetime.now(timezone.utc),
                metadata_={"source": "unsubscribe_link"},
            )
        )
    await db.commit()
    return True


async def get_preferences(
    token: str,
    db: AsyncSession,
) -> Contact | None:
    tracking = await resolve_unsubscribe_token(token, db)
    if tracking is None:
        return None
    return await db.get(Contact, tracking.contact_id)


async def update_preferences(
    token: str,
    unsubscribed: bool,
    db: AsyncSession,
) -> Contact | None:
    tracking = await resolve_unsubscribe_token(token, db)
    if tracking is None:
        return None

    contact = await db.get(Contact, tracking.contact_id)
    if contact is None:
        return None

    if unsubscribed:
        contact.status = ContactStatus.UNSUBSCRIBED
    elif contact.status == ContactStatus.UNSUBSCRIBED:
        contact.status = ContactStatus.ACTIVE

    await db.commit()
    await db.refresh(contact)
    return contact
