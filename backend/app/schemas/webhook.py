from __future__ import annotations

from pydantic import BaseModel


class SNSMessageEnvelope(BaseModel):
    Type: str
    MessageId: str
    TopicArn: str
    Subject: str | None = None
    Message: str
    Timestamp: str
    SignatureVersion: str | None = None
    Signature: str | None = None
    SigningCertURL: str | None = None
    SubscribeURL: str | None = None


class SESMailObject(BaseModel):
    messageId: str
    timestamp: str
    source: str
    destination: list[str]
    tags: dict[str, list[str]] | None = None


class SESBounceRecipient(BaseModel):
    emailAddress: str
    action: str | None = None
    status: str | None = None
    diagnosticCode: str | None = None


class SESBounceObject(BaseModel):
    bounceType: str
    bounceSubType: str | None = None
    bouncedRecipients: list[SESBounceRecipient]
    timestamp: str
    feedbackId: str | None = None


class SESComplaintRecipient(BaseModel):
    emailAddress: str


class SESComplaintObject(BaseModel):
    complainedRecipients: list[SESComplaintRecipient]
    timestamp: str
    complaintFeedbackType: str | None = None
    feedbackId: str | None = None


class SESNotificationPayload(BaseModel):
    notificationType: str
    mail: SESMailObject
    bounce: SESBounceObject | None = None
    complaint: SESComplaintObject | None = None


class WebhookResponse(BaseModel):
    status: str
