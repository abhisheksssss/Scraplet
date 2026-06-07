from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from .executor import ToolExecutor


class PathArgs(BaseModel):
    path: str = Field(..., description="Path relative to the workspace root.")


class CreateFileArgs(PathArgs):
    content: str = Field(..., description="Full file content.")


class ModifyFileArgs(PathArgs):
    content: str = Field(..., description="Complete replacement file content.")


class ListFilesArgs(BaseModel):
    path: str = Field(".", description="Path relative to the workspace root.")
    recursive: bool = Field(False, description="Whether to recurse into folders.")


class AnalyzeCodebaseArgs(BaseModel):
    path: str = Field(".", description="Path relative to the workspace root.")


class SearchFilesArgs(BaseModel):
    root: str = Field(".", description="Directory to search.")
    pattern: str = Field("*", description='Glob pattern, for example "*.py".')
    content_contains: str | None = Field(None, description="Optional text filter.")


class ShellArgs(BaseModel):
    command: str = Field(..., description="Single shell command to queue.")


def create_agent_tools(executor: ToolExecutor) -> list[StructuredTool]:
    def read_file(path: str) -> str:
        return executor.read_file(path)

    def create_file(path: str, content: str) -> str:
        return executor.create_file(path, content)

    def modify_file(path: str, content: str) -> str:
        return executor.modify_file(path, content)

    def delete_file(path: str) -> str:
        return executor.delete_file(path)

    def create_folder(path: str) -> str:
        return executor.create_folder(path)

    def list_files(path: str = ".", recursive: bool = False) -> str:
        return executor.list_files(path, recursive)

    def search_files(
        root: str = ".",
        pattern: str = "*",
        content_contains: str | None = None,
    ) -> str:
        return executor.search_files(root, pattern, content_contains)

    def analyze_codebase(path: str = ".") -> str:
        return executor.analyze_codebase(path)

    def execute_shell(command: str) -> str:
        return executor.queue_shell(command)

    def list_skills() -> str:
        return executor.list_skills()

    def read_skill(path: str) -> str:
        return executor.read_skill(path)

    return [
        StructuredTool.from_function(
            read_file,
            name="read_file",
            description="Read a text file from the workspace.",
            args_schema=PathArgs,
        ),
        StructuredTool.from_function(
            create_file,
            name="create_file",
            description="Stage creation of a file. It is not written until approval.",
            args_schema=CreateFileArgs,
        ),
        StructuredTool.from_function(
            modify_file,
            name="modify_file",
            description="Stage a full-file replacement. It is not written until approval.",
            args_schema=ModifyFileArgs,
        ),
        StructuredTool.from_function(
            delete_file,
            name="delete_file",
            description="Stage deletion of a file.",
            args_schema=PathArgs,
        ),
        StructuredTool.from_function(
            create_folder,
            name="create_folder",
            description="Stage creation of a directory tree.",
            args_schema=PathArgs,
        ),
        StructuredTool.from_function(
            list_files,
            name="list_files",
            description="List files and directories under a path.",
            args_schema=ListFilesArgs,
        ),
        StructuredTool.from_function(
            search_files,
            name="search_files",
            description="Find files matching a glob pattern and optional text filter.",
            args_schema=SearchFilesArgs,
        ),
        StructuredTool.from_function(
            analyze_codebase,
            name="analyze_codebase",
            description="Summarize file and directory counts.",
            args_schema=AnalyzeCodebaseArgs,
        ),
        StructuredTool.from_function(
            execute_shell,
            name="execute_shell",
            description="Queue a shell command to run after approval.",
            args_schema=ShellArgs,
        ),
        StructuredTool.from_function(
            list_skills,
            name="list_skills",
            description="List configured SKILL.md files.",
        ),
        StructuredTool.from_function(
            read_skill,
            name="read_skill",
            description="Read a SKILL.md file from configured skill roots.",
            args_schema=PathArgs,
        ),
    ]


def create_read_only_tools(executor: ToolExecutor) -> list[StructuredTool]:
    blocked = {
        "create_file",
        "modify_file",
        "delete_file",
        "create_folder",
        "execute_shell",
    }
    return [tool for tool in create_agent_tools(executor) if tool.name not in blocked]
