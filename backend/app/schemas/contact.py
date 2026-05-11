from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ContactSource, ContactStatus, ImportJobStatus, SuppressionReason


class ContactListCreate(BaseModel):
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class ContactListUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class ContactListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    name: str
    description: str | None
    tags: list[str]
    contact_count: int
    created_at: datetime


class ContactListCollectionResponse(BaseModel):
    items: list[ContactListResponse]
    total: int
    limit: int
    offset: int


class ContactCreate(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    source: ContactSource = ContactSource.MANUAL
    custom_fields: dict[str, str] = Field(default_factory=dict)


class ContactUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    custom_fields: dict[str, str] | None = None


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    phone: str | None
    status: ContactStatus
    custom_fields: dict[str, str]
    source: ContactSource
    created_at: datetime
    list_memberships: list[UUID] = Field(default_factory=list)


class ContactEventResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    campaign_name: str | None = None
    event_type: str
    occurred_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ContactDetailResponse(ContactResponse):
    event_history: list[ContactEventResponse] = Field(default_factory=list)


class ContactDetailPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ContactResponse]
    total: int
    limit: int
    offset: int


class ContactListDetail(BaseModel):
    items: list[ContactResponse]
    total: int
    limit: int
    offset: int


class SegmentRuleCondition(BaseModel):
    field: str
    operator: str
    value: str


class SegmentRules(BaseModel):
    operator: Literal["AND", "OR"]
    conditions: list[SegmentRuleCondition]


class SegmentCreate(BaseModel):
    name: str
    rules: SegmentRules


class SegmentUpdate(BaseModel):
    name: str | None = None
    rules: SegmentRules | None = None


class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    name: str
    rules: dict[str, object]
    created_at: datetime


class SegmentCollectionResponse(BaseModel):
    items: list[SegmentResponse]
    total: int
    limit: int
    offset: int


class SegmentCountResponse(BaseModel):
    count: int


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    list_id: UUID
    status: ImportJobStatus
    total_rows: int
    added: int
    updated: int
    skipped: int
    errored: int
    error_log: list[dict[str, object]]
    started_at: datetime | None
    completed_at: datetime | None


class CSVPreviewResponse(BaseModel):
    headers: list[str]
    preview_rows: list[list[str]]
    total_rows: int


class BulkDeleteContactsRequest(BaseModel):
    ids: list[UUID]


class SuppressionListEntryResponse(BaseModel):
    id: UUID
    org_id: UUID
    email: str
    reason: SuppressionReason
    suppressed_at: datetime
    added_by: UUID | None