from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaigns import Campaign, Template
from app.schemas.template import TemplateCreate, TemplateUpdate


def _starter_design(name: str, body_html: str) -> dict[str, object]:
    return {
        "schemaVersion": 11,
        "counters": {"u_row": 1, "u_column": 1, "u_text": 1, "u_button": 1, "u_divider": 1},
        "body": {
            "rows": [],
            "values": {
                "backgroundColor": "#f6f9fc",
                "contentWidth": "600px",
                "fontFamily": {"label": "Arial", "value": "arial,helvetica,sans-serif"},
                "name": name,
                "body": body_html,
            },
        },
    }


async def get_templates(
    org_id: UUID,
    category: str | None,
    search: str | None,
    limit: int,
    offset: int,
    db: AsyncSession,
) -> tuple[list[Template], int]:
    query = select(Template).where(Template.org_id == org_id)
    count_query = select(func.count(Template.id)).where(Template.org_id == org_id)

    if category:
        query = query.where(Template.category == category)
        count_query = count_query.where(Template.category == category)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(Template.name.ilike(term))
        count_query = count_query.where(Template.name.ilike(term))

    query = query.order_by(Template.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    total = int((await db.execute(count_query)).scalar_one())
    return list(result.scalars().all()), total


async def get_template(org_id: UUID, template_id: UUID, db: AsyncSession) -> Template:
    result = await db.execute(
        select(Template).where(Template.id == template_id, Template.org_id == org_id)
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise ValueError("NOT_FOUND")
    return template


async def create_template(org_id: UUID, data: TemplateCreate, db: AsyncSession) -> Template:
    template = Template(
        org_id=org_id,
        name=data.name,
        category=data.category,
        blocks=deepcopy(data.blocks),
        html=data.html,
        thumbnail_url=data.thumbnail_url,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def update_template(org_id: UUID, template_id: UUID, data: TemplateUpdate, db: AsyncSession) -> Template:
    template = await get_template(org_id, template_id, db)
    if data.name is not None:
        template.name = data.name
    if data.category is not None:
        template.category = data.category
    if data.blocks is not None:
        template.blocks = deepcopy(data.blocks)
    if data.html is not None:
        template.html = data.html
    if data.thumbnail_url is not None:
        template.thumbnail_url = data.thumbnail_url
    await db.commit()
    await db.refresh(template)
    return template


async def delete_template(org_id: UUID, template_id: UUID, db: AsyncSession) -> None:
    template = await get_template(org_id, template_id, db)
    reference = await db.execute(select(Campaign.id).where(Campaign.template_id == template.id).limit(1))
    if reference.scalar_one_or_none() is not None:
        raise ValueError("TEMPLATE_IN_USE")
    await db.delete(template)
    await db.commit()


async def duplicate_template(org_id: UUID, template_id: UUID, db: AsyncSession) -> Template:
    original = await get_template(org_id, template_id, db)
    duplicate = Template(
        org_id=org_id,
        name=f"{original.name} (Copy)",
        category=original.category,
        blocks=deepcopy(original.blocks),
        html=original.html,
        thumbnail_url=None,
    )
    db.add(duplicate)
    await db.commit()
    await db.refresh(duplicate)
    return duplicate


def _starter_templates(org_id: UUID) -> list[Template]:
    starter_content = [
        {
            "name": "Welcome to [Company]",
            "category": "Welcome",
            "html": """
<div style=\"font-family: Arial, sans-serif; background-color: #f6f9fc; padding: 32px; color: #1f2937;\">
  <div style=\"max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px;\">
    <h1 style=\"margin: 0 0 16px; font-size: 28px;\">Welcome, {{first_name}}!</h1>
    <p style=\"margin: 0 0 16px; line-height: 1.6;\">We’re glad you’re here. Your journey starts now.</p>
    <p style=\"margin: 0; font-size: 13px; color: #6b7280;\">Unsubscribe anytime.</p>
  </div>
</div>
""",
        },
        {
            "name": "Monthly Newsletter",
            "category": "Newsletter",
            "html": """
<div style=\"font-family: Arial, sans-serif; padding: 32px; background-color: #f8fafc;\">
  <div style=\"max-width: 600px; margin: 0 auto; background: #fff; padding: 32px;\">
    <h1 style=\"margin-top: 0;\">This Month’s Highlights</h1>
    <p style=\"line-height: 1.6;\">Hello {{first_name}}, here are the latest updates from our team.</p>
    <p style=\"font-size: 13px; color: #6b7280;\">Unsubscribe anytime.</p>
  </div>
</div>
""",
        },
        {
            "name": "Promotional Offer",
            "category": "Promotional",
            "html": """
<div style=\"font-family: Arial, sans-serif; background:#fff7ed; padding:32px;\">
  <div style=\"max-width: 600px; margin:0 auto; background:#ffffff; padding:32px; border:1px solid #fed7aa;\">
    <h1 style=\"margin-top:0;\">Limited Time Offer</h1>
    <p style=\"line-height:1.6;\">Hi {{first_name}}, enjoy a special discount for a short time only.</p>
    <a href=\"#\" style=\"display:inline-block; background:#ea580c; color:#fff; padding:12px 20px; text-decoration:none; border-radius:8px;\">Shop Now</a>
    <p style=\"font-size:13px; color:#6b7280; margin-top:24px;\">Unsubscribe anytime.</p>
  </div>
</div>
""",
        },
        {
            "name": "Event Invite",
            "category": "Event Invite",
            "html": """
<div style=\"font-family: Arial, sans-serif; padding: 32px; background:#eff6ff;\">
  <div style=\"max-width:600px; margin:0 auto; background:#fff; padding:32px;\">
    <h1 style=\"margin-top:0;\">You’re Invited</h1>
    <p style=\"line-height:1.6;\">Join us on {{event_date}} at {{event_time}} in {{event_location}}.</p>
    <a href=\"#\" style=\"display:inline-block; background:#2563eb; color:#fff; padding:12px 20px; text-decoration:none; border-radius:8px;\">RSVP</a>
    <p style=\"font-size:13px; color:#6b7280; margin-top:24px;\">Unsubscribe anytime.</p>
  </div>
</div>
""",
        },
        {
            "name": "Training Notice",
            "category": "Training Notice",
            "html": """
<div style=\"font-family: Arial, sans-serif; padding: 32px; background:#f0fdf4;\">
  <div style=\"max-width:600px; margin:0 auto; background:#fff; padding:32px;\">
    <h1 style=\"margin-top:0;\">Training Schedule</h1>
    <p style=\"line-height:1.6;\">Hello {{first_name}}, please review the schedule below before the session.</p>
    <table style=\"width:100%; border-collapse:collapse;\">
      <tr><td style=\"padding:8px 0; border-bottom:1px solid #e5e7eb;\">Date</td><td style=\"padding:8px 0; border-bottom:1px solid #e5e7eb;\">{{training_date}}</td></tr>
      <tr><td style=\"padding:8px 0; border-bottom:1px solid #e5e7eb;\">Time</td><td style=\"padding:8px 0; border-bottom:1px solid #e5e7eb;\">{{training_time}}</td></tr>
      <tr><td style=\"padding:8px 0;\">Contact</td><td style=\"padding:8px 0;\">{{contact_email}}</td></tr>
    </table>
    <p style=\"font-size:13px; color:#6b7280; margin-top:24px;\">Unsubscribe anytime.</p>
  </div>
</div>
""",
        },
    ]

    return [
        Template(
            org_id=org_id,
            name=template_data["name"],
            category=template_data["category"],
            blocks=_starter_design(template_data["name"], template_data["html"]),
            html=template_data["html"],
            thumbnail_url=None,
        )
        for template_data in starter_content
    ]


async def seed_starter_templates(org_id: UUID, db: AsyncSession) -> None:
    result = await db.execute(select(func.count(Template.id)).where(Template.org_id == org_id))
    if int(result.scalar_one()) > 0:
        return
    db.add_all(_starter_templates(org_id))
    await db.commit()