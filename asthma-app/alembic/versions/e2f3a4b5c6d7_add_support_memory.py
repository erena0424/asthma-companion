"""One optional user-approved support summary; no automatic extraction."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("support_memory", postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column("users", "support_memory")
