from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CampaignAnalyticsResponse(BaseModel):
    campaign_id: UUID
    sent: int
    delivered: int
    opened: int
    clicked: int
    bounced: int
    complained: int
    unsubscribed: int
    open_rate: float
    click_rate: float
    bounce_rate: float
    complaint_rate: float
    unsubscribe_rate: float


class DashboardAnalyticsResponse(BaseModel):
    total_contacts: int
    active_contacts: int
    total_campaigns: int
    total_sent: int
    total_opens: int
    total_clicks: int
    avg_open_rate: float
    avg_click_rate: float


class AnalyticsTimeSeriesPoint(BaseModel):
    timestamp: datetime
    value: int


class CampaignPerformanceItem(BaseModel):
    campaign_id: UUID
    campaign_name: str
    sent: int
    open_rate: float
    click_rate: float
    created_at: datetime


class TopCampaignsResponse(BaseModel):
    items: list[CampaignPerformanceItem]


class AnalyticsExportResponse(BaseModel):
    download_url: str
