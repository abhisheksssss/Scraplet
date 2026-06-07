from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import questionary
from rich.console import Console
from rich.syntax import Syntax

from .diff_view import compose_before_after, format_patch
from .tracker import ActionTracker
from .types import ActionLog


console = Console()


@dataclass
class ReviewGroup:
    label: str
    action_ids: list[str]
    patch: str | None = None


def _group_pending(pending: list[ActionLog]) -> list[ReviewGroup]:
    by_path: dict[str, list[ActionLog]] = defaultdict(list)
    shell_actions: list[ActionLog] = []

    for action in pending:
        if action.type == "tool_execute":
            shell_actions.append(action)
        else:
            by_path[action.path].append(action)

    groups: list[ReviewGroup] = []
    for path, actions in sorted(by_path.items()):
        actions = sorted(actions, key=lambda item: item.timestamp)
        ids = [item.id for item in actions]
        if all(item.type == "folder_create" for item in actions):
            groups.append(ReviewGroup(f"Create folder: {path}", ids))
            continue

        before, after = compose_before_after(actions)
        kinds = ", ".join(sorted({item.type for item in actions}))
        groups.append(
            ReviewGroup(
                label=f"{path} ({kinds})",
                action_ids=ids,
                patch=format_patch(path, before, after),
            )
        )

    for action in shell_actions:
        groups.append(
            ReviewGroup(
                label=f"Shell: {action.details.get('command', '(no command)')}",
                action_ids=[action.id],
            )
        )

    return groups


def approval_summary(pending: list[ActionLog]) -> str:
    lines = ["Staged changes - review before applying", ""]
    for group in _group_pending(pending):
        lines.append(f"- {group.label}")
    lines.extend(["", f"Total: {len(pending)} change(s)"])
    return "\n".join(lines)


def approval_diff(pending: list[ActionLog]) -> str:
    parts = [group.patch for group in _group_pending(pending) if group.patch]
    return "\n\n".join(parts).strip() or "(no diff available)"


def run_approval_flow(tracker: ActionTracker) -> bool:
    pending = tracker.get_pending_mutations()
    if not pending:
        console.print("[dim]No staged file, folder, or shell changes to review.[/dim]")
        return False

    console.print(approval_summary(pending))
    choice = questionary.select(
        "Apply staged changes?",
        choices=["Approve all", "Review one by one", "Cancel"],
    ).ask()

    if choice in (None, "Cancel"):
        for action in pending:
            tracker.update_status(action.id, "rejected", False)
        return False

    if choice == "Approve all":
        for action in pending:
            tracker.update_status(action.id, "approved", True)
        return True

    for group in _group_pending(pending):
        while True:
            item_choice = questionary.select(
                group.label,
                choices=["Accept", "Show diff", "Reject"],
            ).ask()
            if item_choice in (None, "Reject"):
                for action_id in group.action_ids:
                    tracker.update_status(action_id, "rejected", False)
                break
            if item_choice == "Show diff":
                if group.patch:
                    console.print(Syntax(group.patch, "diff", theme="ansi_dark"))
                else:
                    console.print("[dim]No diff available.[/dim]")
                continue
            for action_id in group.action_ids:
                tracker.update_status(action_id, "approved", True)
            break

    return any(action.status == "approved" for action in tracker.get_actions())
