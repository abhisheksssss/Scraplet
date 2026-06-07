from __future__ import annotations

import questionary
from rich.console import Console
from rich.markdown import Markdown

from .types import Plan, PlanStep


console = Console()


def print_plan(plan: Plan) -> None:
    if plan.research_summary:
        console.print("[bold]Research summary[/bold]")
        console.print(Markdown(plan.research_summary))

    console.print("[bold]Generated Plan[/bold]")
    for index, step in enumerate(plan.steps, start=1):
        tag = f" [{step.complexity}]" if step.complexity else ""
        console.print(f"{index}. [cyan]{step.title}[/cyan]{tag}")


def select_steps(plan: Plan) -> list[PlanStep]:
    choices = [
        questionary.Choice(
            title=f"{index}. {step.title}",
            value=step.id,
            checked=True,
        )
        for index, step in enumerate(plan.steps, start=1)
    ]
    picked = questionary.checkbox(
        "Select steps to execute:",
        choices=choices,
    ).ask()

    if not picked:
        return []
    picked_ids = set(picked)
    return [step for step in plan.steps if step.id in picked_ids]
