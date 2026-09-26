"""Apply database migrations (Alembic).

Prefer this over SQLAlchemy create_all for local and deployed environments.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    cfg = Config(str(_ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    print("Database migrations applied (alembic upgrade head).")


if __name__ == "__main__":
    main()
