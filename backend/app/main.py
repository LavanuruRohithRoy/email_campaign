from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import settings
from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.campaigns import router as campaigns_router
from app.routers.contacts import router as contacts_router
from app.routers.lists import router as lists_router
from app.routers.preferences import router as preferences_router
from app.routers.segments import router as segments_router
from app.routers.templates import router as templates_router
from app.routers.template_builder import router as template_builder_router
from app.routers.tracking import router as tracking_router
from app.routers.unsubscribe import router as unsubscribe_router
from app.routers.webhooks import router as webhooks_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting up")
    redis_client = Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    await redis_client.ping()
    await redis_client.close()
    yield
    logger.info("shutting down")


app = FastAPI(title="Email Campaign Platform", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(contacts_router, prefix="/api/v1/contacts", tags=["contacts"])
app.include_router(lists_router, prefix="/api/v1/lists", tags=["lists"])
app.include_router(segments_router, prefix="/api/v1/segments", tags=["segments"])
app.include_router(templates_router, prefix="/api/v1/templates", tags=["templates"])
app.include_router(template_builder_router, prefix="/api/v1/templates/builder", tags=["templates","builder"])
app.include_router(campaigns_router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(webhooks_router)
app.include_router(webhooks_router, prefix="/api/v1")
app.include_router(tracking_router, prefix="/track", tags=["tracking"])
app.include_router(unsubscribe_router, prefix="/unsubscribe", tags=["unsubscribe"])
app.include_router(preferences_router, prefix="/preferences", tags=["preferences"])
