from __future__ import annotations

from dataclasses import dataclass

import questionary
from rich.console import Console

from ..agent.approval import run_approval_flow
from ..agent.executor import ToolExecutor
from ..agent.orchestrator import run_tool_loop
from ..agent.tools import create_read_only_tools
from ..agent.tracker import ActionTracker
from ..config import default_agent_config
from ..ui.markdown import print_markdown


console = Console()


@dataclass
class AskResult:
    answer: str
    tracker: ActionTracker
    executor: ToolExecutor


def answer_question(question: str, *, include_web: bool = True) -> AskResult:
    config = default_agent_config()
    config.tools.allow_file_creation = True
    config.tools.allow_file_modification = False
    config.tools.allow_folder_creation = False
    config.tools.allow_shell_execution = False

    tracker = ActionTracker()
    executor = ToolExecutor(tracker, config)
    tools = create_read_only_tools(executor)

    if include_web:
        from ..plan.web_tools import create_web_tools

        tools.extend(create_web_tools(tracker))

    answer = run_tool_loop(
        question,
        tools,
        instructions=(
            f"Workspace root: {config.codebase_path}\n"
            "You are in Ask Mode. Do not modify files. Use tools for codebase research."
        ),
        max_steps=20,
    )
    return AskResult(answer=answer, tracker=tracker, executor=executor)


def _answer_markdown(question: str, answer: str) -> str:
    return f"# Ask Mode\n\n## Question\n\n{question.strip()}\n\n## Answer\n\n{answer.strip()}\n"


def run_ask(question: str | None = None) -> None:
    question = question or questionary.text("What do you want to ask?").ask()
    if not question:
        return

    console.print("[bold]Ask Mode[/bold]")
    result = answer_question(question)
    print_markdown(result.answer)

    wants_save = questionary.confirm(
        "Save this answer to a Markdown file?",
        default=False,
    ).ask()
    if not wants_save:
        return

    filename = questionary.text("Filename:", default="ask.md").ask()
    if not filename:
        return
    filename = filename.strip()
    if "/" in filename or "\\" in filename or ".." in filename or not filename.endswith(".md"):
        console.print("[red]Filename must be a simple .md filename.[/red]")
        return

    result.executor.create_file(filename, _answer_markdown(question, result.answer))
    approved = run_approval_flow(result.tracker)
    if approved:
        errors = result.executor.apply_approved_from_tracker()
        if errors:
            console.print("[red]Some operations reported errors:[/red]")
            for error in errors:
                console.print(f"[red]- {error}[/red]")
    result.executor.clear_staging()
