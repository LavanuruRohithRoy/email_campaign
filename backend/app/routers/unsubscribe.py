from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.unsubscribe import UnsubscribeResponse
from app.services.unsubscribe_service import unsubscribe_contact

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "unsubscribe"}


@router.get("", response_model=UnsubscribeResponse)
async def unsubscribe(t: str, db: AsyncSession = Depends(get_db)) -> UnsubscribeResponse:
    unsubscribed = await unsubscribe_contact(t, db)
    if not unsubscribed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Invalid unsubscribe token", "code": "INVALID_UNSUBSCRIBE_TOKEN"},
        )
    return UnsubscribeResponse(
        status="success",
        message="You have been unsubscribed successfully",
    )
