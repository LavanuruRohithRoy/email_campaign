from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.rate_limit import check_login_rate_limit, reset_login_rate_limit
from app.models.core import Organisation, RefreshToken, User
from app.models.enums import UserRole
from app.utils.security import create_access_token, hash_password, verify_password

# Static, service-specific advisory lock id used to serialize bootstrap requests.
BOOTSTRAP_ADVISORY_LOCK_KEY = 918273645


async def login(
    email: str,
    password: str,
    ip: str,
    db: AsyncSession,
    redis: Redis,
) -> tuple[str, str]:
    await check_login_rate_limit(ip, redis)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise ValueError("INVALID_CREDENTIALS")

    if not verify_password(password, user.password_hash):
        raise ValueError("INVALID_CREDENTIALS")

    await reset_login_rate_limit(ip, redis)

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role.value, "org_id": str(user.org_id)},
        expires_delta=timedelta(minutes=15),
    )

    raw_token = secrets.token_urlsafe(32)
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_password(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        used=False,
    )
    db.add(refresh_token)
    await db.commit()

    return access_token, raw_token


async def refresh_tokens(raw_refresh_token: str, db: AsyncSession) -> tuple[str, str]:
    utcnow = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.used.is_(False), RefreshToken.expires_at >= utcnow)
        .order_by(RefreshToken.created_at.desc())
        .limit(10)
    )
    candidates = result.scalars().all()

    matched: RefreshToken | None = None
    for row in candidates:
        if verify_password(raw_refresh_token, row.token_hash):
            matched = row
            break

    if matched is None:
        raise ValueError("INVALID_REFRESH_TOKEN")

    if matched.used or matched.expires_at < utcnow:
        raise ValueError("INVALID_REFRESH_TOKEN")

    matched.used = True
    await db.commit()

    user = await db.get(User, matched.user_id)
    if user is None:
        raise ValueError("INVALID_REFRESH_TOKEN")

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role.value, "org_id": str(user.org_id)},
        expires_delta=timedelta(minutes=15),
    )

    new_raw_token = secrets.token_urlsafe(32)
    new_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_password(new_raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        used=False,
    )
    db.add(new_refresh_token)
    await db.commit()

    return access_token, new_raw_token


async def logout(raw_refresh_token: str, db: AsyncSession) -> None:
    utcnow = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.used.is_(False), RefreshToken.expires_at >= utcnow)
        .order_by(RefreshToken.created_at.desc())
        .limit(10)
    )
    candidates = result.scalars().all()

    for row in candidates:
        if verify_password(raw_refresh_token, row.token_hash):
            row.used = True
            await db.commit()
            return


async def get_user_by_id(user_id: UUID, db: AsyncSession) -> User | None:
    return await db.get(User, user_id)


async def bootstrap_super_admin(
    email: str,
    password: str,
    db: AsyncSession,
    full_name: str | None = None,
) -> User:
    async with db.begin():
        # Transaction-scoped PostgreSQL advisory lock prevents concurrent bootstrap races.
        await db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": BOOTSTRAP_ADVISORY_LOCK_KEY},
        )

        first_user_exists = await db.scalar(select(User.id).limit(1))
        if first_user_exists is not None:
            raise ValueError("BOOTSTRAP_DISABLED")

        organisation = Organisation(name="Primary Organisation")
        db.add(organisation)
        await db.flush()

        user = User(
            org_id=organisation.id,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

    return user


async def create_user(
    *,
    org_id: UUID,
    email: str,
    password: str,
    role: UserRole,
    db: AsyncSession,
    full_name: str | None = None,
    is_active: bool = True,
) -> User:
    if role not in {UserRole.CAMPAIGN_MANAGER, UserRole.VIEWER}:
        raise ValueError("INVALID_ROLE_ASSIGNMENT")

    existing_user = await db.scalar(select(User.id).where(User.email == email).limit(1))
    if existing_user is not None:
        raise ValueError("DUPLICATE_EMAIL")

    user = User(
        org_id=org_id,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def list_users(
    *,
    org_id: UUID,
    limit: int,
    offset: int,
    db: AsyncSession,
) -> tuple[list[User], int]:
    total = await db.scalar(select(func.count()).select_from(User).where(User.org_id == org_id))
    users_result = await db.execute(
        select(User)
        .where(User.org_id == org_id)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    users = list(users_result.scalars().all())
    return users, int(total or 0)
