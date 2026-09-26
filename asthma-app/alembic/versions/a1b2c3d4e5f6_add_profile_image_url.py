"""Add users.profile_image_url for Cloudinary (or other CDN) avatars.

Revision ID: a1b2c3d4e5f6
Revises: 36c402e69a90
Create Date: 2026-07-24 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "36c402e69a90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image_url VARCHAR(2048)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS profile_image_url")
