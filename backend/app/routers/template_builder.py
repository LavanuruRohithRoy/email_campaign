from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.dependencies import get_db, require_role, get_redis
from app.models.campaigns import Template
from app.schemas.template_builder import (
    TemplateBuilderSaveRequest,
    TemplatePreviewRequest,
    TestEmailRequest,
    TemplateVersionResponse,
)
from app.services.template_builder_service import (
    sanitize_template_html,
    render_merge_tags,
    save_template_version,
    send_test_email,
)
from app.services.template_service import create_template, get_template
from app.models.core import User

router = APIRouter()


@router.post("/save")
async def save_builder_template(
    payload: TemplateBuilderSaveRequest,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    # create a Template using existing service and store design in blocks
    template = await create_template(
        current_user.org_id,
        type("T", (), {"name": payload.name, "category": None, "blocks": payload.design_json, "html": payload.html_content, "thumbnail_url": None}),
        db,
    )
    # also record a version
    await save_template_version(template, payload.design_json, payload.html_content, payload.is_draft, db)
    return {"id": str(template.id), "status": "saved"}


@router.post("/preview")
async def preview_template(
    payload: TemplatePreviewRequest,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    sanitized = await sanitize_template_html(payload.html_content)
    rendered = await render_merge_tags(sanitized, payload.sample_data)
    return {"html": rendered}


@router.post("/test-email")
async def test_email(
    payload: TestEmailRequest,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
) -> dict[str, str]:
    try:
        message_id = await send_test_email(current_user.org_id, payload, current_user, db, redis)
    except ValueError as exc:
        code = str(exc)
        if code == "RATE_LIMIT_EXCEEDED":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"detail": "Test email rate limit exceeded", "code": code},
            ) from exc
        if code == "RATE_LIMIT_UNAVAILABLE":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"detail": "Rate limiter unavailable", "code": code},
            ) from exc
        raise
    return {"message_id": message_id}


@router.get("/{template_id}/versions", response_model=List[TemplateVersionResponse])
async def list_versions(
    template_id: str,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> List[TemplateVersionResponse]:
    try:
        template = await get_template(current_user.org_id, template_id, db)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")
    blocks = template.blocks or {}
    versions = blocks.get("_versions", [])
    result: List[TemplateVersionResponse] = []
    for ver in versions:
        result.append(TemplateVersionResponse(id=template.id, version=ver.get("version"), created_at=ver.get("created_at")))
    return result


@router.post("/{template_id}/restore/{version}")
async def restore_version(
    template_id: str,
    version: int,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        template = await get_template(current_user.org_id, template_id, db)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND")
    blocks = template.blocks or {}
    versions = blocks.get("_versions", [])
    match = None
    for ver in versions:
        if ver.get("version") == version:
            match = ver
            break
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VERSION_NOT_FOUND")
    # apply
    template.blocks = match.get("design_json") or template.blocks
    template.html = match.get("html") or template.html
    await db.commit()
    await db.refresh(template)
    return {"id": str(template.id), "version": version, "status": "restored"}
