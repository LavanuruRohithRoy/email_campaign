from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict

import bleach
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaigns import Template
from app.utils.ses import send_email_via_ses
from app.config import settings

logger = logging.getLogger(__name__)


# Build a conservative allowlist for email HTML
ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + ["table", "thead", "tbody", "tr", "td", "th", "span", "div", "img"]
ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "img": ["src", "alt", "width", "height", "style"],
    "td": ["style"],
    "th": ["style"],
    "table": ["style", "cellpadding", "cellspacing"],
    "a": ["href", "title", "style"],
    "*": ["style"],
}


async def sanitize_template_html(html: str) -> str:
    """Sanitize HTML for safe email rendering."""
    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )
    return cleaned


async def render_merge_tags(html: str, data: Dict[str, str] | None = None) -> str:
    """Render merge tags in HTML with provided sample data.

    Supported tags: {{first_name}}, {{last_name}}, {{email}}, {{company}}, {{unsubscribe_url}}
    Missing values are replaced with an empty string.
    """
    if data is None:
        data = {}
    substitutions = {
        "first_name": data.get("first_name", "") or "",
        "last_name": data.get("last_name", "") or "",
        "email": data.get("email", "") or "",
        "company": data.get("company", "") or "",
        "unsubscribe_url": data.get("unsubscribe_url", "") or "",
    }
    rendered = html
    for key, val in substitutions.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(val))
    return rendered


async def save_template_version(template: Template, design_json: dict, html: str, is_draft: bool, db: AsyncSession) -> dict:
    """Save a new version inside the Template.blocks JSON to avoid schema changes.

    This appends a versions array to Template.blocks['_versions'] and updates html and blocks.
    """
    now = datetime.utcnow()
    blocks = dict(template.blocks or {})
    meta = blocks.get("_meta", {})
    version = meta.get("version", 1)
    version += 1
    versions = blocks.get("_versions", [])
    versions.append({"version": version, "created_at": now.isoformat(), "design_json": design_json, "html": html})
    blocks["_versions"] = versions
    meta["version"] = version
    blocks["_meta"] = meta

    template.blocks = blocks
    template.html = html
    await db.commit()
    await db.refresh(template)
    return {"id": template.id, "version": version, "created_at": now}


async def send_test_email(org_id, request, current_user, db: AsyncSession, redis: Redis | None = None):
    """Sanitize, render merge tags with sample data and send a test email via SES.

    Enforces a Redis-backed rate limit of `MAX_TEST_EMAILS_PER_HOUR` per user when a Redis client is provided.
    """
    # Rate limiting (per-user)
    if redis is not None:
        key = f"test_email:{current_user.id}"
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 3600)
            max_allowed = 10
            if count > max_allowed:
                raise ValueError("RATE_LIMIT_EXCEEDED")
        except ValueError:
            raise
        except Exception as exc:
            # If Redis check fails unexpectedly, fail closed for safety.
            logger.warning("Redis rate limit check failed: %s", exc)
            raise ValueError("RATE_LIMIT_UNAVAILABLE") from exc

    # Basic sanitization and merge rendering with sensible sample data
    html = await sanitize_template_html(request.html_content)
    rendered = await render_merge_tags(
        html,
        {"first_name": "Test", "last_name": "User", "email": request.to_email, "unsubscribe_url": ""},
    )

    # Send via SES
    message_id = await send_email_via_ses(
        to_address=request.to_email,
        from_address=current_user.email,
        from_name=current_user.full_name or "Test Sender",
        reply_to=None,
        subject=request.subject,
        html_body=rendered,
        configuration_set=settings.AWS_SES_CONFIG_SET or "",
    )
    logger.info("Sent test email message_id=%s user=%s org=%s", message_id, current_user.id, org_id)
    return message_id
