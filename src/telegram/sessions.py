from __future__ import annotations

from dataclasses import dataclass

from ..agent.executor import ToolExecutor
from ..agent.tracker import ActionTracker
from ..agent.types import ActionLog
from ..plan.types import Plan


@dataclass
class ApprovalSession:
    tracker: ActionTracker
    executor: ToolExecutor
    pending: list[ActionLog]


@dataclass
class PlanSession:
    plan: Plan
    selected: set[str]


approval_sessions: dict[int, ApprovalSession] = {}
plan_sessions: dict[int, PlanSession] = {}
