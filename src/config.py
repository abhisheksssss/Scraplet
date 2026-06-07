from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

WORKSPACE=None

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent
    

def load_environment() -> None:
    """Load root and Scraplet-local .env files."""
    load_dotenv(REPO_ROOT / ".env", override=False)
    load_dotenv(PACKAGE_ROOT / ".env", override=True)


def workspace_root() -> Path:
    env_root = WORKSPACE
    if env_root:
        return Path(env_root).expanduser().resolve()

    cwd = Path.cwd().resolve()
    if cwd.name.lower() == "scraplet" and (cwd.parent / "package.json").exists():
        return cwd.parent.resolve()
    return cwd


@dataclass
class ToolPermissions:
    allow_shell_execution: bool = True
    allow_file_modification: bool = True
    allow_file_creation: bool = True
    allow_folder_creation: bool = True


@dataclass
class AgentConfig:
    codebase_path: Path
    max_file_size_to_read: int = 1024 * 1024
    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            "node_modules",
            ".git",
            "dist",
            "build",
            ".next",
            "*.log",
            ".env*",
            ".venv",
            "__pycache__",
        ]
    )
    tools: ToolPermissions = field(default_factory=ToolPermissions)


def default_agent_config() -> AgentConfig:
    load_environment()
    return AgentConfig(codebase_path=workspace_root())
