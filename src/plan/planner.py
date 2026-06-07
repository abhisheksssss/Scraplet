from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError
from rich.console import Console

from ..agent.executor import ToolExecutor
from ..agent.orchestrator import run_tool_loop
from ..agent.tools import create_read_only_tools
from ..agent.tracker import ActionTracker
from ..config import default_agent_config
from .types import Plan, PlanStep


console = Console()


class PlanStepDraft(BaseModel):
    title: str
    description: str
    hints: list[str] = Field(default_factory=list)
    complexity: Literal["low", "medium", "high"] | None = None


class PlanDraft(BaseModel):
    researchSummary: str | None = None
    steps: list[PlanStepDraft] = Field(min_length=1, max_length=15)


def _extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def generate_plan(goal: str) -> Plan:
    config = default_agent_config()
    config.tools.allow_file_creation = False
    config.tools.allow_file_modification = False
    config.tools.allow_folder_creation = False
    config.tools.allow_shell_execution = False

    tracker = ActionTracker()
    executor = ToolExecutor(tracker, config)
    tools = create_read_only_tools(executor)

    from .web_tools import create_web_tools

    tools.extend(create_web_tools(tracker))

    console.print("[cyan]Researching and drafting a plan...[/cyan]")
    text = run_tool_loop(
        f"User goal:\n{goal}",
        tools,
        instructions=(
            "You are Scraplet Plan Mode. Do not modify files.\n"
            f"Workspace root: {config.codebase_path}\n"
            "Use read-only tools when useful.\n"
            "Return JSON only with this shape:\n"
            '{"researchSummary":"optional summary","steps":[{"title":"...","description":"...","hints":["..."],"complexity":"low|medium|high"}]}\n'
            "Keep the plan between 1 and 15 steps."
        ),
        max_steps=20,
    )

    try:
        draft = PlanDraft.model_validate(json.loads(_extract_json(text)))
    except (json.JSONDecodeError, ValidationError):
        console.print("[yellow]Planner returned non-JSON output; using fallback plan.[/yellow]")
        draft = PlanDraft(
            researchSummary=text.strip()[:1000] or None,
            steps=[
                PlanStepDraft(
                    title="Implement the requested change",
                    description=goal,
                    complexity="medium",
                )
            ],
        )

    steps = [
        PlanStep(
            id=f"step-{index}",
            title=step.title,
            description=step.description,
            hints=step.hints,
            complexity=step.complexity,
        )
        for index, step in enumerate(draft.steps, start=1)
    ]
    return Plan(goal=goal, research_summary=draft.researchSummary, steps=steps)
