from __future__ import annotations

import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-length-123456")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-minimum-length-123456")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/emailplatform"
)
os.environ.setdefault(
    "DATABASE_URL_SYNC", "postgresql+psycopg2://user:pass@localhost:5432/emailplatform"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_REGION", "ap-south-1")
os.environ.setdefault("AWS_S3_BUCKET", "test-bucket")
os.environ.setdefault("AWS_SQS_SEND_QUEUE_URL", "https://sqs.ap-south-1.amazonaws.com/123/send")
os.environ.setdefault(
    "AWS_SQS_EVENTS_QUEUE_URL", "https://sqs.ap-south-1.amazonaws.com/123/events"
)
os.environ.setdefault("AWS_SES_CONFIG_SET", "email-platform-events")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")


@pytest.fixture()
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
