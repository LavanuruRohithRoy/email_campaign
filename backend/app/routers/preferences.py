from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.contacts import Contact
from app.models.enums import ContactStatus
from app.schemas.unsubscribe import ManagePreferenceRequest, PreferenceCenterResponse
from app.services.unsubscribe_service import get_preferences, update_preferences

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "preferences"}


def _preference_response(contact: Contact) -> PreferenceCenterResponse:
    return PreferenceCenterResponse(
        contact_id=contact.id,
        email=contact.email,
        status=contact.status,
        unsubscribed=contact.status == ContactStatus.UNSUBSCRIBED,
        updated_at=None,
    )


@router.get("", response_model=PreferenceCenterResponse)
async def preferences(t: str, db: AsyncSession = Depends(get_db)) -> PreferenceCenterResponse:
    contact = await get_preferences(t, db)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Invalid preference token", "code": "INVALID_PREFERENCE_TOKEN"},
        )
    return _preference_response(contact)


@router.post("", response_model=PreferenceCenterResponse)
async def manage_preferences(
    payload: ManagePreferenceRequest,
    t: str,
    db: AsyncSession = Depends(get_db),
) -> PreferenceCenterResponse:
    contact = await update_preferences(t, payload.unsubscribed, db)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Invalid preference token", "code": "INVALID_PREFERENCE_TOKEN"},
        )
    return _preference_response(contact)
