from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.campaigns import Campaign, Template
from app.models.core import User
from app.models.enums import UserRole
from app.utils.security import hash_password


@pytest.fixture()
async def seed_campaign_manager_user(seed_user: User) -> User:
    yield seed_user


@pytest.fixture()
async def manager_auth_headers(async_client, seed_campaign_manager_user: User) -> dict[str, str]:
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": seed_campaign_manager_user.email, "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture()
async def seed_template(db_session, seed_campaign_manager_user: User) -> Template:
    template = Template(
        org_id=seed_campaign_manager_user.org_id,
        name="Seed Template",
        category="Welcome",
        blocks={"schemaVersion": 11, "body": {"rows": [], "values": {"contentWidth": "600px"}}},
        html="<div style='font-family: Arial;'>Hello {{first_name}}</div>",
        thumbnail_url=None,
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest.fixture()
async def seed_super_admin_user(db_session, seed_user: User) -> User:
    admin_email = f"admin-{uuid4().hex}@example.com"
    admin = User(
        org_id=seed_user.org_id,
        email=admin_email,
        password_hash=hash_password("password123"),
        full_name="Admin User",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture()
async def super_admin_auth_headers(async_client, seed_super_admin_user: User) -> dict[str, str]:
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": seed_super_admin_user.email, "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture()
async def viewer_user(db_session, seed_user: User) -> User:
    viewer_email = f"viewer-{uuid4().hex}@example.com"
    viewer = User(
        org_id=seed_user.org_id,
        email=viewer_email,
        password_hash=hash_password("password123"),
        full_name="Viewer User",
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(viewer)
    await db_session.commit()
    await db_session.refresh(viewer)
    return viewer


@pytest.fixture()
async def viewer_auth_headers(async_client, viewer_user: User) -> dict[str, str]:
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": viewer_user.email, "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_create_template(async_client, seed_campaign_manager_user: User, manager_auth_headers):
    response = await async_client.post(
        "/api/v1/templates",
        json={
            "name": "New Template",
            "category": "Welcome",
            "blocks": {"schemaVersion": 11, "body": {"rows": []}},
            "html": "<div style='font-family: Arial;'>Hi {{first_name}}</div>",
        },
        headers=manager_auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "New Template"
    assert body["blocks"]
    assert body["html"]


async def test_get_template_list(async_client, seed_campaign_manager_user: User, seed_template: Template, db_session, manager_auth_headers):
    extra_template = Template(
        org_id=seed_campaign_manager_user.org_id,
        name="Another Template",
        category="Newsletter",
        blocks={"schemaVersion": 11, "body": {"rows": []}},
        html="<div style='font-family: Arial;'>Newsletter</div>",
        thumbnail_url=None,
    )
    db_session.add(extra_template)
    await db_session.commit()

    response = await async_client.get("/api/v1/templates", headers=manager_auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 2


async def test_get_template_by_id(async_client, seed_template: Template, manager_auth_headers):
    response = await async_client.get(f"/api/v1/templates/{seed_template.id}", headers=manager_auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["blocks"]
    assert body["html"]


async def test_update_template(async_client, seed_template: Template, manager_auth_headers):
    response = await async_client.put(
        f"/api/v1/templates/{seed_template.id}",
        json={"name": "Updated Template"},
        headers=manager_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Template"


async def test_duplicate_template(async_client, seed_template: Template, manager_auth_headers):
    response = await async_client.post(
        f"/api/v1/templates/{seed_template.id}/duplicate",
        headers=manager_auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] != str(seed_template.id)
    assert "(Copy)" in body["name"]


async def test_delete_template(async_client, seed_template: Template, manager_auth_headers):
    response = await async_client.delete(f"/api/v1/templates/{seed_template.id}", headers=manager_auth_headers)
    assert response.status_code == 204

    follow_up = await async_client.get(f"/api/v1/templates/{seed_template.id}", headers=manager_auth_headers)
    assert follow_up.status_code == 404


async def test_delete_template_in_use(async_client, seed_campaign_manager_user: User, seed_template: Template, db_session, manager_auth_headers):
    campaign = Campaign(
        org_id=seed_campaign_manager_user.org_id,
        name="Campaign With Template",
        subject="Subject",
        from_name="Team",
        from_email="team@example.com",
        created_by=seed_campaign_manager_user.id,
        template_id=seed_template.id,
    )
    db_session.add(campaign)
    await db_session.commit()

    response = await async_client.delete(f"/api/v1/templates/{seed_template.id}", headers=manager_auth_headers)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "TEMPLATE_IN_USE"


async def test_viewer_cannot_create_template(async_client, viewer_auth_headers):
    response = await async_client.post(
        "/api/v1/templates",
        json={
            "name": "Should fail",
            "category": "Welcome",
            "blocks": {"schemaVersion": 11, "body": {"rows": []}},
            "html": "<div>Blocked</div>",
        },
        headers=viewer_auth_headers,
    )
    assert response.status_code == 403


async def test_viewer_can_read_template(async_client, seed_template: Template, viewer_auth_headers):
    response = await async_client.get("/api/v1/templates", headers=viewer_auth_headers)
    assert response.status_code == 200


async def test_upload_asset_invalid_type(async_client, manager_auth_headers):
    response = await async_client.post(
        "/api/v1/templates/upload-asset",
        files={"file": ("note.txt", b"hello", "text/plain")},
        headers=manager_auth_headers,
    )
    assert response.status_code == 400


async def test_seed_endpoint(async_client, seed_super_admin_user: User, super_admin_auth_headers):
    response = await async_client.post("/api/v1/templates/seed", headers=super_admin_auth_headers)
    assert response.status_code == 200
    assert response.json()["seeded"] is True

    follow_up = await async_client.get("/api/v1/templates", headers=super_admin_auth_headers)
    assert follow_up.status_code == 200
    assert follow_up.json()["items"]
    assert len(follow_up.json()["items"]) >= 5