from __future__ import annotations

import difflib

from .types import ActionLog


def format_patch(file_path: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=file_path,
            tofile=file_path,
            lineterm="",
        )
    )


def compose_before_after(sorted_actions: list[ActionLog]) -> tuple[str, str]:
    first = sorted_actions[0]
    last = sorted_actions[-1]
    if last.type == "file_delete":
        return last.details.get("before", ""), ""
    before = "" if first.type == "file_create" else first.details.get("before", "")
    after = last.details.get("after", "")
    return before, after
