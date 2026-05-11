from __future__ import annotations

import os
import sys
from pathlib import Path
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import delete

from app.models.campaigns import Campaign, CampaignSend, Template
from app.models.contacts import Contact, ContactList, ContactListMember, ImportJob, Segment, SuppressionList
from app.models.core import Organisation, User, RefreshToken
from app.models.tracking import EmailEvent, TrackingToken
from app.models.enums import UserRole
from app.utils.security import hash_password

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("APP_ENV", "test")

from app.config import settings
from app.main import app
from app.dependencies import get_db as dependency_get_db, get_redis as dependency_get_redis


# Create a single async engine for tests (StaticPool to avoid connection lifecycle issues)
engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture()
async def redis_client() -> AsyncGenerator[Redis, None]:
    client = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture()
async def seed_user() -> AsyncGenerator[User, None]:
    async with async_session_maker() as session:
        # clean tables
        await session.execute(delete(EmailEvent))
        await session.execute(delete(TrackingToken))
        await session.execute(delete(CampaignSend))
        await session.execute(delete(Campaign))
        await session.execute(delete(Template))
        await session.execute(delete(ImportJob))
        await session.execute(delete(ContactListMember))
        await session.execute(delete(Contact))
        await session.execute(delete(ContactList))
        await session.execute(delete(Segment))
        await session.execute(delete(SuppressionList))
        await session.execute(delete(RefreshToken))
        await session.execute(delete(User))
        await session.execute(delete(Organisation))
        await session.commit()

        org = Organisation(name="Test Org")
        session.add(org)
        await session.flush()

        user = User(
            org_id=org.id,
            email="test@example.com",
            password_hash=hash_password("password123"),
            full_name="Test User",
            role=UserRole.CAMPAIGN_MANAGER,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        yield user

        # cleanup after test
        await session.execute(delete(EmailEvent))
        await session.execute(delete(TrackingToken))
        await session.execute(delete(CampaignSend))
        await session.execute(delete(Campaign))
        await session.execute(delete(Template))
        await session.execute(delete(ImportJob))
        await session.execute(delete(ContactListMember))
        await session.execute(delete(Contact))
        await session.execute(delete(ContactList))
        await session.execute(delete(Segment))
        await session.execute(delete(SuppressionList))
        await session.execute(delete(RefreshToken))
        await session.execute(delete(User))
        await session.execute(delete(Organisation))
        await session.commit()


@pytest.fixture()
async def async_client(db_session: AsyncSession, redis_client: Redis) -> AsyncGenerator[AsyncClient, None]:
    # Override app dependencies to use test fixtures
    async def _override_get_db():
        async with async_session_maker() as session:
            yield session

    async def _override_get_redis():
        yield redis_client

    app.dependency_overrides[dependency_get_db] = _override_get_db
    app.dependency_overrides[dependency_get_redis] = _override_get_redis

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.pop(dependency_get_db, None)
    app.dependency_overrides.pop(dependency_get_redis, None)
