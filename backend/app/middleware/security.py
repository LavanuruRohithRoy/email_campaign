"""
Security headers and hardening middleware for the email campaign platform.

Provides:
- Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
- Trusted hosts middleware
- Request size limits
- CSP (Content-Security-Policy) header
- HSTS (HTTP Strict-Transport-Security) for production
"""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security-related HTTP headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        # Restrict resource loading to same origin, inline scripts in specific cases
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Allow inline for frontend app
            "style-src 'self' 'unsafe-inline'; "  # Allow inline styles for shadcn/tailwind
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "  # Restrict API calls to same origin
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp

        # HSTS for production only (forces HTTPS)
        if settings.is_production():
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Disable caching for sensitive endpoints
        if _is_sensitive_endpoint(request.url.path):
            response.headers["Cache-Control"] = (
                "private, no-cache, no-store, must-revalidate"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        # Disable browser caching of sensitive responses
        if request.url.path.startswith("/api/v1/auth") or request.url.path.startswith(
            "/api/v1/settings"
        ):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

        return response


class TrustedHostsMiddleware(BaseHTTPMiddleware):
    """Middleware that validates the Host header against allowed hosts."""

    def __init__(self, app, allowed_hosts: list[str] | None = None):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or self._extract_hosts_from_allowed_origins()

    def _extract_hosts_from_allowed_origins(self) -> list[str]:
        """Extract hosts from ALLOWED_ORIGINS config."""
        hosts = set()
        for origin in settings.ALLOWED_ORIGINS:
            # Extract host from origin URL (e.g., "http://localhost:5173" -> "localhost")
            try:
                from urllib.parse import urlparse

                parsed = urlparse(origin)
                if parsed.hostname:
                    hosts.add(parsed.hostname)
            except Exception:
                pass

        # Always add common localhost variants
        hosts.add("localhost")
        hosts.add("127.0.0.1")

        # Add APP_BASE_URL host
        try:
            from urllib.parse import urlparse

            parsed = urlparse(settings.APP_BASE_URL)
            if parsed.hostname:
                hosts.add(parsed.hostname)
        except Exception:
            pass

        return list(hosts)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate Host header if running in production."""
        if settings.is_production():
            host = request.headers.get("host", "").split(":")[0]

            if host and host not in self.allowed_hosts:
                logger.warning(
                    f"Rejected request with suspicious host header: {host}",
                    extra={"request_id": request.headers.get("X-Request-ID", "unknown")},
                )
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=400,
                    content={
                        "error": {
                            "code": "INVALID_HOST",
                            "message": "Invalid host header",
                        }
                    },
                )

        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces request size limits."""

    # Max request body size: 10MB
    MAX_REQUEST_SIZE = 10 * 1024 * 1024

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check request size before processing."""
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                content_length_int = int(content_length)
                if content_length_int > self.MAX_REQUEST_SIZE:
                    logger.warning(
                        f"Request size {content_length_int} exceeds limit {self.MAX_REQUEST_SIZE}",
                        extra={
                            "request_id": request.headers.get("X-Request-ID", "unknown"),
                            "method": request.method,
                            "path": request.url.path,
                        },
                    )
                    from fastapi.responses import JSONResponse

                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Request size exceeds {self.MAX_REQUEST_SIZE // (1024*1024)}MB limit",
                            }
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)


def _is_sensitive_endpoint(path: str) -> bool:
    """Check if endpoint should not be cached."""
    sensitive_prefixes = [
        "/api/v1/auth",
        "/api/v1/contacts",
        "/api/v1/campaigns",
        "/api/v1/templates",
        "/api/v1/analytics",
        "/api/v1/settings",
    ]
    return any(path.startswith(prefix) for prefix in sensitive_prefixes)
