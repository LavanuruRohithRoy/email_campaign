from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign_recipients import CampaignRecipient
from app.models.campaigns import Campaign, CampaignSend, Template
from app.models.contacts import Contact, ContactList, ContactListMember, SuppressionList
from app.models.enums import CampaignStatus, ContactStatus
from app.schemas.campaign import CampaignCreate, CampaignRecipientsInput, CampaignScheduleInput, CampaignUpdate
from app.services.segment_service import evaluate_segment_contacts


def _recipient_rows(campaign_id: UUID, target_ids: Iterable[UUID], target_type: str, is_exclusion: bool) -> list[CampaignRecipient]:
    return [
        CampaignRecipient(
            campaign_id=campaign_id,
            target_type=target_type,
            target_id=target_id,
            is_exclusion=is_exclusion,
        )
        for target_id in target_ids
    ]


async def _get_campaign(org_id: UUID, campaign_id: UUID, db: AsyncSession) -> Campaign:
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.org_id == org_id))
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise ValueError("NOT_FOUND")
    return campaign


async def _validate_template(org_id: UUID, template_id: UUID | None, db: AsyncSession) -> None:
    if template_id is None:
        return
    result = await db.execute(select(Template.id).where(Template.id == template_id, Template.org_id == org_id))
    if result.scalar_one_or_none() is None:
        raise ValueError("NOT_FOUND")


async def create_campaign(org_id: UUID, created_by: UUID, data: CampaignCreate, db: AsyncSession) -> Campaign:
    await _validate_template(org_id, data.template_id, db)
    campaign = Campaign(
        org_id=org_id,
        name=data.name,
        subject=data.subject,
        preview_text=data.preview_text,
        from_name=data.from_name,
        from_email=str(data.from_email),
        reply_to=str(data.reply_to) if data.reply_to is not None else None,
        status=CampaignStatus.DRAFT,
        template_id=data.template_id,
        created_by=created_by,
    )
    db.add(campaign)
    await db.flush()
    recipient_rows = [
        *_recipient_rows(campaign.id, data.target_list_ids, "list", False),
        *_recipient_rows(campaign.id, data.target_segment_ids, "segment", False),
        *_recipient_rows(campaign.id, data.exclude_list_ids, "list", True),
    ]
    if recipient_rows:
        db.add_all(recipient_rows)
    await db.commit()
    await db.refresh(campaign)
    return campaign


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


async def get_campaigns(
    org_id: UUID,
    status: CampaignStatus | None,
    start_date: datetime | None,
    end_date: datetime | None,
    limit: int,
    offset: int,
    db: AsyncSession,
) -> tuple[list[Campaign], int]:
    query = select(Campaign).where(Campaign.org_id == org_id)
    count_query = select(func.count(Campaign.id)).where(Campaign.org_id == org_id)
    if status is not None:
        query = query.where(Campaign.status == status)
        count_query = count_query.where(Campaign.status == status)
    normalized_start = _as_aware(start_date)
    normalized_end = _as_aware(end_date)
    if normalized_start is not None:
        query = query.where(Campaign.created_at >= normalized_start)
        count_query = count_query.where(Campaign.created_at >= normalized_start)
    if normalized_end is not None:
        query = query.where(Campaign.created_at <= normalized_end)
        count_query = count_query.where(Campaign.created_at <= normalized_end)
    query = query.order_by(Campaign.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    total = int((await db.execute(count_query)).scalar_one())
    return list(result.scalars().all()), total


async def get_campaign(org_id: UUID, campaign_id: UUID, db: AsyncSession) -> Campaign:
    return await _get_campaign(org_id, campaign_id, db)


async def update_campaign(org_id: UUID, campaign_id: UUID, data: CampaignUpdate, db: AsyncSession) -> Campaign:
    campaign = await _get_campaign(org_id, campaign_id, db)
    if campaign.status != CampaignStatus.DRAFT:
        raise ValueError("NOT_DRAFT")
    await _validate_template(org_id, data.template_id, db)
    if data.name is not None:
        campaign.name = data.name
    if data.subject is not None:
        campaign.subject = data.subject
    if data.preview_text is not None:
        campaign.preview_text = data.preview_text
    if data.from_name is not None:
        campaign.from_name = data.from_name
    if data.from_email is not None:
        campaign.from_email = str(data.from_email)
    if data.reply_to is not None:
        campaign.reply_to = str(data.reply_to)
    if data.template_id is not None:
        campaign.template_id = data.template_id
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def delete_campaign(org_id: UUID, campaign_id: UUID, db: AsyncSession) -> None:
    campaign = await _get_campaign(org_id, campaign_id, db)
    if campaign.status != CampaignStatus.DRAFT:
        raise ValueError("NOT_DRAFT")
    await db.execute(delete(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id))
    await db.execute(delete(CampaignSend).where(CampaignSend.campaign_id == campaign.id))
    await db.delete(campaign)
    await db.commit()


async def duplicate_campaign(org_id: UUID, campaign_id: UUID, created_by: UUID, db: AsyncSession) -> Campaign:
    original = await _get_campaign(org_id, campaign_id, db)
    duplicate = Campaign(
        org_id=org_id,
        name=f"{original.name} (Copy)",
        subject=original.subject,
        preview_text=original.preview_text,
        from_name=original.from_name,
        from_email=original.from_email,
        reply_to=original.reply_to,
        status=CampaignStatus.DRAFT,
        template_id=original.template_id,
        scheduled_at=None,
        timezone=None,
        created_by=created_by,
    )
    db.add(duplicate)
    await db.flush()
    recipient_rows = await db.execute(
        select(CampaignRecipient.target_type, CampaignRecipient.target_id, CampaignRecipient.is_exclusion).where(
            CampaignRecipient.campaign_id == original.id
        )
    )
    db.add_all(
        [
            CampaignRecipient(
                campaign_id=duplicate.id,
                target_type=target_type,
                target_id=target_id,
                is_exclusion=is_exclusion,
            )
            for target_type, target_id, is_exclusion in recipient_rows.all()
        ]
    )
    await db.commit()
    await db.refresh(duplicate)
    return duplicate


async def set_recipients(org_id: UUID, campaign_id: UUID, data: CampaignRecipientsInput, db: AsyncSession) -> None:
    campaign = await _get_campaign(org_id, campaign_id, db)
    if campaign.status != CampaignStatus.DRAFT:
        raise ValueError("NOT_DRAFT")
    await db.execute(delete(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id))
    recipient_rows = [
        *_recipient_rows(campaign.id, data.target_list_ids, "list", False),
        *_recipient_rows(campaign.id, data.target_segment_ids, "segment", False),
        *_recipient_rows(campaign.id, data.exclude_list_ids, "list", True),
    ]
    if recipient_rows:
        db.add_all(recipient_rows)
    await db.commit()


async def _resolve_list_contacts(org_id: UUID, list_id: UUID, db: AsyncSession) -> set[UUID]:
    result = await db.execute(
        select(Contact.id)
        .join(ContactListMember, ContactListMember.contact_id == Contact.id)
        .join(ContactList, ContactList.id == ContactListMember.list_id)
        .where(Contact.org_id == org_id, ContactList.org_id == org_id, ContactListMember.list_id == list_id)
    )
    return {contact_id for contact_id in result.scalars().all()}


async def _resolve_segment_contacts(org_id: UUID, segment_id: UUID, db: AsyncSession) -> set[UUID]:
    return set(await evaluate_segment_contacts(org_id, segment_id, db))


async def resolve_recipients(org_id: UUID, campaign_id: UUID, db: AsyncSession) -> list[UUID]:
    campaign_result = await db.execute(
        select(CampaignRecipient.target_type, CampaignRecipient.target_id, CampaignRecipient.is_exclusion).where(
            CampaignRecipient.campaign_id == campaign_id
        )
    )
    recipient_rows = campaign_result.all()
    if not recipient_rows:
        return []

    included: set[UUID] = set()
    excluded: set[UUID] = set()
    for target_type, target_id, is_exclusion in recipient_rows:
        if target_type == "list":
            resolved = await _resolve_list_contacts(org_id, target_id, db)
        else:
            resolved = await _resolve_segment_contacts(org_id, target_id, db)
        if is_exclusion:
            excluded.update(resolved)
        else:
            included.update(resolved)

    candidate_ids = included - excluded
    if not candidate_ids:
        return []

    contact_rows = await db.execute(
        select(Contact.id, Contact.email, Contact.status)
        .where(Contact.org_id == org_id, Contact.id.in_(candidate_ids))
        .order_by(Contact.created_at.asc())
    )
    contacts = contact_rows.all()
    suppressed_rows = await db.execute(
        select(SuppressionList.email).where(SuppressionList.org_id == org_id, SuppressionList.email.in_({email for _, email, _ in contacts}))
    )
    suppressed = set(suppressed_rows.scalars().all())
    allowed = [
        contact_id
        for contact_id, email, status in contacts
        if status not in {ContactStatus.UNSUBSCRIBED, ContactStatus.BOUNCED, ContactStatus.COMPLAINED} and email not in suppressed
    ]
    return allowed


async def estimate_recipient_count(org_id: UUID, campaign_id: UUID, db: AsyncSession) -> int:
    return len(await resolve_recipients(org_id, campaign_id, db))


async def schedule_campaign(org_id: UUID, campaign_id: UUID, data: CampaignScheduleInput, db: AsyncSession) -> Campaign:
    campaign = await _get_campaign(org_id, campaign_id, db)
    if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED}:
        raise ValueError("NOT_DRAFT")
    if campaign.template_id is None:
        raise ValueError("NO_TEMPLATE")
    recipient_count = await db.execute(
        select(func.count(CampaignRecipient.id)).where(
            CampaignRecipient.campaign_id == campaign.id,
            CampaignRecipient.is_exclusion.is_(False),
        )
    )
    if int(recipient_count.scalar_one()) == 0:
        raise ValueError("NO_RECIPIENTS")
    campaign.status = CampaignStatus.SCHEDULED
    campaign.scheduled_at = data.scheduled_at
    campaign.timezone = data.timezone
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def cancel_schedule(org_id: UUID, campaign_id: UUID, db: AsyncSession) -> Campaign:
    campaign = await _get_campaign(org_id, campaign_id, db)
    if campaign.status != CampaignStatus.SCHEDULED:
        raise ValueError("NOT_SCHEDULED")
    campaign.status = CampaignStatus.DRAFT
    campaign.scheduled_at = None
    campaign.timezone = None
    await db.commit()
    await db.refresh(campaign)
    return campaign