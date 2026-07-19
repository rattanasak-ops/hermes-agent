#!/usr/bin/env python3
"""Read and enforce the single machine-readable active-task contract."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any


SCHEMA = "hermes-goal-contract-v1"
CONTRACT_PATH = Path(".project/active-task.json")
HUMAN_PATH = Path(".project/active-task.md")
STATUSES = {"active", "frozen", "completed"}
HASH_FIELDS = (
    "schema",
    "task_id",
    "plan_id",
    "goal",
    "deliverables",
    "branch",
    "base_sha",
    "allowed_paths",
    "forbidden_paths",
    "work_types",
    "owner_scope_token",
    "primary_issues",
    "support_issues",
    "next_prompt",
    "status",
    "frozen_at",
    "merge_sha",
)

SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _text(value: object) -> str:
    return str(value or "").strip()


def _string_list(value: object, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"GOAL_CONTRACT_INVALID: {field} ต้องเป็นรายการที่มีข้อมูล")
    result = [_text(item) for item in value]
    if any(not item for item in result) or len(set(result)) != len(result):
        raise ValueError(f"GOAL_CONTRACT_INVALID: {field} มีค่าว่างหรือค่าซ้ำ")
    return result


def canonical_scope(value: dict[str, Any]) -> dict[str, Any]:
    return {field: value.get(field) for field in HASH_FIELDS}


def goal_hash(value: dict[str, Any]) -> str:
    data = json.dumps(
        canonical_scope(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def validate_contract(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ValueError("GOAL_CONTRACT_INVALID: schema ไม่ตรง")
    for field in ("task_id", "plan_id", "goal", "branch", "base_sha", "owner_scope_token", "next_prompt"):
        if not _text(value.get(field)):
            raise ValueError(f"GOAL_CONTRACT_INVALID: ไม่มี {field}")
    if not SHA_PATTERN.fullmatch(_text(value.get("base_sha"))):
        raise ValueError("GOAL_CONTRACT_INVALID: base_sha ต้องเป็น Git SHA 40 ตัว")
    for field in ("deliverables", "allowed_paths", "work_types", "primary_issues"):
        value[field] = _string_list(value.get(field), field)
    for field in ("forbidden_paths", "support_issues"):
        value[field] = _string_list(value.get(field), field, allow_empty=True)
    if value.get("status") not in STATUSES:
        raise ValueError("GOAL_CONTRACT_INVALID: status ไม่ตรง")
    if value["status"] == "frozen" and (
        not _text(value.get("frozen_at")) or not _text(value.get("merge_sha"))
    ):
        raise ValueError("GOAL_CONTRACT_INVALID: frozen ต้องมีเวลาและ merge_sha")
    if value["status"] == "frozen" and not SHA_PATTERN.fullmatch(
        _text(value.get("merge_sha"))
    ):
        raise ValueError("GOAL_CONTRACT_INVALID: merge_sha ต้องเป็น Git SHA 40 ตัว")
    expected = goal_hash(value)
    if _text(value.get("goal_hash")) != expected:
        raise ValueError("GOAL_HASH_MISMATCH: เป้าหมายหรือขอบเขตถูกเปลี่ยนโดยไม่มีลายนิ้วมือใหม่")
    return value


def load_contract(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("GOAL_CONTRACT_INVALID: ไฟล์ต้องเป็น JSON object")
    return validate_contract(value)


def find_contract(start: str | Path) -> Path | None:
    current = Path(start).expanduser().resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        candidate = directory / CONTRACT_PATH
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            break
    return None


def _matches(path: str, pattern: str) -> bool:
    clean_path = path.strip("/")
    clean_pattern = pattern.strip("/")
    if clean_pattern.endswith("/**"):
        prefix = clean_pattern[:-3].rstrip("/")
        return clean_path == prefix or clean_path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(clean_path, clean_pattern)


def check_action(
    contract: dict[str, Any], paths: list[str], work_type: str, branch: str
) -> dict[str, Any]:
    try:
        value = validate_contract(dict(contract))
    except ValueError as exc:
        return {"ok": False, "code": str(exc).split(":", 1)[0], "reason": str(exc)}
    if value["status"] == "frozen":
        return {"ok": False, "code": "BRANCH_FROZEN", "reason": "กิ่งนี้ถูกรวมและแช่แข็งแล้ว"}
    if value["status"] != "active":
        return {"ok": False, "code": "GOAL_TASK_NOT_ACTIVE", "reason": "ใบงานไม่ได้อยู่สถานะ active"}
    if branch != value["branch"]:
        return {"ok": False, "code": "GOAL_BRANCH_MISMATCH", "reason": "กิ่งปัจจุบันไม่ตรงใบงาน"}
    if work_type not in value["work_types"]:
        return {"ok": False, "code": "GOAL_WORK_TYPE_BLOCKED", "reason": "ชนิดงานไม่อยู่ในใบงาน"}
    if not paths:
        return {"ok": False, "code": "GOAL_PATH_UNRESOLVED", "reason": "ระบุไฟล์ที่จะเปลี่ยนไม่ได้"}
    for path in paths:
        clean = str(path).replace("\\", "/")
        while clean.startswith("./"):
            clean = clean[2:]
        if any(_matches(clean, pattern) for pattern in value["forbidden_paths"]):
            return {"ok": False, "code": "GOAL_PATH_FORBIDDEN", "reason": clean, "path": clean}
        if not any(_matches(clean, pattern) for pattern in value["allowed_paths"]):
            return {"ok": False, "code": "GOAL_PATH_OUTSIDE_SCOPE", "reason": clean, "path": clean}
    return {"ok": True, "code": "GOAL_CONTRACT_OK"}


def scope_change_command(
    old_task_id: str,
    new_task_id: str,
    branch: str,
    new_allowed_paths: list[str],
    impact: str,
) -> str:
    paths = _string_list(new_allowed_paths, "new_allowed_paths")
    return (
        f"SCOPE CHANGE {_text(old_task_id)} TO {_text(new_task_id)} "
        f"BRANCH {_text(branch)} PATHS {','.join(paths)} IMPACT {_text(impact)}"
    )


def apply_scope_change(current: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    value = validate_contract(dict(current))
    command = _text(change.get("owner_command"))
    if not command.startswith("SCOPE CHANGE "):
        raise ValueError("SCOPE_CHANGE_TOKEN_REQUIRED: คำอนุมัติทั่วไปเปลี่ยนขอบเขตไม่ได้")
    required = ("old_task_id", "new_task_id", "branch", "new_allowed_paths", "impact")
    if any(not change.get(field) for field in required):
        raise ValueError("SCOPE_CHANGE_INVALID: ข้อมูลเปลี่ยนขอบเขตไม่ครบ")
    if change["old_task_id"] != value["task_id"] or change["branch"] != value["branch"]:
        raise ValueError("SCOPE_CHANGE_INVALID: งานเดิมหรือกิ่งไม่ตรงใบงาน")
    expected_command = scope_change_command(
        change["old_task_id"],
        change["new_task_id"],
        change["branch"],
        change["new_allowed_paths"],
        change["impact"],
    )
    if command != expected_command:
        raise ValueError(
            "SCOPE_CHANGE_TOKEN_REQUIRED: คำสั่งเจ้าของต้องผูกงานเดิม งานใหม่ กิ่ง เส้นทาง และผลกระทบตรงกัน"
        )
    updated = dict(value)
    updated["task_id"] = _text(change["new_task_id"])
    updated["allowed_paths"] = _string_list(change["new_allowed_paths"], "new_allowed_paths")
    updated["owner_scope_token"] = command
    updated["goal_hash"] = goal_hash(updated)
    return validate_contract(updated)


def freeze_contract(contract: dict[str, Any], merge_sha: str, frozen_at: str) -> dict[str, Any]:
    value = validate_contract(dict(contract))
    if not _text(merge_sha) or not _text(frozen_at):
        raise ValueError("BRANCH_FREEZE_INVALID: ต้องมี merge_sha และเวลา")
    value["status"] = "frozen"
    value["merge_sha"] = _text(merge_sha)
    value["frozen_at"] = _text(frozen_at)
    value["goal_hash"] = goal_hash(value)
    return validate_contract(value)


def render_human_view(value: dict[str, Any]) -> str:
    item = validate_contract(dict(value))
    lines = [
        f"# Active Task — {item['task_id']}",
        "",
        "> สร้างจาก .project/active-task.json · ห้ามแก้ไฟล์นี้เป็นแหล่งข้อมูลหลัก",
        f"> goal_hash: `{item['goal_hash']}`",
        f"> status: `{item['status']}` · branch: `{item['branch']}` · base: `{item['base_sha']}`",
        "",
        "## เป้าหมาย",
        "",
        item["goal"],
        "",
        "## ผลที่ต้องส่ง",
        "",
        *[f"- {row}" for row in item["deliverables"]],
        "",
        "## เส้นทางที่อนุญาต",
        "",
        *[f"- `{row}`" for row in item["allowed_paths"]],
        "",
        "## Prompt ถัดไป",
        "",
        item["next_prompt"],
        "",
    ]
    return "\n".join(lines)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def git_gate(
    root: Path,
    contract: dict[str, Any],
    *,
    branch: str,
    base_sha: str,
    head_sha: str,
) -> dict[str, Any]:
    value = validate_contract(dict(contract))
    if base_sha != value["base_sha"]:
        return {"ok": False, "code": "GOAL_BASE_SHA_MISMATCH", "expected": value["base_sha"], "actual": base_sha}
    if branch != value["branch"]:
        return {"ok": False, "code": "GOAL_BRANCH_MISMATCH", "expected": value["branch"], "actual": branch}
    if value["status"] == "frozen":
        return {"ok": False, "code": "BRANCH_FROZEN"}
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base_sha, head_sha],
        cwd=root,
        text=True,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        return {"ok": False, "code": "GOAL_HISTORY_MISMATCH"}
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{base_sha}..{head_sha}"],
        cwd=root,
        text=True,
        capture_output=True,
    )
    if changed.returncode != 0:
        return {"ok": False, "code": "GOAL_GIT_DIFF_FAILED", "reason": changed.stderr.strip()}
    paths = sorted(set(filter(None, changed.stdout.splitlines())))
    result = check_action(value, paths, "release", branch)
    if not result["ok"]:
        if result.get("reason") in paths:
            result["path"] = result["reason"]
        return result
    return {"ok": True, "code": "GOAL_GIT_GATE_OK", "files": len(paths), "goal_hash": value["goal_hash"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=".")
    parser.add_argument(
        "command", choices=("verify", "render", "freeze", "scope-change", "check-git")
    )
    parser.add_argument("--merge-sha", default="")
    parser.add_argument("--frozen-at", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--base-sha", default="")
    parser.add_argument("--head-sha", default="HEAD")
    parser.add_argument("--owner-command", default="")
    parser.add_argument("--old-task-id", default="")
    parser.add_argument("--new-task-id", default="")
    parser.add_argument("--allowed-path", action="append", default=[])
    parser.add_argument("--impact", default="")
    args = parser.parse_args(argv)
    root = Path(args.cwd).expanduser().resolve()
    path = root / CONTRACT_PATH
    try:
        value = load_contract(path)
        if args.command == "check-git":
            result = git_gate(
                root,
                value,
                branch=args.branch,
                base_sha=args.base_sha,
                head_sha=args.head_sha,
            )
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0 if result["ok"] else 2
        if args.command == "render":
            atomic_write(root / HUMAN_PATH, render_human_view(value))
        elif args.command == "freeze":
            value = freeze_contract(value, args.merge_sha, args.frozen_at)
            atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            atomic_write(root / HUMAN_PATH, render_human_view(value))
        elif args.command == "scope-change":
            value = apply_scope_change(
                value,
                {
                    "owner_command": args.owner_command,
                    "old_task_id": args.old_task_id,
                    "new_task_id": args.new_task_id,
                    "branch": args.branch,
                    "new_allowed_paths": args.allowed_path,
                    "impact": args.impact,
                },
            )
            atomic_write(
                path,
                json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )
            atomic_write(root / HUMAN_PATH, render_human_view(value))
        result = {"ok": True, "code": "GOAL_CONTRACT_OK", "task_id": value["task_id"], "goal_hash": value["goal_hash"], "status": value["status"]}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"ok": False, "code": str(exc).split(":", 1)[0], "reason": str(exc)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
