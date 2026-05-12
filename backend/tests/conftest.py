from __future__ import annotations

# ruff: noqa: E402

import os
import sys
from pathlib import Path
from collections.abc import AsyncGenerator
import asyncio
import time
from typing import Any

# Ensure the backend root is on sys.path before any app imports.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("APP_ENV", "test")

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import delete

from app.models.campaign_recipients import CampaignRecipient
from app.models.campaigns import Campaign, CampaignSend, Template
from app.models.contacts import Contact, ContactList, ContactListMember, ImportJob, Segment, SuppressionList
from app.models.core import Organisation, User, RefreshToken
from app.models.tracking import EmailEvent, TrackingToken
from app.models.enums import UserRole
from app.utils.security import hash_password

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
async def redis_client() -> AsyncGenerator[Any, None]:
    """Redis fixture that falls back to an in-memory FakeRedis when a real Redis is unavailable."""

    class FakeRedis:
        def __init__(self):
            self._store: dict[str, int] = {}
            self._exp: dict[str, float] = {}
            self._lock = asyncio.Lock()

        async def flushdb(self):
            async with self._lock:
                self._store.clear()
                self._exp.clear()

        async def incr(self, key: str) -> int:
            async with self._lock:
                # expire keys if needed
                now = time.time()
                if key in self._exp and self._exp[key] < now:
                    self._store.pop(key, None)
                    self._exp.pop(key, None)
                val = self._store.get(key, 0) + 1
                self._store[key] = val
                return val

        async def expire(self, key: str, seconds: int) -> None:
            async with self._lock:
                self._exp[key] = time.time() + seconds

        async def delete(self, key: str) -> None:
            async with self._lock:
                self._store.pop(key, None)
                self._exp.pop(key, None)

        async def close(self):
            return None

    # Try connecting to real Redis; if unavailable, use FakeRedis
    try:
        client = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        try:
            await client.ping()
            await client.flushdb()
            yield client
            await client.close()
            return
        except Exception:
            # fallthrough to fake
            try:
                await client.close()
            except Exception:
                pass

    except Exception:
        pass

    fake = FakeRedis()
    await fake.flushdb()
    try:
        yield fake
    finally:
        await fake.close()


@pytest.fixture()
async def seed_user() -> AsyncGenerator[User, None]:
    async with async_session_maker() as session:
        # clean tables
        await session.execute(delete(EmailEvent))
        await session.execute(delete(TrackingToken))
        await session.execute(delete(CampaignSend))
        await session.execute(delete(CampaignRecipient))
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
        await session.execute(delete(CampaignRecipient))
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
