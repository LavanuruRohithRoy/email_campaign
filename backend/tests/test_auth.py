from __future__ import annotations

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
