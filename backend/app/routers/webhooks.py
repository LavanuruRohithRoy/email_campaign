from __future__ import annotations

import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.rate_limit import ip_rate_limit
from app.config import settings
from app.schemas.webhook import SESNotificationPayload, SNSMessageEnvelope
from app.services.webhook_service import process_ses_notification
from app.utils.webhook_signature import SNSSignatureVerifier, WebhookSignatureError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "webhooks"}


@router.post("/ses")
async def handle_ses_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(ip_rate_limit(limit=settings.RATE_LIMIT_WEBHOOK_PER_MINUTE, window=60)),
) -> dict[str, str]:
    """
    Handle SES events via SNS subscription.
    
    Validates SNS signature before processing.
    """
    try:
        raw_payload = await request.json()
        envelope = SNSMessageEnvelope.model_validate(raw_payload)
    except Exception as e:
        logger.warning(f"Invalid SNS payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_sns_payload"
        )

    # Verify SNS signature
    try:
        await SNSSignatureVerifier.verify_signature(raw_payload)
    except WebhookSignatureError as e:
        logger.error(f"SNS signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_webhook_signature",
        )

    if envelope.Type == "SubscriptionConfirmation":
        if not envelope.SubscribeURL:
            logger.warning("Subscription confirmation missing SubscribeURL")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_subscribe_url"
            )

        # Confirm SNS subscription
        try:
            async with httpx.AsyncClient() as client:
                await client.get(envelope.SubscribeURL, timeout=10.0)
            logger.info("SNS subscription confirmed")
        except Exception as e:
            logger.error(f"Failed to confirm SNS subscription: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="failed_to_confirm_subscription",
            )

        return {"status": "subscription_confirmed"}

    if envelope.Type == "Notification":
        try:
            message_payload = SESNotificationPayload.model_validate(
                json.loads(envelope.Message)
            )
        except Exception as e:
            logger.warning(f"Invalid SES payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_ses_payload"
            )

        # Process SES notification
        try:
            await process_ses_notification(message_payload, db)
        except Exception as e:
            logger.error(f"Error processing SES notification: {e}", exc_info=True)
            # Still return 200 to acknowledge receipt to SNS
            # SQS/DLQ will handle failures in the future

        return {"status": "processed"}

    logger.warning(f"Unsupported SNS message type: {envelope.Type}")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_sns_type"
    )

