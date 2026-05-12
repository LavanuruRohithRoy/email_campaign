from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.campaigns import Template
from app.models.core import Organisation, User
from app.models.enums import UserRole
from app.utils.security import hash_password
from app.services.template_builder_service import (
    sanitize_template_html,
    render_merge_tags,
    save_template_version,
    send_test_email,
)


@pytest.fixture()
async def m10_seed(db_session) -> dict:
    org = Organisation(name=f"M10 Org {uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    user = User(
        org_id=org.id,
        email=f"m10-admin-{uuid4().hex}@example.com",
        password_hash=hash_password("password123"),
        full_name="M10 Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    template = Template(
        org_id=org.id,
        name="M10 Template",
        category="General",
        blocks={"schemaVersion": 11, "body": {"rows": []}},
        html="<html><body>Hello {{first_name}}</body></html>",
        thumbnail_url=None,
    )
    db_session.add(template)
    await db_session.commit()
    return {"org": org, "user": user, "template": template}


async def test_sanitize_html():
    raw = '<div><script>alert(1)</script><table><tr><td>Hi</td></tr></table></div>'
    cleaned = await sanitize_template_html(raw)
    assert "script" not in cleaned
    assert "<table" in cleaned


async def test_render_merge_tags():
    html = "Hello {{first_name}} {{last_name}} ({{email}})"
    rendered = await render_merge_tags(html, {"first_name": "Alice", "last_name": "Z"})
    assert "Alice" in rendered
    assert "Z" in rendered
    assert "(" in rendered


async def test_save_template_version(db_session, m10_seed):
    template = m10_seed["template"]
    design = {"canvas": {"rows": []}}
    result = await save_template_version(template, design, "<html>v2</html>", True, db_session)
    assert result["version"] >= 2


async def test_send_test_email(monkeypatch, db_session, m10_seed):
    class DummyUser:
        id = m10_seed["user"].id
        email = "no-reply@example.com"
        full_name = "No Reply"

    async def fake_send_email_via_ses(*args, **kwargs):
        return "message-123"

    monkeypatch.setattr("app.services.template_builder_service.send_email_via_ses", fake_send_email_via_ses)

    request = type("Req", (), {"to_email": "test@example.com", "subject": "T", "html_content": "<p>Hello</p>"})
    message_id = await send_test_email(m10_seed["org"].id, request, DummyUser, db_session)
    assert message_id == "message-123"
