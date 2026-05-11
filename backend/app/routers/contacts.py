from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models.campaigns import Campaign
from app.models.contacts import ContactList, ContactListMember
from app.models.core import User
from app.models.enums import ContactStatus
from app.models.tracking import EmailEvent
from app.routers.common import value_error_to_http_exception
from app.schemas.contact import (
    ContactCreate,
    ContactDetailResponse,
    ContactListDetail,
    ContactResponse,
    ContactUpdate,
)
from app.services import contact_service

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "contacts"}


@router.get("", response_model=ContactListDetail)
async def list_contacts(
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(default=None),
    status_filter: ContactStatus | None = Query(default=None, alias="status"),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ContactListDetail:
    contacts, total = await contact_service.get_contacts(
        current_user.org_id,
        None,
        search,
        status_filter,
        limit,
        offset,
        db,
        sort_by=sort_by,
        sort_order=sort_order if sort_order in {"asc", "desc"} else "desc",
    )
    memberships = await _load_memberships(current_user.org_id, [contact.id for contact in contacts], db)
    items = [
        ContactResponse.model_validate(
            {
                "id": contact.id,
                "org_id": contact.org_id,
                "email": contact.email,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "phone": contact.phone,
                "status": contact.status,
                "custom_fields": contact.custom_fields,
                "source": contact.source,
                "created_at": contact.created_at,
                "list_memberships": memberships.get(contact.id, []),
            }
        )
        for contact in contacts
    ]
    return ContactListDetail(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: ContactCreate,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    try:
        contact = await contact_service.create_contact(current_user.org_id, payload, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return ContactResponse.model_validate(contact)


@router.get("/{contact_id}", response_model=ContactDetailResponse)
async def get_contact_detail(
    contact_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> ContactDetailResponse:
    try:
        contact = await contact_service.get_contact(current_user.org_id, contact_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc

    memberships = await _load_memberships(current_user.org_id, [contact.id], db)
    events = await contact_service.get_contact_event_history(current_user.org_id, contact.id, db)
    campaign_names = await _load_campaign_names([event.campaign_id for event in events], db)
    response = ContactDetailResponse.model_validate(contact).model_copy(
        update={
            "list_memberships": memberships.get(contact.id, []),
            "event_history": [
                {
                    "id": event.id,
                    "campaign_id": event.campaign_id,
                    "campaign_name": campaign_names.get(event.campaign_id),
                    "event_type": event.event_type,
                    "occurred_at": event.occurred_at,
                    "ip_address": event.ip_address,
                    "user_agent": event.user_agent,
                    "metadata": event.metadata_ or {},
                }
                for event in events
            ],
        }
    )
    return response


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    payload: ContactUpdate,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    try:
        contact = await contact_service.update_contact(current_user.org_id, contact_id, payload, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return ContactResponse.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await contact_service.delete_contact(current_user.org_id, contact_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _load_memberships(org_id: UUID, contact_ids: list[UUID], db: AsyncSession) -> dict[UUID, list[UUID]]:
    if not contact_ids:
        return {}
    result = await db.execute(
        select(ContactListMember.contact_id, ContactListMember.list_id)
        .join(ContactList, ContactList.id == ContactListMember.list_id)
        .where(ContactList.org_id == org_id, ContactListMember.contact_id.in_(contact_ids))
    )
    memberships: dict[UUID, list[UUID]] = {contact_id: [] for contact_id in contact_ids}
    for contact_id, list_id in result.all():
        if contact_id in memberships:
            memberships[contact_id].append(list_id)
    return memberships


async def _load_campaign_names(campaign_ids: list[UUID], db: AsyncSession) -> dict[UUID, str]:
    if not campaign_ids:
        return {}
    result = await db.execute(select(Campaign.id, Campaign.name).where(Campaign.id.in_(campaign_ids)))
    return {campaign_id: campaign_name for campaign_id, campaign_name in result.all()}
