"""
Request and error handling middleware for the email campaign platform.

Provides:
- Request ID injection
- Global exception handling
- Standardized error responses
- Request/response logging
- Timeout handling
"""

import contextvars
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

# Context variable for request ID tracking
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)


async def get_request_id() -> str:
    """Get the current request ID from context."""
    request_id = request_id_ctx.get()
    if not request_id:
        request_id = str(uuid.uuid4())
        request_id_ctx.set(request_id)
    return request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that injects request IDs into all requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request and response headers."""
        # Generate or retrieve request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_ctx.set(request_id)

        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response information."""
        request_id = request_id_ctx.get() or str(uuid.uuid4())
        
        # Record request start time
        start_time = time.time()

        # Skip logging for health checks to reduce noise
        if request.url.path in ["/health/live", "/health/ready"]:
            response = await call_next(request)
            return response

        # Create logger with request ID context
        log_extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_host": request.client.host if request.client else "unknown",
        }

        logger.info(
            f"{request.method} {request.url.path} started",
            extra=log_extra,
        )

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            log_extra["status_code"] = response.status_code
            log_extra["duration_ms"] = round(duration * 1000, 2)

            logger.info(
                f"{request.method} {request.url.path} completed "
                f"({response.status_code}) in {log_extra['duration_ms']}ms",
                extra=log_extra,
            )

            return response

        except Exception as exc:
            duration = time.time() - start_time
            log_extra["duration_ms"] = round(duration * 1000, 2)
            log_extra["error"] = str(exc)

            logger.error(
                f"{request.method} {request.url.path} failed after "
                f"{log_extra['duration_ms']}ms: {exc}",
                extra=log_extra,
                exc_info=True,
            )
            raise


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    """Middleware for global exception handling and standardized error responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle exceptions and return standardized error responses."""
        try:
            response = await call_next(request)
            return response

        except RequestValidationError as exc:
            """Handle Pydantic validation errors."""
            request_id = request_id_ctx.get() or str(uuid.uuid4())
            logger.warning(
                f"Validation error on {request.method} {request.url.path}",
                extra={"request_id": request_id, "errors": exc.errors()},
            )

            error_details = []
            for error in exc.errors():
                field = ".".join(str(x) for x in error["loc"][1:])
                error_details.append({"field": field, "message": error["msg"]})

            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "details": error_details,
                    }
                },
                headers={"X-Request-ID": request_id},
            )

        except ValueError as exc:
            """Handle value errors with 400 Bad Request."""
            request_id = request_id_ctx.get() or str(uuid.uuid4())
            logger.warning(
                f"Bad request on {request.method} {request.url.path}: {exc}",
                extra={"request_id": request_id},
            )

            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": str(exc),
                    }
                },
                headers={"X-Request-ID": request_id},
            )

        except TimeoutError:
            """Handle timeout errors with 504 Gateway Timeout."""
            request_id = request_id_ctx.get() or str(uuid.uuid4())
            logger.error(
                f"Request timeout on {request.method} {request.url.path}",
                extra={"request_id": request_id},
            )

            return JSONResponse(
                status_code=504,
                content={
                    "error": {
                        "code": "REQUEST_TIMEOUT",
                        "message": "Request processing timeout",
                    }
                },
                headers={"X-Request-ID": request_id},
            )

        except Exception as exc:
            """Handle all other exceptions with 500 Internal Server Error."""
            request_id = request_id_ctx.get() or str(uuid.uuid4())
            logger.error(
                f"Unhandled exception on {request.method} {request.url.path}: {exc}",
                extra={"request_id": request_id},
                exc_info=True,
            )

            # Don't expose internal error details in production
            error_message = "Internal server error"
            if settings.is_development() or settings.is_test():
                error_message = str(exc)

            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": error_message,
                    }
                },
                headers={"X-Request-ID": request_id},
            )


async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    """Standalone function to inject request ID (can be used as dependency)."""
    return await RequestIDMiddleware(app=call_next).dispatch(request, call_next)
