from __future__ import annotations

from httpx import AsyncClient

from app.config import settings


async def test_health_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/auth/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "module": "auth"}


async def test_health_all_routers(async_client: AsyncClient) -> None:
    paths = [
        "/api/v1/auth/health",
        "/api/v1/contacts/health",
        "/api/v1/lists/health",
        "/api/v1/segments/health",
        "/api/v1/templates/health",
        "/api/v1/campaigns/health",
        "/api/v1/analytics/health",
        "/api/v1/webhooks/health",
        "/track/health",
        "/unsubscribe/health",
        "/preferences/health",
    ]

    for path in paths:
        response = await async_client.get(path)
        assert response.status_code == 200


def test_settings_loaded() -> None:
    assert settings.JWT_SECRET is not None
    assert len(settings.JWT_SECRET) > 8


def test_models_importable() -> None:
    from app.models import campaigns, contacts, core, tracking

    assert campaigns is not None
    assert contacts is not None
    assert core is not None
    assert tracking is not None
