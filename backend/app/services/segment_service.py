from __future__ import annotations

from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contacts import Contact, Segment
from app.schemas.contact import SegmentCreate, SegmentRuleCondition, SegmentRules, SegmentUpdate


async def get_segments(org_id: UUID, db: AsyncSession) -> list[Segment]:
    result = await db.execute(
        select(Segment).where(Segment.org_id == org_id).order_by(Segment.created_at.desc())
    )
    return list(result.scalars().all())


async def create_segment(org_id: UUID, data: SegmentCreate, db: AsyncSession) -> Segment:
    segment = Segment(org_id=org_id, name=data.name, rules=data.rules.model_dump())
    db.add(segment)
    await db.commit()
    await db.refresh(segment)
    return segment


async def _get_segment(org_id: UUID, segment_id: UUID, db: AsyncSession) -> Segment:
    result = await db.execute(
        select(Segment).where(Segment.id == segment_id, Segment.org_id == org_id)
    )
    segment = result.scalar_one_or_none()
    if segment is None:
        raise ValueError("NOT_FOUND")
    return segment


async def update_segment(org_id: UUID, segment_id: UUID, data: SegmentUpdate, db: AsyncSession) -> Segment:
    segment = await _get_segment(org_id, segment_id, db)
    if data.name is not None:
        segment.name = data.name
    if data.rules is not None:
        segment.rules = data.rules.model_dump()
    await db.commit()
    await db.refresh(segment)
    return segment


async def delete_segment(org_id: UUID, segment_id: UUID, db: AsyncSession) -> None:
    segment = await _get_segment(org_id, segment_id, db)
    await db.delete(segment)
    await db.commit()


def _segment_condition(condition: SegmentRuleCondition):
    field = condition.field
    operator = condition.operator.lower()
    value = condition.value

    if field == "status":
        column = Contact.status
    elif field == "email":
        column = Contact.email
    elif field == "first_name":
        column = Contact.first_name
    elif field == "last_name":
        column = Contact.last_name
    elif field.startswith("custom_fields."):
        key = field.split(".", 1)[1]
        column = Contact.custom_fields[key].astext
    else:
        raise ValueError("INVALID_SEGMENT_RULES")

    if operator == "equals":
        return column == value
    if operator == "not_equals":
        return column != value
    if operator == "contains":
        return column.ilike(f"%{value}%")
    if operator == "gt":
        return column > value
    if operator == "lt":
        return column < value
    raise ValueError("INVALID_SEGMENT_RULES")


async def count_segment(org_id: UUID, segment_id: UUID, db: AsyncSession, redis: Redis) -> int:
    cache_key = f"segment_count:{segment_id}"
    cached = await redis.get(cache_key)
    if cached is not None:
        return int(cached)

    segment = await _get_segment(org_id, segment_id, db)
    rules = segment.rules or {}
    operator = str(rules.get("operator", "AND")).upper()
    conditions_data = rules.get("conditions", [])
    conditions = [_segment_condition(SegmentRuleCondition.model_validate(condition)) for condition in conditions_data]

    query = select(func.count(Contact.id)).where(Contact.org_id == org_id)
    if conditions:
        if operator == "OR":
            query = query.where(or_(*conditions))
        else:
            query = query.where(and_(*conditions))

    count = int((await db.execute(query)).scalar_one())
    await redis.set(cache_key, str(count), ex=300)
    return count


async def evaluate_segment_contacts(org_id: UUID, segment_id: UUID, db: AsyncSession) -> list[UUID]:
    segment = await _get_segment(org_id, segment_id, db)
    rules = segment.rules or {}
    operator = str(rules.get("operator", "AND")).upper()
    conditions_data = rules.get("conditions", [])
    conditions = [_segment_condition(SegmentRuleCondition.model_validate(condition)) for condition in conditions_data]

    query = select(Contact.id).where(Contact.org_id == org_id)
    if conditions:
        if operator == "OR":
            query = query.where(or_(*conditions))
        else:
            query = query.where(and_(*conditions))
    result = await db.execute(query)
    return list(result.scalars().all())
