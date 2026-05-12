from __future__ import annotations

from datetime import datetime
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models.core import User
from app.models.enums import CampaignStatus
from app.routers.common import value_error_to_http_exception
from app.schemas.campaign import (
    CampaignCreate,
    CampaignListResponse,
    CampaignRecipientsInput,
    CampaignResponse,
    CampaignScheduleInput,
    CampaignUpdate,
    RecipientCountResponse,
    TestSendRequest,
)
from app.services import campaign_service
from app.middleware.rate_limit import ip_rate_limit, org_rate_limit
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "campaigns"}


def _serialize_campaign(campaign, recipient_count: int) -> CampaignResponse:
    return CampaignResponse.model_validate(
        {
            **{key: value for key, value in campaign.__dict__.items() if not key.startswith("_")},
            "recipient_count": recipient_count,
        }
    )


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    status: CampaignStatus | None = Query(default=None, alias="status"),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> CampaignListResponse:
    campaigns, total = await campaign_service.get_campaigns(
        current_user.org_id,
        status,
        start_date,
        end_date,
        limit,
        offset,
        db,
    )
    items = []
    for campaign in campaigns:
        recipient_count = await campaign_service.estimate_recipient_count(current_user.org_id, campaign.id, db)
        items.append(_serialize_campaign(campaign, recipient_count))
    return CampaignListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    try:
        campaign = await campaign_service.create_campaign(current_user.org_id, current_user.id, payload, db)
        recipient_count = await campaign_service.estimate_recipient_count(current_user.org_id, campaign.id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return _serialize_campaign(campaign, recipient_count)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    try:
        campaign = await campaign_service.get_campaign(current_user.org_id, campaign_id, db)
        recipient_count = await campaign_service.estimate_recipient_count(current_user.org_id, campaign.id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return _serialize_campaign(campaign, recipient_count)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    try:
        campaign = await campaign_service.update_campaign(current_user.org_id, campaign_id, payload, db)
        recipient_count = await campaign_service.estimate_recipient_count(current_user.org_id, campaign.id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return _serialize_campaign(campaign, recipient_count)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await campaign_service.delete_campaign(current_user.org_id, campaign_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{campaign_id}/duplicate", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_campaign(
    campaign_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    try:
        campaign = await campaign_service.duplicate_campaign(current_user.org_id, campaign_id, current_user.id, db)
        recipient_count = await campaign_service.estimate_recipient_count(current_user.org_id, campaign.id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return _serialize_campaign(campaign, recipient_count)


@router.put("/{campaign_id}/recipients")
async def set_campaign_recipients(
    campaign_id: UUID,
    payload: CampaignRecipientsInput,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    try:
        await campaign_service.set_recipients(current_user.org_id, campaign_id, payload, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return {"updated": True}


@router.get("/{campaign_id}/recipient-count", response_model=RecipientCountResponse)
async def get_recipient_count(
    campaign_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> RecipientCountResponse:
    try:
        count = await campaign_service.estimate_recipient_count(current_user.org_id, campaign_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return RecipientCountResponse(estimated_count=count)


@router.post("/{campaign_id}/schedule", response_model=CampaignResponse)
async def schedule_campaign(
    campaign_id: UUID,
    payload: CampaignScheduleInput,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    try:
        campaign = await campaign_service.schedule_campaign(current_user.org_id, campaign_id, payload, db)
        recipient_count = await campaign_service.estimate_recipient_count(current_user.org_id, campaign.id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return _serialize_campaign(campaign, recipient_count)


@router.post("/{campaign_id}/cancel-schedule", response_model=CampaignResponse)
async def cancel_schedule(
    campaign_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    try:
        campaign = await campaign_service.cancel_schedule(current_user.org_id, campaign_id, db)
        recipient_count = await campaign_service.estimate_recipient_count(current_user.org_id, campaign.id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return _serialize_campaign(campaign, recipient_count)


@router.post("/{campaign_id}/test-send")
async def test_send(
    campaign_id: UUID,
    payload: TestSendRequest,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
    _rl: None = Depends(ip_rate_limit(limit=settings.RATE_LIMIT_TEST_EMAIL_PER_HOUR, window=3600)),
) -> dict[str, list[str] | str]:
    try:
        addresses = [str(address) for address in payload.email_addresses]
        await campaign_service.send_test_email(campaign_id, current_user.org_id, addresses, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return {"status": "queued", "addresses": addresses}



@router.post("/{campaign_id}/send")
async def send_campaign(
    campaign_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
    _org_rl: None = Depends(org_rate_limit(limit=1000, window=3600)),
) -> dict[str, str | int]:
    try:
        queued = await campaign_service.enqueue_campaign(current_user.org_id, campaign_id, db)
    except ValueError as exc:
        code = str(exc)
        if code == "INVALID_STATUS_FOR_SEND":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": "Campaign cannot be sent in current status", "code": code},
            ) from exc
        raise value_error_to_http_exception(exc) from exc
    return {"status": "sending", "queued": queued}


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    try:
        campaign = await campaign_service.pause_campaign(current_user.org_id, campaign_id, db)
        recipient_count = await campaign_service.estimate_recipient_count(current_user.org_id, campaign.id, db)
    except ValueError as exc:
        code = str(exc)
        if code == "NOT_SENDING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": "Campaign is not currently sending", "code": code},
            ) from exc
        raise value_error_to_http_exception(exc) from exc
    return _serialize_campaign(campaign, recipient_count)


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(
    campaign_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    try:
        campaign = await campaign_service.resume_campaign(current_user.org_id, campaign_id, db)
        recipient_count = await campaign_service.estimate_recipient_count(current_user.org_id, campaign.id, db)
    except ValueError as exc:
        code = str(exc)
        if code == "NOT_PAUSED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": "Campaign is not paused", "code": code},
            ) from exc
        raise value_error_to_http_exception(exc) from exc
    return _serialize_campaign(campaign, recipient_count)


@router.get("/{campaign_id}/progress")
async def get_send_progress(
    campaign_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    try:
        return await campaign_service.get_send_progress(current_user.org_id, campaign_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
