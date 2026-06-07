from __future__ import annotations

import os
from pathlib import Path

import pyfiglet
import questionary
from rich.console import Console

from ..config import REPO_ROOT, load_environment


console = Console()


def _env_path() -> Path:
    return REPO_ROOT / ".env"


def _get_env(key: str) -> str | None:
    load_environment()
    return os.getenv(key)


def _set_env(key: str, value: str) -> None:
    path = _env_path()
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    prefix = f"{key}="
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{key}={value}"
            break
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = value


def _configure_local() -> None:
    _set_env("SCRAPLET_LLM_PROVIDER", "local")
    url = _get_env("LOCAL_LLM_URL")
    if not url:
        url = questionary.text(
            "Local LLM URL:",
            default="http://localhost:11434",
        ).ask()
        if not url:
            return
        _set_env("LOCAL_LLM_URL", url)

    model = _get_env("LOCAL_LLM_MODEL")
    if not model:
        model = questionary.text("Local model:", default="llama3").ask()
        if model:
            _set_env("LOCAL_LLM_MODEL", model)

    console.print(f"[green]Using local LLM at {url}[/green]")


def _configure_openrouter() -> None:
    _set_env("SCRAPLET_LLM_PROVIDER", "openrouter")
    api_key = _get_env("OPENROUTER_API_KEY") or _get_env("OPEN_ROUTER_API_KEY")
    if not api_key:
        api_key = questionary.password("OpenRouter API key:").ask()
        if not api_key:
            return
        _set_env("OPENROUTER_API_KEY", api_key)

    model = _get_env("OPENROUTER_MODEL") or _get_env("OPEN_ROUTER_DEFAULT_MODEL")
    if not model:
        model = questionary.text(
            "OpenRouter model:",
            default="openai/gpt-4o-mini",
        ).ask()
        if model:
            _set_env("OPENROUTER_MODEL", model)

    console.print("[green]Using OpenRouter configuration from .env[/green]")


def run_wakeup() -> None:
    console.print(f"[bold cyan]{pyfiglet.figlet_format('Scraplet').rstrip()}[/bold cyan]")

    provider = questionary.select(
        "Choose LLM provider:",
        choices=["Local LLM", "OpenRouter API", "Exit"],
    ).ask()

    if provider in (None, "Exit"):
        console.print("[dim]Bye[/dim]")
        return
    if provider == "Local LLM":
        _configure_local()
    else:
        _configure_openrouter()

    mode = questionary.select(
        "Choose mode:",
        choices=["CLI", "Telegram", "Exit"],
    ).ask()

    if mode in (None, "Exit"):
        console.print("[dim]Bye[/dim]")
        return
    if mode == "CLI":
        from ..cli import interactive_cli

        interactive_cli()
    else:
        from ..telegram.bot import run_telegram_bot

        run_telegram_bot()
