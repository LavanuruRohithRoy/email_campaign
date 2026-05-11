from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import CampaignStatus


class CampaignDetailsInput(BaseModel):
    name: str
    subject: str = Field(max_length=998)
    preview_text: str | None = None
    from_name: str
    from_email: EmailStr
    reply_to: EmailStr | None = None


class CampaignRecipientsInput(BaseModel):
    target_list_ids: list[UUID] = Field(default_factory=list)
    target_segment_ids: list[UUID] = Field(default_factory=list)
    exclude_list_ids: list[UUID] = Field(default_factory=list)


class CampaignDesignInput(BaseModel):
    template_id: UUID


class CampaignScheduleInput(BaseModel):
    scheduled_at: datetime
    timezone: str

    @field_validator("scheduled_at")
    @classmethod
    def must_be_future(cls, value: datetime) -> datetime:
        candidate = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        if candidate <= datetime.now(timezone.utc):
            raise ValueError("scheduled_at must be in the future")
        return candidate


class CampaignCreate(CampaignDetailsInput):
    target_list_ids: list[UUID] = Field(default_factory=list)
    target_segment_ids: list[UUID] = Field(default_factory=list)
    exclude_list_ids: list[UUID] = Field(default_factory=list)
    template_id: UUID | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    subject: str | None = Field(default=None, max_length=998)
    preview_text: str | None = None
    from_name: str | None = None
    from_email: EmailStr | None = None
    reply_to: EmailStr | None = None
    template_id: UUID | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    name: str
    subject: str
    preview_text: str | None
    from_name: str
    from_email: str
    reply_to: str | None
    status: CampaignStatus
    template_id: UUID | None
    scheduled_at: datetime | None
    timezone: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime | None
    recipient_count: int = 0


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int
    limit: int
    offset: int


class RecipientCountResponse(BaseModel):
    estimated_count: int


class TestSendRequest(BaseModel):
    email_addresses: list[EmailStr]

    @field_validator("email_addresses")
    @classmethod
    def max_five(cls, value: list[EmailStr]) -> list[EmailStr]:
        if len(value) > 5:
            raise ValueError("Maximum 5 test addresses allowed")
        return value


class CampaignRecipientConfig(BaseModel):
    target_list_ids: list[UUID] = Field(default_factory=list)
    target_segment_ids: list[UUID] = Field(default_factory=list)
    exclude_list_ids: list[UUID] = Field(default_factory=list)