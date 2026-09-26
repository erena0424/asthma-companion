"""Add calendar sync and user preference columns (formerly ad-hoc ALTER in init_db).

Revision ID: b7e8f9a0c1d2
Revises: a1b2c3d4e5f6
Create Date: 2026-07-26 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e8f9a0c1d2"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# IF NOT EXISTS so DBs that already got these via the old create_all/_migrate_schema path
# can still advance alembic_version without failing.
_UPGRADE_STATEMENTS = (
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS emergency_contacts JSONB DEFAULT '[]'::jsonb",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS symptoms TEXT[]",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS tracking TEXT[]",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_calendar_refresh_token TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_calendar_email VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_calendar_connected_at TIMESTAMPTZ",
    "ALTER TABLE check_ins ADD COLUMN IF NOT EXISTS calendar_events JSONB",
    "ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS calendar_events JSONB",
)


def upgrade() -> None:
    for stmt in _UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    op.execute("ALTER TABLE forecasts DROP COLUMN IF EXISTS calendar_events")
    op.execute("ALTER TABLE check_ins DROP COLUMN IF EXISTS calendar_events")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS google_calendar_connected_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS google_calendar_email")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS google_calendar_refresh_token")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS tracking")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS symptoms")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS emergency_contacts")
