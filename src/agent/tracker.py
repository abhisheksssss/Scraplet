from __future__ import annotations

from datetime import datetime

from .types import ActionLog, ActionStatus, ActionType, is_mutation_type


class ActionTracker:
    def __init__(self) -> None:
        self._actions: list[ActionLog] = []

    def log(
        self,
        *,
        action_type: ActionType,
        path: str,
        details: dict[str, str] | None = None,
        status: ActionStatus,
        action_id: str | None = None,
        timestamp: datetime | None = None,
        user_approved: bool | None = None,
    ) -> ActionLog:
        action = ActionLog(
            id=action_id or f"action_{len(self._actions)}",
            type=action_type,
            path=path,
            details=details or {},
            status=status,
            timestamp=timestamp or datetime.now().astimezone(),
            user_approved=user_approved,
        )
        self._actions.append(action)
        return action

    def clear(self) -> None:
        self._actions.clear()

    def get_actions(self) -> list[ActionLog]:
        return list(self._actions)

    def get_pending_mutations(self) -> list[ActionLog]:
        return [
            action
            for action in self._actions
            if is_mutation_type(action.type) and action.status == "pending"
        ]

    def update_status(
        self,
        action_id: str,
        status: ActionStatus,
        user_approved: bool | None = None,
    ) -> None:
        for action in self._actions:
            if action.id == action_id:
                action.status = status
                if user_approved is not None:
                    action.user_approved = user_approved
                return
