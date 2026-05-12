from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "m3_template_fix"
down_revision: str | None = "m2_contacts"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "templates",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        existing_server_default="now()",
    )


def downgrade() -> None:
    op.alter_column(
        "templates",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        existing_server_default="now()",
    )