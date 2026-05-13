from __future__ import annotations

from sqlalchemy import delete

from app.models.core import Organisation, RefreshToken, User


async def test_login_success(async_client, seed_user):

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_wrong_password(async_client, seed_user):

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


async def test_login_rate_limit(async_client, seed_user, redis_client):
    for _ in range(5):
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpass"},
        )
        assert response.status_code == 401

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 429
    await redis_client.flushdb()


async def test_get_me_authenticated(async_client, seed_user):

    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    access_token = login.json()["access_token"]

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test@example.com"
    assert body["role"] == "campaign_manager"
    assert "password_hash" not in body


async def test_get_me_no_token(async_client):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_refresh_tokens(async_client, seed_user):

    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    refresh_token = login.json()["refresh_token"]

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_token_reuse(async_client, seed_user):

    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    refresh_token = login.json()["refresh_token"]

    first = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert first.status_code == 200

    second = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert second.status_code == 401


async def test_role_guard_forbidden(async_client, seed_user):

    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    access_token = login.json()["access_token"]

    response = await async_client.get(
        "/api/v1/auth/super-admin-only",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "INSUFFICIENT_PERMISSIONS"


async def test_logout(async_client, seed_user):

    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    body = login.json()

    response = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": body["refresh_token"]},
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert response.status_code == 204

    refresh_after_logout = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert refresh_after_logout.status_code == 401


async def test_bootstrap_creates_first_super_admin(async_client, db_session):
    await db_session.execute(delete(RefreshToken))
    await db_session.execute(delete(User))
    await db_session.execute(delete(Organisation))
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "owner@example.com",
            "password": "StrongPassword123",
            "full_name": "Owner",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "owner@example.com"
    assert body["role"] == "super_admin"


async def test_bootstrap_disabled_when_users_exist(async_client, seed_user):
    response = await async_client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "owner2@example.com", "password": "StrongPassword123"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "BOOTSTRAP_DISABLED"


async def test_bootstrap_hidden_from_openapi_after_initialization(async_client, seed_user):
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/auth/bootstrap" not in response.json()["paths"]


async def test_bootstrap_visible_in_openapi_before_initialization(async_client, db_session):
    await db_session.execute(delete(RefreshToken))
    await db_session.execute(delete(User))
    await db_session.execute(delete(Organisation))
    await db_session.commit()

    response = await async_client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/auth/bootstrap" in response.json()["paths"]


async def test_super_admin_can_create_and_list_users(async_client, db_session):
    await db_session.execute(delete(RefreshToken))
    await db_session.execute(delete(User))
    await db_session.execute(delete(Organisation))
    await db_session.commit()

    bootstrap = await async_client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "owner@example.com", "password": "StrongPassword123"},
    )
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "StrongPassword123"},
    )
    admin_token = admin_login.json()["access_token"]
    assert bootstrap.status_code == 201

    create_user = await async_client.post(
        "/api/v1/auth/users",
        json={
            "email": "viewer@example.com",
            "password": "StrongPassword123",
            "role": "viewer",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_user.status_code == 201
    assert create_user.json()["role"] == "viewer"

    list_users = await async_client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_users.status_code == 200
    users = list_users.json()["items"]
    assert len(users) == 2
    assert {user["role"] for user in users} == {"super_admin", "viewer"}


async def test_non_super_admin_cannot_create_users(async_client, seed_user):
    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    access_token = login.json()["access_token"]

    create_user = await async_client.post(
        "/api/v1/auth/users",
        json={
            "email": "viewer@example.com",
            "password": "StrongPassword123",
            "role": "viewer",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert create_user.status_code == 403
