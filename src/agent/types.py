from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


ActionType = Literal[
    "file_create",
    "file_modify",
    "file_delete",
    "folder_create",
    "code_analysis",
    "tool_execute",
]
ActionStatus = Literal["pending", "executed", "approved", "rejected"]


@dataclass
class ActionLog:
    id: str
    type: ActionType
    path: str
    details: dict[str, str] = field(default_factory=dict)
    status: ActionStatus = "pending"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_approved: bool | None = None


def is_mutation_type(action_type: ActionType) -> bool:
    return action_type in {
        "file_create",
        "file_modify",
        "file_delete",
        "folder_create",
        "tool_execute",
    }
