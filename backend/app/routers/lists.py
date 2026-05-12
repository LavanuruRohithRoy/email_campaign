from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models.contacts import ContactList, ContactListMember
from app.models.core import User
from app.models.enums import ContactStatus
from app.routers.common import value_error_to_http_exception
from app.schemas.contact import (
    CSVPreviewResponse,
    ContactListCollectionResponse,
    ContactListCreate,
    ContactListDetail,
    ContactListResponse,
    ContactListUpdate,
    ContactResponse,
    ImportJobResponse,
)
from app.services import contact_service, import_service

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "lists"}


@router.get("", response_model=ContactListCollectionResponse)
async def list_contact_lists(
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ContactListCollectionResponse:
    lists = await contact_service.get_lists(current_user.org_id, db)
    total = len(lists)
    page = lists[offset : offset + limit]
    items = [ContactListResponse.model_validate(item) for item in page]
    return ContactListCollectionResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=ContactListResponse, status_code=status.HTTP_201_CREATED)
async def create_contact_list(
    payload: ContactListCreate,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> ContactListResponse:
    contact_list = await contact_service.create_list(current_user.org_id, payload, db)
    list_data = await contact_service.get_list(current_user.org_id, contact_list.id, db)
    return ContactListResponse.model_validate(list_data)


@router.get("/{list_id}", response_model=ContactListResponse)
async def get_contact_list(
    list_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> ContactListResponse:
    try:
        list_data = await contact_service.get_list(current_user.org_id, list_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return ContactListResponse.model_validate(list_data)


@router.put("/{list_id}", response_model=ContactListResponse)
async def update_contact_list(
    list_id: UUID,
    payload: ContactListUpdate,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> ContactListResponse:
    try:
        contact_list = await contact_service.update_list(current_user.org_id, list_id, payload, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    list_data = await contact_service.get_list(current_user.org_id, contact_list.id, db)
    return ContactListResponse.model_validate(list_data)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact_list(
    list_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await contact_service.delete_list(current_user.org_id, list_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{list_id}/contacts", response_model=ContactListDetail)
async def list_contacts_in_list(
    list_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(default=None),
    status_filter: ContactStatus | None = Query(default=None, alias="status"),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ContactListDetail:
    try:
        contacts, total = await contact_service.get_contacts(
            current_user.org_id,
            list_id,
            search,
            status_filter,
            limit,
            offset,
            db,
            sort_by=sort_by,
            sort_order=sort_order if sort_order in {"asc", "desc"} else "desc",  # type: ignore[arg-type]
        )
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
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


@router.post("/{list_id}/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_contact_to_list(
    list_id: UUID,
    contact_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await contact_service.add_to_list(current_user.org_id, contact_id, list_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{list_id}/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_contact_from_list(
    list_id: UUID,
    contact_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await contact_service.remove_from_list(current_user.org_id, contact_id, list_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{list_id}/import/preview", response_model=CSVPreviewResponse)
async def preview_import_csv(
    list_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> CSVPreviewResponse:
    try:
        await contact_service.get_list(current_user.org_id, list_id, db)
        file_bytes = await file.read()
        return await import_service.preview_csv(file_bytes)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc


@router.post("/{list_id}/import", response_model=ImportJobResponse, status_code=status.HTTP_201_CREATED)
async def start_import(
    list_id: UUID,
    file: UploadFile = File(...),
    column_mapping: str = Form(...),
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> ImportJobResponse:
    try:
        await contact_service.get_list(current_user.org_id, list_id, db)
        mapping_data = json.loads(column_mapping)
        if not isinstance(mapping_data, dict):
            raise ValueError("INVALID_CSV")
        normalized_mapping = {str(key): str(value) for key, value in mapping_data.items()}
        file_bytes = await file.read()
        job = await import_service.start_import_job(
            current_user.org_id,
            list_id,
            current_user.id,
            normalized_mapping,
            file_bytes,
            db,
        )
        return ImportJobResponse.model_validate(job)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc


@router.get("/{list_id}/import/{job_id}", response_model=ImportJobResponse)
async def get_import_status(
    list_id: UUID,
    job_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> ImportJobResponse:
    try:
        job = await import_service.get_import_job(current_user.org_id, job_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return ImportJobResponse.model_validate(job)


async def _load_memberships(org_id: UUID, contact_ids: list[UUID], db: AsyncSession) -> dict[UUID, list[UUID]]:
    if not contact_ids:
        return {}
    result = await db.execute(
        select(ContactListMember.contact_id, ContactListMember.list_id)
        .join(ContactList, ContactList.id == ContactListMember.list_id)
        .where(ContactList.org_id == org_id, ContactListMember.contact_id.in_(contact_ids))
    )
    memberships: dict[UUID, list[UUID]] = {contact_id: [] for contact_id in contact_ids}
    for contact_id, membership_list_id in result.all():
        memberships.setdefault(contact_id, []).append(membership_list_id)
    return memberships
