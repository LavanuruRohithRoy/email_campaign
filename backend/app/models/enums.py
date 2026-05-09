from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    CAMPAIGN_MANAGER = "campaign_manager"
    VIEWER = "viewer"


class ContactStatus(str, Enum):
    ACTIVE = "active"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    COMPLAINED = "complained"


class ContactSource(str, Enum):
    IMPORT = "import"
    MANUAL = "manual"
    API = "api"
    FORM = "form"


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class EventType(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    UNSUBSCRIBED = "unsubscribed"


class TokenType(str, Enum):
    OPEN = "open"
    CLICK = "click"
    UNSUBSCRIBE = "unsubscribe"


class ImportJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SendStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class SuppressionReason(str, Enum):
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    MANUAL = "manual"
