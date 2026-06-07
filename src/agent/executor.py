from __future__ import annotations

import fnmatch
import os
import posixpath
import subprocess
from pathlib import Path

import questionary

from ..config import AgentConfig
from .tracker import ActionTracker
from .types import ActionLog


TEXT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".json",
    ".md",
    ".mdx",
    ".css",
    ".html",
    ".yml",
    ".yaml",
    ".toml",
    ".txt",
}


class ToolExecutor:
    def __init__(self, tracker: ActionTracker, config: AgentConfig) -> None:
        self.tracker = tracker
        self.config = config
        self._overlay: dict[str, str] = {}
        self._deleted: set[str] = set()

    def _norm(self, rel: str | os.PathLike[str]) -> str:
        value = posixpath.normpath(str(rel).replace("\\", "/"))
        if value == ".":
            return "."
        while value.startswith("./"):
            value = value[2:]
        return value

    def _resolve_safe(self, rel: str | os.PathLike[str]) -> Path:
        root = self.config.codebase_path.resolve()
        target = (root / Path(str(rel))).resolve(strict=False)
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Path escapes workspace: {rel}") from exc
        return target

    def _excluded(self, rel: str | os.PathLike[str]) -> bool:
        norm = self._norm(rel)
        parts = [part for part in norm.split("/") if part]
        base = parts[-1] if parts else norm

        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(base, pattern) or fnmatch.fnmatch(norm, pattern):
                return True
            if "*" not in pattern and (
                pattern in parts or norm == pattern or norm.startswith(f"{pattern}/")
            ):
                return True
        return False

    def _assert_not_excluded(self, rel: str, operation: str) -> None:
        if self._excluded(rel):
            raise ValueError(f"{operation}: path is excluded by policy: {rel}")

    def _is_text_file(self, path: Path) -> bool:
        return path.suffix.lower() in TEXT_EXTENSIONS or path.suffix == ""

    def get_effective_text(self, rel: str) -> str | None:
        key = self._norm(rel)
        if key in self._deleted:
            return None
        if key in self._overlay:
            return self._overlay[key]
        target = self._resolve_safe(rel)
        if not target.exists() or not target.is_file():
            return None
        return target.read_text(encoding="utf-8")

    def read_file(self, path: str) -> str:
        self._assert_not_excluded(path, "read_file")
        target = self._resolve_safe(path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        if target.stat().st_size > self.config.max_file_size_to_read:
            raise ValueError(f"File too large: {path}")
        text = target.read_text(encoding="utf-8")
        self.tracker.log(
            action_type="code_analysis",
            path=self._norm(path),
            details={"after": text, "toolName": "read_file"},
            status="executed",
        )
        return text

    def create_file(self, path: str, content: str) -> str:
        if not self.config.tools.allow_file_creation:
            raise PermissionError("File creation disabled")
        self._assert_not_excluded(path, "create_file")
        key = self._norm(path)
        target = self._resolve_safe(path)
        if target.exists() and key not in self._deleted:
            raise FileExistsError(f"create_file: already exists: {path}")
        self._deleted.discard(key)
        self._overlay[key] = content
        self.tracker.log(
            action_type="file_create",
            path=key,
            details={"after": content},
            status="pending",
        )
        return f"Staged new file: {key}"

    def modify_file(self, path: str, content: str) -> str:
        if not self.config.tools.allow_file_modification:
            raise PermissionError("File modification disabled")
        self._assert_not_excluded(path, "modify_file")
        before = self.get_effective_text(path)
        if before is None:
            raise FileNotFoundError(f"modify_file: file not found: {path}")
        key = self._norm(path)
        self._overlay[key] = content
        self.tracker.log(
            action_type="file_modify",
            path=key,
            details={"before": before, "after": content},
            status="pending",
        )
        return f"Staged update: {key}"

    def delete_file(self, path: str) -> str:
        if not self.config.tools.allow_file_modification:
            raise PermissionError("File deletion disabled")
        self._assert_not_excluded(path, "delete_file")
        before = self.get_effective_text(path)
        if before is None:
            raise FileNotFoundError(f"delete_file: file not found: {path}")
        key = self._norm(path)
        self._overlay.pop(key, None)
        self._deleted.add(key)
        self.tracker.log(
            action_type="file_delete",
            path=key,
            details={"before": before},
            status="pending",
        )
        return f"Staged delete: {key}"

    def create_folder(self, path: str) -> str:
        if not self.config.tools.allow_folder_creation:
            raise PermissionError("Folder creation disabled")
        self._assert_not_excluded(path, "create_folder")
        key = self._norm(path)
        self.tracker.log(
            action_type="folder_create",
            path=key,
            details={"after": key},
            status="pending",
        )
        return f"Staged folder: {key}"

    def list_files(self, path: str = ".", recursive: bool = False) -> str:
        self._assert_not_excluded(path, "list_files")
        target = self._resolve_safe(path)
        if not target.exists():
            raise FileNotFoundError(f"list_files: not found: {path}")

        root = self.config.codebase_path.resolve()
        lines: list[str] = []

        def walk(directory: Path, prefix: str = "") -> None:
            for entry in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
                rel = entry.relative_to(root).as_posix()
                if self._excluded(rel):
                    continue
                if entry.is_dir():
                    lines.append(f"{prefix}{entry.name}/")
                    if recursive:
                        walk(entry, f"{prefix}{entry.name}/")
                else:
                    lines.append(f"{prefix}{entry.name}")

        if target.is_dir():
            walk(target)
        else:
            lines.append(target.relative_to(root).as_posix())

        output = "\n".join(sorted(lines)) or "(empty)"
        self.tracker.log(
            action_type="code_analysis",
            path=self._norm(path),
            details={"after": output, "toolName": "list_files"},
            status="executed",
        )
        return output

    def search_files(
        self,
        root: str = ".",
        pattern: str = "*",
        content_contains: str | None = None,
    ) -> str:
        self._assert_not_excluded(root, "search_files")
        root_path = self._resolve_safe(root)
        if not root_path.exists():
            raise FileNotFoundError(f"search_files: root not found: {root}")

        workspace = self.config.codebase_path.resolve()
        candidates = [root_path] if root_path.is_file() else root_path.rglob("*")
        matches: list[str] = []

        for candidate in candidates:
            if not candidate.is_file():
                continue
            rel = candidate.relative_to(workspace).as_posix()
            if self._excluded(rel):
                continue
            if not (
                fnmatch.fnmatch(rel, pattern)
                or fnmatch.fnmatch(candidate.name, pattern)
            ):
                continue
            if content_contains:
                if not self._is_text_file(candidate):
                    continue
                try:
                    text = candidate.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                if content_contains not in text:
                    continue
            matches.append(rel)

        output = "\n".join(sorted(set(matches))) or "(no matches)"
        self.tracker.log(
            action_type="code_analysis",
            path=self._norm(root),
            details={"after": output, "toolName": "search_files"},
            status="executed",
        )
        return output

    def analyze_codebase(self, path: str = ".") -> str:
        target = self._resolve_safe(path)
        if not target.exists():
            raise FileNotFoundError(f"analyze_codebase: not found: {path}")

        files = 0
        directories = 0
        if target.is_file():
            files = 1
        else:
            for candidate in target.rglob("*"):
                rel = candidate.relative_to(self.config.codebase_path).as_posix()
                if self._excluded(rel):
                    continue
                if candidate.is_dir():
                    directories += 1
                else:
                    files += 1

        output = f"Files: {files} | Directories: {directories}"
        self.tracker.log(
            action_type="code_analysis",
            path=self._norm(path),
            details={"after": output, "toolName": "analyze_codebase"},
            status="executed",
        )
        return output

    def queue_shell(self, command: str) -> str:
        if not self.config.tools.allow_shell_execution:
            raise PermissionError("Shell execution disabled")
        self.tracker.log(
            action_type="tool_execute",
            path="shell",
            details={"command": command, "toolName": "execute_shell"},
            status="pending",
        )
        return f"Shell queued: {command}"

    def skill_roots(self) -> list[Path]:
        extra = [
            Path(item).expanduser()
            for item in os.getenv("SKILLS_DIRS", "").split(";")
            if item.strip()
        ]
        home = Path.home()
        return extra + [
            home / ".cursor" / "skills-cursor",
            home / ".claude" / "skills",
        ]

    def list_skills(self) -> str:
        lines: list[str] = []
        for root in self.skill_roots():
            if root.exists():
                lines.extend(str(path) for path in root.rglob("SKILL.md"))
        output = "\n".join(sorted(lines)) or "(none)"
        self.tracker.log(
            action_type="code_analysis",
            path="skills",
            details={"after": output, "toolName": "list_skills"},
            status="executed",
        )
        return output

    def read_skill(self, path: str) -> str:
        target = Path(path).expanduser().resolve()
        allowed = False
        for root in self.skill_roots():
            root = root.resolve()
            try:
                target.relative_to(root)
                allowed = True
                break
            except ValueError:
                continue
        if not allowed:
            raise ValueError("read_skill: outside configured skill roots")
        text = target.read_text(encoding="utf-8")
        self.tracker.log(
            action_type="code_analysis",
            path=str(target),
            details={"after": text, "toolName": "read_skill"},
            status="executed",
        )
        return text

    def _run_in_docker(self, command: str) -> subprocess.CompletedProcess:
        container_name = "scraplet-sandbox"
        image = os.getenv("DOCKER_IMAGE", "python:3.11-slim")
        workspace_str = str(self.config.codebase_path.resolve())
        
        check = subprocess.run(["docker", "info"], capture_output=True, text=True, check=False)
        if check.returncode != 0:
            raise RuntimeError("Docker daemon is not running or accessible.")
            
        check_running = subprocess.run(
            f"docker ps -q -f name=^/{container_name}$", 
            shell=True, capture_output=True, text=True
        )
        if not check_running.stdout.strip():
            check_exists = subprocess.run(
                f"docker ps -aq -f name=^/{container_name}$", 
                shell=True, capture_output=True, text=True
            )
            if check_exists.stdout.strip():
                subprocess.run(f"docker rm -f {container_name}", shell=True, capture_output=True)
                
            start_cmd = (
                f'docker run -d --name {container_name} '
                f'-v "{workspace_str}:/workspace" '
                f'-w /workspace '
                f'{image} tail -f /dev/null'
            )
            res = subprocess.run(start_cmd, shell=True, check=False, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Failed to start sandbox container: {res.stderr}")

        # Execute command using sh (available in all slim images)
        # Escape double quotes in the command to prevent bash injection issues
        escaped_cmd = command.replace('"', '\\"')
        exec_cmd = f'docker exec {container_name} sh -c "{escaped_cmd}"'
        result = subprocess.run(exec_cmd, shell=True, capture_output=True, text=True)
        return result

    def apply_approved_from_tracker(self) -> list[str]:
        errors: list[str] = []
        actions = self.tracker.get_actions()

        for action in [
            item
            for item in actions
            if item.type == "folder_create" and item.status == "approved"
        ]:
            try:
                self._resolve_safe(action.path).mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                errors.append(str(exc))

        file_ops = [
            item
            for item in actions
            if item.status == "approved"
            and item.type in {"file_create", "file_modify", "file_delete"}
        ]
        file_ops.sort(key=lambda item: item.timestamp)

        last_by_path: dict[str, ActionLog] = {}
        for action in file_ops:
            last_by_path[self._norm(action.path)] = action

        for path, action in last_by_path.items():
            try:
                target = self._resolve_safe(path)
                if action.type == "file_delete":
                    target.unlink(missing_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(action.details.get("after", ""), encoding="utf-8")
            except Exception as exc:
                errors.append(str(exc))

        for action in [
            item
            for item in actions
            if item.type == "tool_execute" and item.status == "approved"
        ]:
            command = action.details.get("command")
            if not command:
                continue
            
            use_docker = os.getenv("USE_DOCKER_SANDBOX", "false").lower() == "true"
            result = None
            
            if use_docker:
                try:
                    result = self._run_in_docker(command)
                except Exception as e:
                    print(f"\n--- Notice ---\nDocker sandbox unavailable ({e}).\n--------------")
                    proceed = questionary.confirm("Do you want to fallback and execute this locally instead?").ask()
                    if not proceed:
                        errors.append(f"Aborted: Docker sandbox unavailable for '{command}'")
                        continue
            
            if result is None or not use_docker:
                result = subprocess.run(
                    command,
                    cwd=self.config.codebase_path,
                    shell=True,
                    text=True,
                    capture_output=True,
                )
            
            if result.returncode != 0:
                errors.append(
                    f"shell exit {result.returncode}: {command}\n{result.stderr}"
                )
            elif result.stdout.strip():
                print(f"\n--- Output of '{command}' ---\n{result.stdout.strip()}\n-----------------------------")

        return errors

    def apply_and_return_results(self) -> dict[str, str]:
        results: dict[str, str] = {}
        actions = self.tracker.get_actions()

        for action in [item for item in actions if item.type == "folder_create" and item.status == "approved"]:
            try:
                self._resolve_safe(action.path).mkdir(parents=True, exist_ok=True)
                results[action.id] = "Folder created successfully."
            except Exception as exc:
                results[action.id] = f"Error: {exc}"

        file_ops = [item for item in actions if item.status == "approved" and item.type in {"file_create", "file_modify", "file_delete"}]
        file_ops.sort(key=lambda item: item.timestamp)

        last_by_path: dict[str, ActionLog] = {}
        for action in file_ops:
            last_by_path[self._norm(action.path)] = action

        for action in file_ops:
            if action.id not in [a.id for a in last_by_path.values()]:
                results[action.id] = "Skipped (superseded by a later action in the same batch)."

        for path, action in last_by_path.items():
            try:
                target = self._resolve_safe(path)
                if action.type == "file_delete":
                    target.unlink(missing_ok=True)
                    results[action.id] = "File deleted successfully."
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(action.details.get("after", ""), encoding="utf-8")
                results[action.id] = "File written successfully."
            except Exception as exc:
                results[action.id] = f"Error: {exc}"

        for action in [item for item in actions if item.type == "tool_execute" and item.status == "approved"]:
            command = action.details.get("command")
            if not command:
                results[action.id] = "Error: No command specified."
                continue
            
            use_docker = os.getenv("USE_DOCKER_SANDBOX", "false").lower() == "true"
            result = None
            
            if use_docker:
                try:
                    result = self._run_in_docker(command)
                except Exception as e:
                    print(f"\n--- Notice ---\nDocker sandbox unavailable ({e}).\n--------------")
                    proceed = questionary.confirm("Do you want to fallback and execute this locally instead?").ask()
                    if not proceed:
                        results[action.id] = f"Aborted: Docker sandbox unavailable for '{command}'"
                        continue
            
            if result is None or not use_docker:
                result = subprocess.run(
                    command,
                    cwd=self.config.codebase_path,
                    shell=True,
                    text=True,
                    capture_output=True,
                )
            
            if result.returncode != 0:
                results[action.id] = f"shell exit {result.returncode}: {command}\n{result.stderr}"
            else:
                out = result.stdout.strip()
                if not out:
                    out = "Command executed successfully (no output)."
                results[action.id] = out
                print(f"\n--- Output of '{command}' ---\n{out}\n-----------------------------")

        return results

    def clear_staging(self) -> None:
        self._overlay.clear()
        self._deleted.clear()
