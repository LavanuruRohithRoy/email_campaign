from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import settings
from app.core.logging import setup_logging
from app.middleware.request_error import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    GlobalExceptionMiddleware,
)
from app.middleware.security import (
    SecurityHeadersMiddleware,
    TrustedHostsMiddleware,
    RequestSizeLimitMiddleware,
)
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
from app.routers.health import router as health_router

# Initialize structured logging
setup_logging()
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

# Standardize Pydantic/Request validation errors to use our error shape
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.middleware.request_error import request_id_middleware, request_id_ctx


async def _validation_exception_handler(request, exc: RequestValidationError):
    request_id = request.headers.get("X-Request-ID") or request_id_ctx.get("") or ""
    logging.getLogger("app.middleware.request_error").warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={"request_id": request_id, "errors": exc.errors()},
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": [
                    {"field": ".".join(str(x) for x in err["loc"][1:]), "message": err["msg"]}
                    for err in exc.errors()
                ],
            }
        },
        headers={"X-Request-ID": request_id},
    )


app.add_exception_handler(RequestValidationError, _validation_exception_handler)

# Add middleware in reverse order (they execute in reverse order)
# Request size limit (must be first to reject oversized requests early)
app.add_middleware(RequestSizeLimitMiddleware)

# Global exception handling (catches all exceptions)
app.add_middleware(GlobalExceptionMiddleware)

# Request logging (after exceptions, logs all requests)
app.add_middleware(RequestLoggingMiddleware)

# Request ID injection
app.add_middleware(RequestIDMiddleware)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Trusted hosts validation
app.add_middleware(TrustedHostsMiddleware)

# CORS handling
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
app.include_router(health_router)
app.include_router(health_router, prefix="/api/v1")
app.include_router(tracking_router, prefix="/track", tags=["tracking"])
app.include_router(unsubscribe_router, prefix="/unsubscribe", tags=["unsubscribe"])
app.include_router(preferences_router, prefix="/preferences", tags=["preferences"])
