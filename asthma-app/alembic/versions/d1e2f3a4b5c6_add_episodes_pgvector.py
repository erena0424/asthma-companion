"""Add episodes table with pgvector + full-text search.

Revision ID: d1e2f3a4b5c6
Revises: c8d9e0f1a2b3
Create Date: 2026-07-27 14:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "episodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("episode_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="retrospective"),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("search_tsv", postgresql.TSVECTOR(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "episode_date", name="uq_episodes_user_date"),
    )
    op.create_index("ix_episodes_user_date", "episodes", ["user_id", "episode_date"])
    op.create_index("ix_episodes_search_tsv", "episodes", ["search_tsv"], postgresql_using="gin")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_episodes_embedding_hnsw "
        "ON episodes USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_episodes_embedding_hnsw")
    op.drop_index("ix_episodes_search_tsv", table_name="episodes")
    op.drop_index("ix_episodes_user_date", table_name="episodes")
    op.drop_table("episodes")
