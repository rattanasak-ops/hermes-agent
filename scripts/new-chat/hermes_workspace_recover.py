#!/usr/bin/env python3
"""Recover a registered task branch from detached HEAD in the current Git root.

This command never creates a worktree and never invents a branch name.  The
target branch must come from the Hermes worktree registry for the exact Git
root supplied by ``--cwd``.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ACTIVE_STATES = {"CREATED", "ACTIVE", "PAUSED", "IN_REVIEW", "BLOCKED"}
PROTECTED_BRANCHES = {"main", "master", "develop", "development", "production", "prod"}


class RecoveryError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def git_root(cwd: Path) -> Path:
    result = git(cwd, "rev-parse", "--show-toplevel", check=False)
    if result.returncode != 0:
        raise RecoveryError("NOT_GIT_ROOT", "พื้นที่ปัจจุบันไม่ใช่ Git repository")
    return Path(result.stdout.strip()).resolve()


def registry_paths() -> list[Path]:
    paths: list[Path] = []
    explicit = os.environ.get("HERMES_WORKTREE_REGISTRY", "").strip()
    if explicit:
        paths.append(Path(explicit).expanduser())
    hermes_home = os.environ.get("HERMES_HOME", "").strip()
    if hermes_home:
        paths.append(Path(hermes_home).expanduser() / "worktrees/registry.json")
    paths.append(Path.home() / ".hermes/worktrees/registry.json")
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve(strict=False)
        if resolved not in unique:
            unique.append(resolved)
    return unique


def load_registry() -> tuple[Path, dict[str, Any]]:
    for path in registry_paths():
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RecoveryError("REGISTRY_INVALID", f"อ่านสมุดทะเบียนไม่ได้: {exc}") from exc
        if not isinstance(data, dict):
            raise RecoveryError("REGISTRY_INVALID", "สมุดทะเบียนต้องเป็น JSON object")
        return path, data
    raise RecoveryError("REGISTRY_NOT_FOUND", "ไม่พบสมุดทะเบียน Worktree ของ Hermes")


def task_records(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw = data.get("tasks", {})
    if isinstance(raw, dict):
        return [value for value in raw.values() if isinstance(value, dict)]
    if isinstance(raw, list):
        return [value for value in raw if isinstance(value, dict)]
    return []


def record_for_root(data: dict[str, Any], root: Path) -> dict[str, Any]:
    matches = []
    for record in task_records(data):
        raw_path = str(record.get("worktree_path") or "").strip()
        if not raw_path:
            continue
        if Path(raw_path).expanduser().resolve(strict=False) == root:
            matches.append(record)
    if not matches:
        raise RecoveryError("REGISTERED_ROOT_NOT_FOUND", "พื้นที่นี้ไม่มีรายการงานในสมุดทะเบียน")
    if len(matches) > 1:
        raise RecoveryError("REGISTERED_ROOT_AMBIGUOUS", "พื้นที่นี้ผูกกับงานมากกว่าหนึ่งรายการ")
    record = matches[0]
    state = str(record.get("state") or "").upper()
    if state not in ACTIVE_STATES:
        raise RecoveryError("REGISTERED_TASK_INACTIVE", f"งานในสมุดทะเบียนอยู่สถานะ {state or 'UNKNOWN'}")
    return record


def checked_out_roots(root: Path) -> dict[str, Path]:
    result = git(root, "worktree", "list", "--porcelain")
    mapping: dict[str, Path] = {}
    current_path: Path | None = None
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current_path = Path(line.removeprefix("worktree ")).resolve(strict=False)
        elif line.startswith("branch refs/heads/") and current_path is not None:
            mapping[line.removeprefix("branch refs/heads/")] = current_path
    return mapping


def branch_exists(root: Path, branch: str) -> bool:
    result = git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    return result.returncode == 0


def current_branch(root: Path) -> str:
    return git(root, "branch", "--show-current").stdout.strip()


def current_head(root: Path) -> str:
    return git(root, "rev-parse", "HEAD").stdout.strip()


def recover(cwd: Path) -> dict[str, Any]:
    root = git_root(cwd)
    registry_path, registry = load_registry()
    record = record_for_root(registry, root)
    branch = str(record.get("branch") or "").strip()
    valid_ref = bool(branch) and git(
        root, "check-ref-format", "--branch", branch, check=False
    ).returncode == 0
    if not valid_ref or branch in PROTECTED_BRANCHES:
        raise RecoveryError("REGISTERED_BRANCH_UNSAFE", "ชื่อกิ่งในสมุดทะเบียนว่างหรือเป็นกิ่งร่วม")

    current = current_branch(root)
    if current == branch:
        return {
            "ok": True,
            "code": "REGISTERED_BRANCH_ALREADY_READY",
            "task_id": record.get("task_id"),
            "root": str(root),
            "branch": branch,
            "registry": str(registry_path),
        }
    if current:
        raise RecoveryError(
            "RECOVERY_NOT_DETACHED",
            f"พื้นที่อยู่บนกิ่ง {current} จึงไม่เปลี่ยนกิ่งอัตโนมัติ",
        )

    checked_out = checked_out_roots(root).get(branch)
    if checked_out is not None and checked_out != root:
        raise RecoveryError(
            "REGISTERED_BRANCH_IN_OTHER_WORKTREE",
            f"กิ่งที่ลงทะเบียนถูกเปิดอยู่ในพื้นที่อื่น: {checked_out}",
        )

    dirty = bool(git(root, "status", "--porcelain").stdout.strip())
    head = current_head(root)
    exists = branch_exists(root, branch)
    if exists:
        branch_head = git(root, "rev-parse", branch).stdout.strip()
        if branch_head != head:
            raise RecoveryError(
                "RECOVERY_CONFLICT",
                "HEAD ปัจจุบันอยู่คนละ SHA กับกิ่งในสมุดทะเบียน จึงหยุดเพื่อรักษางาน",
            )
        git(root, "switch", branch)
    else:
        git(root, "switch", "-c", branch)

    return {
        "ok": True,
        "code": "RECOVERED_REGISTERED_BRANCH",
        "task_id": record.get("task_id"),
        "root": str(root),
        "branch": branch,
        "head": current_head(root),
        "dirty_preserved": dirty,
        "worktree_created": False,
        "registry": str(registry_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="กู้กิ่งที่ลงทะเบียนไว้ใน Git root เดิม โดยไม่สร้าง Worktree ใหม่"
    )
    parser.add_argument("--cwd", default=".", help="โฟลเดอร์ภายใน Git root ที่ต้องกู้")
    parser.add_argument("--json", action="store_true", help="แสดงผลเป็น JSON")
    return parser.parse_args()


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{payload['code']}: {payload.get('message') or payload.get('branch', '')}")


def main() -> int:
    args = parse_args()
    try:
        payload = recover(Path(args.cwd).expanduser())
    except RecoveryError as exc:
        payload = {"ok": False, "code": exc.code, "message": exc.message}
        emit(payload, args.json)
        return 2
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or exc.stdout or str(exc)).strip()
        payload = {"ok": False, "code": "GIT_RECOVERY_FAILED", "message": message}
        emit(payload, args.json)
        return 2
    emit(payload, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
