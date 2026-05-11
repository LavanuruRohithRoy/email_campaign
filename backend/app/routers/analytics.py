from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis, require_role
from app.models.core import User
from app.routers.common import value_error_to_http_exception
from app.schemas.analytics import (
    AnalyticsExportResponse,
    AnalyticsTimeSeriesPoint,
    CampaignAnalyticsResponse,
    DashboardAnalyticsResponse,
    TopCampaignsResponse,
)
from app.services import analytics_service

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "analytics"}


@router.get("/dashboard", response_model=DashboardAnalyticsResponse)
async def dashboard_analytics(
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> DashboardAnalyticsResponse:
    return await analytics_service.get_dashboard_analytics(current_user.org_id, db, redis)


@router.get("/campaigns/top", response_model=TopCampaignsResponse)
async def top_campaigns(
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
) -> TopCampaignsResponse:
    return await analytics_service.get_top_campaigns(current_user.org_id, limit, db)


@router.get("/timeseries/opens", response_model=list[AnalyticsTimeSeriesPoint])
async def open_timeseries(
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
) -> list[AnalyticsTimeSeriesPoint]:
    return await analytics_service.get_open_timeseries(current_user.org_id, days, db)


@router.get("/timeseries/clicks", response_model=list[AnalyticsTimeSeriesPoint])
async def click_timeseries(
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
) -> list[AnalyticsTimeSeriesPoint]:
    return await analytics_service.get_click_timeseries(current_user.org_id, days, db)


@router.get("/campaigns/{campaign_id}", response_model=CampaignAnalyticsResponse)
async def campaign_analytics(
    campaign_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> CampaignAnalyticsResponse:
    try:
        return await analytics_service.get_campaign_analytics(current_user.org_id, campaign_id, db, redis)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc


@router.post("/campaigns/{campaign_id}/export", response_model=AnalyticsExportResponse)
async def export_campaign_report(
    campaign_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsExportResponse:
    try:
        download_url = await analytics_service.export_campaign_report_csv(current_user.org_id, campaign_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return AnalyticsExportResponse(download_url=download_url)
