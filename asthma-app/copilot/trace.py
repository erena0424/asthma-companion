"""Development-only formatting helpers for inspecting LangGraph state updates."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any


def preview_value(
    value: Any,
    *,
    rows: int = 3,
    max_string_chars: int = 900,
) -> Any:
    """Return a JSON-safe preview without dumping an entire prompt or data window."""
    if isinstance(value, dict):
        return {
            str(key): preview_value(
                item,
                rows=rows,
                max_string_chars=max_string_chars,
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        preview = [
            preview_value(
                item,
                rows=rows,
                max_string_chars=max_string_chars,
            )
            for item in value[:rows]
        ]
        remaining = len(value) - rows
        if remaining > 0:
            preview.append(f"... ({remaining} more items)")
        return preview
    if isinstance(value, str) and len(value) > max_string_chars:
        return value[:max_string_chars] + f"... ({len(value) - max_string_chars} more characters)"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def format_stage_update(
    node_name: str,
    update: dict[str, Any],
    *,
    rows: int = 3,
    max_string_chars: int = 900,
) -> str:
    """Format one LangGraph `stream_mode="updates"` event for terminal output."""
    preview = preview_value(
        update,
        rows=max(1, rows),
        max_string_chars=max(80, max_string_chars),
    )
    heading = f"NODE: {node_name}"
    return (
        f"\n{'=' * 88}\n"
        f"{heading}\n"
        f"Fields written: {', '.join(update) or '(none)'}\n"
        f"{'-' * 88}\n"
        f"{json.dumps(preview, indent=2, ensure_ascii=False, default=str)}"
    )
