"""
Structured logging configuration for the email campaign platform.

Provides:
- JSON logging in production
- Readable logging in development
- Request ID tracking
- Secret redaction
- Worker context injection
"""

import json
import logging
import logging.config
import re
import sys
import uuid
from typing import Any

from app.config import settings


class SecretRedactorFormatter(logging.Formatter):
    """Log formatter that redacts sensitive information."""

    # Patterns to redact
    SECRET_PATTERNS = [
        (r"(password[\"']?\s*:?\s*[\"'])([^\"']+)([\"'])", r"\1***REDACTED***\3"),
        (r"(secret[\"']?\s*:?\s*[\"'])([^\"']+)([\"'])", r"\1***REDACTED***\3"),
        (r"(token[\"']?\s*:?\s*[\"'])([^\"']+)([\"'])", r"\1***REDACTED***\3"),
        (r"(Authorization[\"']?\s*:?\s*[\"'])([^\"']+)([\"'])", r"\1***REDACTED***\3"),
        (r"(api_key[\"']?\s*:?\s*[\"'])([^\"']+)([\"'])", r"\1***REDACTED***\3"),
        (r"(aws_secret[\"']?\s*:?\s*[\"'])([^\"']+)([\"'])", r"\1***REDACTED***\3"),
    ]

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with secret redaction."""
        msg = super().format(record)
        
        # Redact sensitive patterns
        for pattern, replacement in self.SECRET_PATTERNS:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        
        return msg


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request ID if available (from contextvars via middleware)
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id

        # Add campaign ID if available
        if hasattr(record, "campaign_id"):
            log_obj["campaign_id"] = record.campaign_id

        # Add user ID if available
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id

        # Add organization ID if available
        if hasattr(record, "org_id"):
            log_obj["org_id"] = record.org_id

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Redact sensitive fields
        log_obj = self._redact_sensitive_fields(log_obj)

        return json.dumps(log_obj, default=str)

    @staticmethod
    def _redact_sensitive_fields(obj: Any) -> Any:
        """Recursively redact sensitive fields in log objects."""
        if isinstance(obj, dict):
            return {
                k: (
                    "***REDACTED***"
                    if any(
                        secret in k.lower()
                        for secret in ["password", "secret", "token", "key", "credential"]
                    )
                    else JSONFormatter._redact_sensitive_fields(v)
                )
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [JSONFormatter._redact_sensitive_fields(item) for item in obj]
        return obj


def get_logging_config() -> dict:
    """Get logging configuration based on environment."""
    
    base_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": SecretRedactorFormatter,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "json": {
                "()": JSONFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "json" if settings.LOG_FORMAT_JSON else "default",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "formatter": "json" if settings.LOG_FORMAT_JSON else "default",
            },
        },
        "root": {
            "level": settings.LOG_LEVEL,
            "handlers": ["console", "file"] if settings.is_production() else ["console"],
        },
        "loggers": {
            "app": {
                "level": settings.LOG_LEVEL,
                "handlers": ["console", "file"] if settings.is_production() else ["console"],
                "propagate": False,
            },
            "uvicorn": {
                "level": settings.LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy": {
                "level": "WARNING" if settings.is_production() else settings.LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    return base_config


def setup_logging() -> None:
    """Initialize logging configuration."""
    try:
        # Create logs directory if it doesn't exist
        import os
        os.makedirs("logs", exist_ok=True)
    except Exception:
        pass  # Silently fail if directory creation fails

    config = get_logging_config()
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


def get_request_id() -> str:
    """Generate or retrieve a request ID."""
    return str(uuid.uuid4())


class ContextFilter(logging.Filter):
    """
    Logging filter that adds contextual information to log records.
    
    Can be used to inject request IDs, user IDs, campaign IDs, etc.
    """

    def __init__(self, **kwargs):
        super().__init__()
        self.context = kwargs

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True
