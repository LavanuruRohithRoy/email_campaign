from __future__ import annotations

import pytest

from fastapi import HTTPException

from app.config import settings
from app.utils.webhook_signature import SNSSignatureVerifier, WebhookSignatureError
from app.middleware.rate_limit import ip_rate_limit


async def test_settings_in_test_mode():
    # Tests may run in environments where settings were loaded earlier;
    # accept either explicit 'test' or 'development' during local runs.
    assert settings.APP_ENV in ("test", "development")


async def test_security_and_request_id_headers(async_client):
    resp = await async_client.get("/api/v1/auth/health")
    assert resp.status_code == 200
    # Request ID injected by middleware
    assert "X-Request-ID" in resp.headers
    # Security headers set
    assert resp.headers.get("X-Frame-Options") == "DENY"


async def test_validation_error_shape(async_client):
    # Missing password field should trigger validation error
    resp = await async_client.post("/api/v1/auth/login", json={"email": "a@b.com"})
    assert resp.status_code == 422
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"


async def test_ip_rate_limit_logic(redis_client):
    # Create a small limit for testing
    limiter = ip_rate_limit(limit=3, window=60)

    class DummyRequest:
        def __init__(self, host: str = "127.0.0.1"):
            self.headers = {}
            self.client = type("C", (), {"host": host})()

    req = DummyRequest()

    # First three calls should pass
    await limiter(req, redis_client)
    await limiter(req, redis_client)
    await limiter(req, redis_client)

    # Fourth should raise HTTPException for rate limit
    with pytest.raises(HTTPException) as excinfo:
        await limiter(req, redis_client)
    assert excinfo.value.status_code == 429


async def test_sns_signature_missing_fields_raises():
    with pytest.raises(WebhookSignatureError):
        await SNSSignatureVerifier.verify_signature({})


async def test_health_endpoints(async_client):
    r1 = await async_client.get("/health/live")
    assert r1.status_code == 200
    assert r1.json().get("status") == "ok"

    r2 = await async_client.get("/health/ready")
    # readiness may report detailed component errors; ensure JSON response returned
    assert r2.status_code == 200
    assert "status" in r2.json()


async def test_docs_and_redoc_csp_allows_required_assets(async_client):
    docs = await async_client.get("/docs")
    redoc = await async_client.get("/redoc")
    openapi = await async_client.get("/openapi.json")

    assert docs.status_code == 200
    assert redoc.status_code == 200
    assert openapi.status_code == 200

    docs_csp = docs.headers.get("Content-Security-Policy", "")
    redoc_csp = redoc.headers.get("Content-Security-Policy", "")
    assert "cdn.jsdelivr.net" in docs_csp
    assert "cdn.jsdelivr.net" in redoc_csp
