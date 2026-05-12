from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, get_redis, require_role
from app.models.core import User
from app.schemas.auth import (
    BootstrapRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenResponse,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(tags=["Auth"])
logger = logging.getLogger(__name__)


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


@router.post("/bootstrap", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap(
    payload: BootstrapRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        user = await auth_service.bootstrap_super_admin(
            payload.email,
            payload.password,
            db,
            full_name=payload.full_name,
        )
    except ValueError as exc:
        if str(exc) == "BOOTSTRAP_DISABLED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"detail": "Bootstrap is disabled after initial setup", "code": "BOOTSTRAP_DISABLED"},
            ) from exc
        logger.exception("Unexpected bootstrap error", extra={"error_code": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": "Internal server error", "code": "INTERNAL_SERVER_ERROR"},
        ) from exc
    return UserResponse.model_validate(user)


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


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    current_user: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        user = await auth_service.create_user(
            org_id=current_user.org_id,
            email=payload.email,
            password=payload.password,
            role=payload.role,
            full_name=payload.full_name,
            is_active=payload.is_active,
            db=db,
        )
    except ValueError as exc:
        if str(exc) == "INVALID_ROLE_ASSIGNMENT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"detail": "Only campaign_manager or viewer roles are assignable", "code": "INVALID_ROLE_ASSIGNMENT"},
            ) from exc
        if str(exc) == "DUPLICATE_EMAIL":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": "Email already exists", "code": "DUPLICATE_EMAIL"},
            ) from exc
        logger.exception(
            "Unexpected admin user creation error",
            extra={"error_code": str(exc), "actor_user_id": str(current_user.id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"detail": "Internal server error", "code": "INTERNAL_SERVER_ERROR"},
        ) from exc
    return UserResponse.model_validate(user)


@router.get("/users", response_model=UserListResponse)
async def list_users(
    current_user: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> UserListResponse:
    users, total = await auth_service.list_users(
        org_id=current_user.org_id,
        limit=limit,
        offset=offset,
        db=db,
    )
    return UserListResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )
