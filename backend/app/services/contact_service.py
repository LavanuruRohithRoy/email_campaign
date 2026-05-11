from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaigns import Campaign
from app.models.contacts import Contact, ContactList, ContactListMember, Segment, SuppressionList
from app.models.core import RefreshToken
from app.models.tracking import EmailEvent
from app.schemas.contact import ContactCreate, ContactListCreate, ContactListUpdate, ContactUpdate, SegmentCreate, SegmentUpdate
from app.models.enums import ContactStatus, ContactSource


async def get_lists(org_id: UUID, db: AsyncSession) -> list[dict[str, object]]:
    counts_subquery = (
        select(
            ContactListMember.list_id.label("list_id"),
            func.count(ContactListMember.contact_id).label("contact_count"),
        )
        .group_by(ContactListMember.list_id)
        .subquery()
    )

    result = await db.execute(
        select(ContactList, func.coalesce(counts_subquery.c.contact_count, 0))
        .outerjoin(counts_subquery, counts_subquery.c.list_id == ContactList.id)
        .where(ContactList.org_id == org_id)
        .order_by(ContactList.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": contact_list.id,
            "org_id": contact_list.org_id,
            "name": contact_list.name,
            "description": contact_list.description,
            "tags": list(contact_list.tags or []),
            "contact_count": int(contact_count or 0),
            "created_at": contact_list.created_at,
        }
        for contact_list, contact_count in rows
    ]


async def get_list(org_id: UUID, list_id: UUID, db: AsyncSession) -> dict[str, object]:
    lists = await get_lists(org_id, db)
    for contact_list in lists:
        if contact_list["id"] == list_id:
            return contact_list
    raise ValueError("NOT_FOUND")


async def create_list(org_id: UUID, data: ContactListCreate, db: AsyncSession) -> ContactList:
    contact_list = ContactList(
        org_id=org_id,
        name=data.name,
        description=data.description,
        tags=list(data.tags),
    )
    db.add(contact_list)
    await db.commit()
    await db.refresh(contact_list)
    return contact_list


async def _get_list(org_id: UUID, list_id: UUID, db: AsyncSession) -> ContactList:
    result = await db.execute(
        select(ContactList).where(ContactList.id == list_id, ContactList.org_id == org_id)
    )
    contact_list = result.scalar_one_or_none()
    if contact_list is None:
        raise ValueError("NOT_FOUND")
    return contact_list


async def update_list(org_id: UUID, list_id: UUID, data: ContactListUpdate, db: AsyncSession) -> ContactList:
    contact_list = await _get_list(org_id, list_id, db)
    if data.name is not None:
        contact_list.name = data.name
    if data.description is not None:
        contact_list.description = data.description
    if data.tags is not None:
        contact_list.tags = list(data.tags)
    await db.commit()
    await db.refresh(contact_list)
    return contact_list


async def delete_list(org_id: UUID, list_id: UUID, db: AsyncSession) -> None:
    contact_list = await _get_list(org_id, list_id, db)
    await db.execute(delete(ContactListMember).where(ContactListMember.list_id == contact_list.id))
    await db.delete(contact_list)
    await db.commit()


def _apply_contact_search(query, search: str | None) -> object:
    if search is None or not search.strip():
        return query
    term = f"%{search.strip()}%"
    return query.where(
        or_(
            Contact.email.ilike(term),
            Contact.first_name.ilike(term),
            Contact.last_name.ilike(term),
        )
    )


def _apply_contact_status(query, status: ContactStatus | None) -> object:
    if status is None:
        return query
    return query.where(Contact.status == status)


async def get_contacts(
    org_id: UUID,
    list_id: UUID | None,
    search: str | None,
    status: ContactStatus | None,
    limit: int,
    offset: int,
    db: AsyncSession,
    sort_by: str = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> tuple[list[Contact], int]:
    base_query = select(Contact).where(Contact.org_id == org_id)
    count_query = select(func.count(func.distinct(Contact.id))).where(Contact.org_id == org_id)

    if list_id is not None:
        base_query = base_query.join(ContactListMember, ContactListMember.contact_id == Contact.id)
        count_query = count_query.join(ContactListMember, ContactListMember.contact_id == Contact.id)
        base_query = base_query.where(ContactListMember.list_id == list_id)
        count_query = count_query.where(ContactListMember.list_id == list_id)

    base_query = _apply_contact_search(base_query, search)
    count_query = _apply_contact_search(count_query, search)
    base_query = _apply_contact_status(base_query, status)
    count_query = _apply_contact_status(count_query, status)

    sort_columns = {
        "email": Contact.email,
        "first_name": Contact.first_name,
        "last_name": Contact.last_name,
        "status": Contact.status,
        "created_at": Contact.created_at,
    }
    sort_column = sort_columns.get(sort_by, Contact.created_at)
    sort_expression = sort_column.asc() if sort_order == "asc" else sort_column.desc()

    result = await db.execute(
        base_query.order_by(sort_expression).limit(limit).offset(offset)
    )
    contacts = list(result.scalars().all())
    total = int((await db.execute(count_query)).scalar_one())
    return contacts, total


async def get_contact(org_id: UUID, contact_id: UUID, db: AsyncSession) -> Contact:
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.org_id == org_id)
    )
    contact = result.scalar_one_or_none()
    if contact is None:
        raise ValueError("NOT_FOUND")
    return contact


async def is_suppressed(org_id: UUID, email: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(SuppressionList.id).where(
            SuppressionList.org_id == org_id,
            func.lower(SuppressionList.email) == email.lower(),
        )
    )
    return result.scalar_one_or_none() is not None


async def create_contact(org_id: UUID, data: ContactCreate, db: AsyncSession) -> Contact:
    if await is_suppressed(org_id, data.email, db):
        raise ValueError("EMAIL_SUPPRESSED")

    duplicate_result = await db.execute(
        select(Contact.id).where(
            Contact.org_id == org_id,
            func.lower(Contact.email) == data.email.lower(),
        )
    )
    if duplicate_result.scalar_one_or_none() is not None:
        raise ValueError("DUPLICATE_EMAIL")

    contact = Contact(
        org_id=org_id,
        email=str(data.email),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        status=ContactStatus.ACTIVE,
        custom_fields=dict(data.custom_fields),
        source=data.source if data.source is not None else ContactSource.MANUAL,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def update_contact(org_id: UUID, contact_id: UUID, data: ContactUpdate, db: AsyncSession) -> Contact:
    contact = await get_contact(org_id, contact_id, db)
    if data.first_name is not None:
        contact.first_name = data.first_name
    if data.last_name is not None:
        contact.last_name = data.last_name
    if data.phone is not None:
        contact.phone = data.phone
    if data.custom_fields is not None:
        contact.custom_fields = dict(data.custom_fields)
    await db.commit()
    await db.refresh(contact)
    return contact


async def delete_contact(org_id: UUID, contact_id: UUID, db: AsyncSession) -> None:
    contact = await get_contact(org_id, contact_id, db)
    await db.execute(delete(ContactListMember).where(ContactListMember.contact_id == contact.id))
    await db.delete(contact)
    await db.commit()


async def add_to_list(org_id: UUID, contact_id: UUID, list_id: UUID, db: AsyncSession) -> None:
    await get_contact(org_id, contact_id, db)
    await _get_list(org_id, list_id, db)
    stmt = pg_insert(ContactListMember).values(contact_id=contact_id, list_id=list_id)
    stmt = stmt.on_conflict_do_nothing(index_elements=["contact_id", "list_id"])
    await db.execute(stmt)
    await db.commit()


async def remove_from_list(org_id: UUID, contact_id: UUID, list_id: UUID, db: AsyncSession) -> None:
    await get_contact(org_id, contact_id, db)
    await _get_list(org_id, list_id, db)
    await db.execute(
        delete(ContactListMember).where(
            ContactListMember.contact_id == contact_id,
            ContactListMember.list_id == list_id,
        )
    )
    await db.commit()


async def get_contact_event_history(org_id: UUID, contact_id: UUID, db: AsyncSession) -> list[EmailEvent]:
    await get_contact(org_id, contact_id, db)
    result = await db.execute(
        select(EmailEvent)
        .where(EmailEvent.contact_id == contact_id)
        .order_by(EmailEvent.occurred_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())
