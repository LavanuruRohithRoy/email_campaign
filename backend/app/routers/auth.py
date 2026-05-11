from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, get_redis, require_role
from app.models.core import User
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(tags=["Auth"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "auth"}


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> LoginResponse:
    ip = request.client.host if request.client is not None else "127.0.0.1"
    try:
        access_token, refresh_token = await auth_service.login(payload.email, payload.password, ip, db, redis)
    except ValueError as exc:
        if str(exc) == "INVALID_CREDENTIALS":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"detail": "Invalid email or password", "code": "INVALID_CREDENTIALS"},
            ) from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"detail": "Internal server error", "code": "INTERNAL_SERVER_ERROR"}) from exc
    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        access_token, refresh_token = await auth_service.refresh_tokens(payload.refresh_token, db)
    except ValueError as exc:
        if str(exc) == "INVALID_REFRESH_TOKEN":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"detail": "Invalid or expired refresh token", "code": "INVALID_REFRESH_TOKEN"},
            ) from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"detail": "Internal server error", "code": "INTERNAL_SERVER_ERROR"}) from exc
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    await auth_service.logout(payload.refresh_token, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get("/super-admin-only")
async def super_admin_only(_current_user: User = Depends(require_role("super_admin"))) -> dict[str, str]:
    return {"status": "ok", "module": "auth", "role": "super_admin"}
