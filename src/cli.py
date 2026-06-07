from __future__ import annotations

from typing import Optional

import questionary
import typer
from rich.console import Console

from .agent.orchestrator import run_agent
from .ask.orchestrator import run_ask
from .plan.orchestrator import run_plan
from .ui.wakeup import run_wakeup
from dotenv import set_key
from pathlib import Path
from . import config



app = typer.Typer(name="scraplet", help="Python Scraplet assistant.")
console = Console()

config.WORKSPACE = str(Path.cwd())
print(config.WORKSPACE)


@app.command()
def wakeup() -> None:
    """Show the banner and choose CLI or Telegram mode."""
    run_wakeup()


@app.command()
def ask(question: Optional[str] = typer.Argument(None)) -> None:
    """Ask a read-only question about the codebase."""
    run_ask(question)



@app.command()
def agent(goal: Optional[str] = typer.Argument(None)) -> None:
    """Run the agent and stage changes for approval."""
    run_agent(goal)


@app.command()
def plan(goal: Optional[str] = typer.Argument(None)) -> None:
    """Generate a plan, select steps, then execute them."""
    run_plan(goal)


@app.command()
def telegram() -> None:
    """Start Telegram bot mode."""
    from .telegram.bot import run_telegram_bot

    run_telegram_bot()


def interactive_cli() -> None:
    while True:
        mode = questionary.select(
            "Choose CLI sub-mode:",
            choices=["Agent Mode", "Plan Mode", "Ask Mode", "Exit"],
        ).ask()
        if mode in (None, "Exit"):
            return
        if mode == "Agent Mode":
            run_agent()
        elif mode == "Plan Mode":
            run_plan()
        elif mode == "Ask Mode":
            run_ask()


if __name__ == "__main__":
    app()
