from __future__ import annotations

from alembic import op
from collections.abc import Sequence

revision: str = "m5_add_indexes"
down_revision: str | None = "m4_campaign_recipients"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Add indexes useful for analytics and lookups (IF NOT EXISTS)
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_events_campaign_event_type ON email_events (campaign_id, event_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tracking_tokens_token ON tracking_tokens (token);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_suppression_org_email ON suppression_list (org_id, email);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_contacts_org_email ON contacts (org_id, email);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_campaign_sends_campaign_status ON campaign_sends (campaign_id, status);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_email_events_campaign_event_type;")
    op.execute("DROP INDEX IF EXISTS ix_tracking_tokens_token;")
    op.execute("DROP INDEX IF EXISTS ix_suppression_org_email;")
    op.execute("DROP INDEX IF EXISTS ix_contacts_org_email;")
    op.execute("DROP INDEX IF EXISTS ix_campaign_sends_campaign_status;")
