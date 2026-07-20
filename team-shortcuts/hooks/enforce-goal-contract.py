#!/usr/bin/env python3
"""Block writes that do not fit the active goal contract."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from goal_contract import check_action, find_contract, git_gate, load_contract


WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit", "applypatch"}
PATCH_PATH = re.compile(r"^\*\*\* (?:Add|Update|Delete) File:\s*(.+)$", re.M)
SHELL_WRITE = re.compile(r"(?:^|\s)(?:cp|mv|install|tee|truncate|touch|chmod|chown|sed\s+-i|git\s+(?:commit|push|merge))\b|>>?", re.I)
CONTRACT_FILES = {".project/active-task.json", ".project/active-task.md"}


def _tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("tool_input") or payload.get("input") or payload
    return value if isinstance(value, dict) else {}


def _tool_name(payload: dict[str, Any]) -> str:
    return str(payload.get("tool_name") or payload.get("name") or "").lower().replace("-", "").replace("_", "")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-c", f"safe.directory={root}", *args], cwd=root, text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def _relative(root: Path, value: str, cwd: Path) -> str | None:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = cwd / path
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return value.replace("\\", "/").lstrip("./")


def _git_action(command: str) -> str:
    match = re.search(r"\bgit\s+(commit|push|merge)\b", command, re.I)
    return match.group(1).lower() if match else ""


def _paths(payload: dict[str, Any], root: Path, cwd: Path) -> list[str]:
    data = _tool_input(payload)
    result: list[str] = []
    for key in ("file_path", "path", "notebook_path", "target_file"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            result.append(_relative(root, value, cwd) or value)
    patch = str(data.get("patch") or data.get("patch_text") or "")
    result.extend(_relative(root, item.strip(), cwd) or item.strip() for item in PATCH_PATH.findall(patch))
    command = str(data.get("command") or data.get("cmd") or "")
    if _git_action(command) == "commit":
        result.extend(_git(root, "diff", "--cached", "--name-only").splitlines())
    return sorted(set(item for item in result if item))


def _work_type(payload: dict[str, Any], paths: list[str]) -> str:
    explicit = str(payload.get("work_type") or _tool_input(payload).get("work_type") or "").strip()
    if explicit:
        return explicit
    if paths and all(path.startswith("tests/") for path in paths):
        return "test"
    if paths and all(path.endswith((".md", ".json", ".yaml", ".yml")) for path in paths):
        return "docs"
    return "code"


def _is_write(payload: dict[str, Any]) -> bool:
    name = _tool_name(payload)
    if name in WRITE_TOOLS:
        return True
    data = _tool_input(payload)
    command = str(data.get("command") or data.get("cmd") or "")
    return bool(command and SHELL_WRITE.search(command))


def _history_matches(root: Path, base_sha: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base_sha, "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return 0
    if not isinstance(payload, dict) or not _is_write(payload):
        return 0
    cwd = Path(str(payload.get("cwd") or _tool_input(payload).get("cwd") or Path.cwd())).expanduser().resolve()
    contract_path = find_contract(cwd)
    if contract_path is None:
        return 0
    root = contract_path.parents[1]
    try:
        contract = load_contract(contract_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"GOAL_CONTRACT_INVALID: {exc}", file=sys.stderr)
        return 2
    data = _tool_input(payload)
    command = str(data.get("command") or data.get("cmd") or "")
    action = _git_action(command)
    paths = _paths(payload, root, cwd)
    branch = str(payload.get("branch") or _git(root, "branch", "--show-current") or contract["branch"])
    if not _history_matches(root, contract["base_sha"]):
        print(
            f"GOAL_HISTORY_MISMATCH: HEAD ไม่ได้ต่อจาก base_sha ในใบงาน "
            f"· task={contract['task_id']} · goal_hash={contract['goal_hash'][:12]}",
            file=sys.stderr,
        )
        return 2
    if not action and any(path in CONTRACT_FILES for path in paths):
        print(
            "GOAL_CONTRACT_DIRECT_WRITE_BLOCKED: ใบงานเครื่องต้องเปลี่ยนผ่าน "
            "goal_contract.py scope-change หรือ freeze เท่านั้น",
            file=sys.stderr,
        )
        return 2
    if action in {"push", "merge"}:
        result = git_gate(
            root,
            contract,
            branch=branch,
            base_sha=contract["base_sha"],
            head_sha="HEAD",
        )
        if result["ok"]:
            return 0
        print(
            f"{result['code']}: {result.get('reason') or result.get('path') or ''} "
            f"· งานถูกหยุดก่อน {action} · task={contract['task_id']} "
            f"· goal_hash={contract['goal_hash'][:12]}",
            file=sys.stderr,
        )
        return 2
    result = check_action(contract, paths, _work_type(payload, paths), branch)
    if result["ok"]:
        return 0
    print(
        f"{result['code']}: {result.get('reason', '')} · งานถูกหยุดก่อนเขียน "
        f"· task={contract['task_id']} · goal_hash={contract['goal_hash'][:12]}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
