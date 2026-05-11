from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TemplateCreate(BaseModel):
    name: str
    category: str | None = None
    blocks: dict[str, object]
    html: str
    thumbnail_url: str | None = None


class TemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    blocks: dict[str, object] | None = None
    html: str | None = None
    thumbnail_url: str | None = None


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    name: str
    category: str | None
    blocks: dict[str, object]
    html: str
    thumbnail_url: str | None
    created_at: datetime
    updated_at: datetime


class TemplateSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    name: str
    category: str | None
    thumbnail_url: str | None
    created_at: datetime
    updated_at: datetime


class TemplateListResponse(BaseModel):
    items: list[TemplateSummaryResponse]
    total: int
    limit: int
    offset: int


class ImageUploadResponse(BaseModel):
    url: str