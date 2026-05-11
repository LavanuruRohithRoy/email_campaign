from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.tracking_service import record_click, record_open

router = APIRouter(tags=["Tracking"])

# 1x1 transparent PNG bytes.
TRACKING_PIXEL = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "tracking"}


@router.get("/open")
async def track_open(t: str, request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    await record_open(t, ip, user_agent, db)
    return Response(
        content=TRACKING_PIXEL,
        media_type="image/png",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get("/click")
async def track_click(t: str, request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    target_url = await record_click(t, ip, user_agent, db)
    if not target_url:
        return RedirectResponse(url="/", status_code=302)
    return RedirectResponse(url=target_url, status_code=302)
