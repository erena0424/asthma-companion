"""Tests for compact, development-only Copilot stage previews."""

from copilot.trace import format_stage_update, preview_value


def test_preview_value_limits_rows_and_long_strings():
    preview = preview_value(
        {
            "episodes": [{"date": index} for index in range(5)],
            "prompt": "x" * 120,
        },
        rows=2,
        max_string_chars=80,
    )

    assert preview["episodes"] == [
        {"date": 0},
        {"date": 1},
        "... (3 more items)",
    ]
    assert preview["prompt"].startswith("x" * 80)
    assert preview["prompt"].endswith("(40 more characters)")


def test_format_stage_update_names_node_and_fields():
    output = format_stage_update(
        "history",
        {
            "history": {"episodes": [{"date": "2026-07-16"}]},
            "_history_analysis_pool": [],
        },
        rows=1,
    )

    assert "NODE: history" in output
    assert "Fields written: history, _history_analysis_pool" in output
    assert '"date": "2026-07-16"' in output
