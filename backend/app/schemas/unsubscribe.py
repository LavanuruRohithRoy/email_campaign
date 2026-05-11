from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import ContactStatus


class UnsubscribeResponse(BaseModel):
    status: str
    message: str


class PreferenceCenterResponse(BaseModel):
    contact_id: UUID
    email: str
    status: ContactStatus
    unsubscribed: bool
    updated_at: datetime | None = None


class ManagePreferenceRequest(BaseModel):
    unsubscribed: bool
