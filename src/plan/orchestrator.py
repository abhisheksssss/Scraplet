from __future__ import annotations

from dataclasses import dataclass

import questionary
from rich.console import Console

from ..agent.approval import run_approval_flow
from ..agent.executor import ToolExecutor
from ..agent.orchestrator import run_tool_loop
from ..agent.tools import create_agent_tools
from ..agent.tracker import ActionTracker
from ..config import default_agent_config
from ..ui.markdown import print_markdown
from .planner import generate_plan
from .selection import print_plan, select_steps
from .types import Plan, PlanStep


console = Console()


@dataclass
class PlanExecutionResult:
    outputs: list[str]
    tracker: ActionTracker
    executor: ToolExecutor


def step_prompt(goal: str, step: PlanStep) -> str:
    hints = "\n".join(f"- {hint}" for hint in step.hints)
    return "\n".join(
        [
            f"Goal: {goal}",
            f"Step: {step.title}",
            step.description,
            f"Hints:\n{hints}" if hints else "",
        ]
    ).strip()


def execute_plan_steps(plan: Plan, steps: list[PlanStep]) -> PlanExecutionResult:
    config = default_agent_config()
    tracker = ActionTracker()
    executor = ToolExecutor(tracker, config)
    tools = create_agent_tools(executor)

    from .web_tools import create_web_tools

    tools.extend(create_web_tools(tracker))

    outputs: list[str] = []
    for step in steps:
        console.print(f"[bold]Executing:[/bold] {step.title}")
        output = run_tool_loop(
            step_prompt(plan.goal, step),
            tools,
            instructions=(
                f"Workspace root: {config.codebase_path}\n"
                "Execute only the requested plan step.\n"
                "All mutations are staged until approval."
            ),
            max_steps=30,
        )
        outputs.append(output)

    return PlanExecutionResult(outputs=outputs, tracker=tracker, executor=executor)


def run_plan(goal: str | None = None) -> None:
    goal = goal or questionary.text("What is your goal?").ask()
    if not goal:
        return

    console.print("[bold]Plan Mode[/bold]")
    plan = generate_plan(goal)
    print_plan(plan)

    selected = select_steps(plan)
    if not selected:
        console.print("[dim]No steps selected.[/dim]")
        return

    proceed = questionary.confirm(
        f"Execute {len(selected)} selected step(s)?",
        default=True,
    ).ask()
    if not proceed:
        return

    result = execute_plan_steps(plan, selected)
    for output in result.outputs:
        if output.strip():
            print_markdown(output)

    approved = run_approval_flow(result.tracker)
    if not approved:
        result.executor.clear_staging()
        return

    errors = result.executor.apply_approved_from_tracker()
    result.executor.clear_staging()

    if errors:
        console.print("[red]Some operations reported errors:[/red]")
        for error in errors:
            console.print(f"[red]- {error}[/red]")
    else:
        console.print("[green]Applied.[/green]")
