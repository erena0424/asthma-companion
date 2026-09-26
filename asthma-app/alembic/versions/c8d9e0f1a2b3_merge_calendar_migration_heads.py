"""Merge diverged calendar migration heads.

b7e8f9a0c1d2 and b7f3a1c9d2e4 both descended from 36c402e69a90 after parallel
branch work (profile image + calendar vs calendar-only). This empty merge
restores a single Alembic head so `alembic upgrade head` works for everyone.

Revision ID: c8d9e0f1a2b3
Revises: b7e8f9a0c1d2, b7f3a1c9d2e4
Create Date: 2026-07-27 09:40:00.000000

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = ("b7e8f9a0c1d2", "b7f3a1c9d2e4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
