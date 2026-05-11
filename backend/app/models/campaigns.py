from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import CampaignStatus, SendStatus


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    blocks: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    html: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    preview_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_name: Mapped[str] = mapped_column(String(255), nullable=False)
    from_email: Mapped[str] = mapped_column(String(320), nullable=False)
    reply_to: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"),
        nullable=False,
        default=CampaignStatus.DRAFT,
    )
    template_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("templates.id"), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CampaignSend(Base):
    __tablename__ = "campaign_sends"
    __table_args__ = (
        UniqueConstraint("campaign_id", "contact_id", name="uq_campaign_sends_pair"),
        Index("ix_campaign_sends_campaign", "campaign_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False
    )
    contact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False
    )
    ses_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[SendStatus] = mapped_column(
        Enum(SendStatus, name="send_status"), nullable=False, default=SendStatus.QUEUED
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
