from __future__ import annotations

import secrets
from uuid import UUID

from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TokenType
from app.models.tracking import TrackingToken


async def create_tracking_tokens(
    contact_id: UUID,
    campaign_id: UUID,
    links: list[str],
    db: AsyncSession,
) -> dict[str, object]:
    open_token = secrets.token_urlsafe(16)
    unsub_token = secrets.token_urlsafe(16)
    db.add(
        TrackingToken(
            token=open_token,
            contact_id=contact_id,
            campaign_id=campaign_id,
            token_type=TokenType.OPEN,
        )
    )
    db.add(
        TrackingToken(
            token=unsub_token,
            contact_id=contact_id,
            campaign_id=campaign_id,
            token_type=TokenType.UNSUBSCRIBE,
        )
    )
    click_tokens: dict[str, str] = {}
    for url in links:
        token = secrets.token_urlsafe(16)
        db.add(
            TrackingToken(
                token=token,
                contact_id=contact_id,
                campaign_id=campaign_id,
                token_type=TokenType.CLICK,
                target_url=url,
            )
        )
        click_tokens[url] = token
    await db.commit()
    return {
        "open_token": open_token,
        "unsub_token": unsub_token,
        "click_tokens": click_tokens,
    }


def extract_links_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links: set[str] = set()
    for tag in soup.find_all("a", href=True):
        href = str(tag["href"])
        if href.startswith("http") and "unsubscribe" not in href:
            links.add(href)
    return list(links)


def inject_tracking_into_html(
    html: str,
    open_token: str,
    click_tokens: dict[str, str],
    base_url: str,
) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("a", href=True):
        url = str(tag["href"])
        if url in click_tokens:
            tag["href"] = f"{base_url}/track/click?t={click_tokens[url]}"
    pixel = soup.new_tag(
        "img",
        src=f"{base_url}/track/open?t={open_token}",
        width="1",
        height="1",
        style="display:none",
        alt="",
    )
    body = soup.find("body")
    if body:
        body.append(pixel)
    return str(soup)


def inject_unsubscribe_link(html: str, unsub_token: str, base_url: str) -> str:
    return html.replace(
        "{{unsubscribe_url}}",
        f"{base_url}/unsubscribe?t={unsub_token}",
    )
