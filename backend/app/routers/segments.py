from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis, require_role
from app.models.core import User
from app.routers.common import value_error_to_http_exception
from app.schemas.contact import SegmentCollectionResponse, SegmentCountResponse, SegmentCreate, SegmentResponse, SegmentUpdate
from app.services import segment_service

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "segments"}

@router.get("", response_model=SegmentCollectionResponse)
async def list_segments(
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> SegmentCollectionResponse:
    segments = await segment_service.get_segments(current_user.org_id, db)
    total = len(segments)
    page = segments[offset : offset + limit]
    return SegmentCollectionResponse(
        items=[SegmentResponse.model_validate(segment) for segment in page],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=SegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_segment(
    payload: SegmentCreate,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> SegmentResponse:
    segment = await segment_service.create_segment(current_user.org_id, payload, db)
    return SegmentResponse.model_validate(segment)


@router.get("/{segment_id}", response_model=SegmentResponse)
async def get_segment(
    segment_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> SegmentResponse:
    try:
        segments = await segment_service.get_segments(current_user.org_id, db)
        for segment in segments:
            if segment.id == segment_id:
                return SegmentResponse.model_validate(segment)
        raise ValueError("NOT_FOUND")
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc


@router.put("/{segment_id}", response_model=SegmentResponse)
async def update_segment(
    segment_id: UUID,
    payload: SegmentUpdate,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> SegmentResponse:
    try:
        segment = await segment_service.update_segment(current_user.org_id, segment_id, payload, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return SegmentResponse.model_validate(segment)


@router.delete("/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(
    segment_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await segment_service.delete_segment(current_user.org_id, segment_id, db)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{segment_id}/count", response_model=SegmentCountResponse)
async def count_segment(
    segment_id: UUID,
    current_user: User = Depends(require_role("super_admin", "campaign_manager", "viewer")),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SegmentCountResponse:
    try:
        count = await segment_service.count_segment(current_user.org_id, segment_id, db, redis)
    except ValueError as exc:
        raise value_error_to_http_exception(exc) from exc
    return SegmentCountResponse(count=count)
