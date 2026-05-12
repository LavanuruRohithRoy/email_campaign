from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_role
from app.models.core import User
from app.routers.common import value_error_to_http_exception
from app.schemas.template import (
    ImageUploadResponse,
    TemplateCreate,
    TemplateListResponse,
    TemplateResponse,
    TemplateSummaryResponse,
    TemplateUpdate,
)
from app.services.template_service import (
    create_template,
    delete_template,
    duplicate_template,
    get_template,
    get_templates,
    seed_starter_templates,
    update_template,
)
from app.utils.s3 import upload_image_to_s3

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "templates"}


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> TemplateListResponse:
    templates, total = await get_templates(current_user.org_id, category, search, limit, offset, db)
    return TemplateListResponse(
        items=[TemplateSummaryResponse.model_validate(template) for template in templates],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_new_template(
    payload: TemplateCreate,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    template = await create_template(current_user.org_id, payload, db)
    return TemplateResponse.model_validate(template)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template_by_id(
    template_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    try:
        template = await get_template(current_user.org_id, template_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return TemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_existing_template(
    template_id: UUID,
    payload: TemplateUpdate,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    try:
        template = await update_template(current_user.org_id, template_id, payload, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_template(
    template_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await delete_template(current_user.org_id, template_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{template_id}/duplicate", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_existing_template(
    template_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    try:
        template = await duplicate_template(current_user.org_id, template_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return TemplateResponse.model_validate(template)


@router.post("/upload-asset", response_model=ImageUploadResponse)
async def upload_asset(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
) -> ImageUploadResponse:
    allowed_content_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_content_types:
        raise value_error_to_http_exception(ValueError("INVALID_FILE_TYPE"))
    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise value_error_to_http_exception(ValueError("FILE_TOO_LARGE"))
    url = await upload_image_to_s3(file_bytes, file.content_type)
    return ImageUploadResponse(url=url)


@router.post("/seed")
async def seed_templates_endpoint(
    current_user: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    await seed_starter_templates(current_user.org_id, db)
    return {"seeded": True}
