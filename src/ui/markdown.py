from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown


console = Console()


def print_markdown(text: str) -> None:
    console.print(Markdown((text or "(empty)").strip()))
