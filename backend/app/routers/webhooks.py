from __future__ import annotations

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.webhook import SESNotificationPayload, SNSMessageEnvelope
from app.services.webhook_service import process_ses_notification

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "webhooks"}


@router.post("/ses")
async def handle_ses_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        raw_payload = await request.json()
        envelope = SNSMessageEnvelope.model_validate(raw_payload)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_sns_payload")

    if envelope.Type == "SubscriptionConfirmation":
        if not envelope.SubscribeURL:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_subscribe_url")
        async with httpx.AsyncClient() as client:
            await client.get(envelope.SubscribeURL)
        return {"status": "subscription_confirmed"}

    if envelope.Type == "Notification":
        try:
            message_payload = SESNotificationPayload.model_validate(json.loads(envelope.Message))
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_ses_payload")
        await process_ses_notification(message_payload, db)
        return {"status": "processed"}

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_sns_type")
