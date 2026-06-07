from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Complexity = Literal["low", "medium", "high"]


@dataclass
class PlanStep:
    id: str
    title: str
    description: str
    hints: list[str] = field(default_factory=list)
    complexity: Complexity | None = None


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep]
    research_summary: str | None = None
