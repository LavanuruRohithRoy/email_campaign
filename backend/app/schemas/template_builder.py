from __future__ import annotations

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class TemplateBuilderSaveRequest(BaseModel):
    name: str
    subject: str
    html_content: str
    design_json: dict
    is_draft: bool = True


class TemplatePreviewRequest(BaseModel):
    html_content: str
    sample_data: dict | None = None


class TestEmailRequest(BaseModel):
    to_email: str
    subject: str
    html_content: str


class TemplateVersionResponse(BaseModel):
    id: UUID
    version: int
    created_at: datetime
