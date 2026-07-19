#!/usr/bin/env python3
"""Machine-readable phase state used by the phase-autonomy response gate."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from goal_contract import load_contract


SCHEMA = "phase-state-v1"
ZONES = {"ZONE_A", "ZONE_B"}
KINDS = {"primary", "support"}
STATUSES = {"pending", "working", "verified", "owner_required", "failed", "blocked"}
SAFE_STATUSES = {"pending", "working", "failed"}


def find_state_path(cwd: str | Path) -> Path | None:
    current = Path(cwd).expanduser().resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        target = candidate / ".project/phase-state.json"
        if target.is_file():
            return target
    return None


def validate_state(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("phase-state ต้องเป็น JSON object")
    if value.get("schema") != SCHEMA:
        raise ValueError("schema ของ phase-state ไม่ตรง")
    if not str(value.get("plan_id") or "").strip() or not str(value.get("phase_id") or "").strip():
        raise ValueError("phase-state ไม่มี plan_id หรือ phase_id")
    scope = value.get("approved_scope")
    if not isinstance(scope, dict) or not str(scope.get("owner_approval") or "").strip():
        raise ValueError("phase-state ไม่มีหลักฐานอนุมัติขอบเขต")
    if scope.get("question_budget") != 0:
        raise ValueError("งาน ZONE_A ต้องมีงบคำถาม 0 ครั้ง")
    issues = value.get("issues")
    if not isinstance(issues, list) or not issues:
        raise ValueError("phase-state ต้องมี Issue อย่างน้อยหนึ่งรายการ")
    seen: set[str] = set()
    for issue in issues:
        if not isinstance(issue, dict):
            raise ValueError("ข้อมูล Issue ผิดรูปแบบ")
        issue_id = str(issue.get("issue_id") or "").strip()
        if not issue_id or issue_id in seen:
            raise ValueError("issue_id ว่างหรือซ้ำ")
        seen.add(issue_id)
        if issue.get("zone") not in ZONES:
            raise ValueError(f"{issue_id} ไม่มี ZONE_A หรือ ZONE_B")
        if issue.get("status") not in STATUSES:
            raise ValueError(f"{issue_id} มีสถานะผิดรูปแบบ")
        issue.setdefault("kind", "primary")
        if issue.get("kind") not in KINDS:
            raise ValueError(f"{issue_id} ต้องเป็น primary หรือ support")
        evidence = issue.get("evidence", [])
        if not isinstance(evidence, list):
            raise ValueError(f"{issue_id} evidence ต้องเป็นรายการ")
        if issue.get("status") == "verified" and not evidence:
            raise ValueError(f"{issue_id} verified แต่ไม่มีหลักฐาน")
    return value


def load_state(path: Path) -> dict[str, Any]:
    state = validate_state(json.loads(path.read_text(encoding="utf-8")))
    contract_path = path.parent / "active-task.json"
    if contract_path.is_file():
        contract = load_contract(contract_path)
        if (
            state.get("task_id") != contract["task_id"]
            or state.get("plan_id") != contract["plan_id"]
            or state.get("goal_hash") != contract["goal_hash"]
        ):
            raise ValueError("PHASE_GOAL_DRIFT: phase-state ไม่ตรง task_id, plan_id หรือ goal_hash ปัจจุบัน")
    return state


def next_safe_issue(state: dict[str, Any]) -> dict[str, Any] | None:
    for issue in state["issues"]:
        if issue["zone"] == "ZONE_A" and issue["status"] in SAFE_STATUSES:
            return issue
    return None


def phase_summary(state: dict[str, Any]) -> dict[str, Any]:
    total = len(state["issues"])
    verified = sum(issue["status"] == "verified" for issue in state["issues"])
    pending = total - verified
    percent = round((verified / total) * 100) if total else 0
    next_issue = next_safe_issue(state)
    primary = [issue for issue in state["issues"] if issue.get("kind", "primary") == "primary"]
    support = [issue for issue in state["issues"] if issue.get("kind", "primary") == "support"]
    primary_verified = sum(issue["status"] == "verified" for issue in primary)
    support_verified = sum(issue["status"] == "verified" for issue in support)
    return {
        "plan_id": state["plan_id"], "phase_id": state["phase_id"],
        "total": total, "verified": verified, "pending": pending,
        "percent": percent, "remaining_percent": 100 - percent,
        "safe_work_remaining": next_issue is not None,
        "next_safe_issue": next_issue["issue_id"] if next_issue else None,
        "primary_total": len(primary),
        "primary_verified": primary_verified,
        "primary_percent": round((primary_verified / len(primary)) * 100) if primary else 0,
        "support_total": len(support),
        "support_verified": support_verified,
        "support_percent": round((support_verified / len(support)) * 100) if support else 0,
    }


def atomic_write(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    with lock.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            json.dump(state, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)


def set_status(path: Path, issue_id: str, status: str, evidence: list[str]) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError("สถานะใหม่ผิดรูปแบบ")
    state = load_state(path)
    for issue in state["issues"]:
        if issue["issue_id"] != issue_id:
            continue
        if status == "verified" and not evidence:
            raise ValueError("สถานะ verified ต้องมีหลักฐาน")
        issue["status"] = status
        if evidence:
            issue["evidence"] = evidence
        validate_state(state)
        atomic_write(path, state)
        return phase_summary(state)
    raise ValueError(f"ไม่พบ Issue {issue_id}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    root.add_argument("--cwd", default=".")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    commands.add_parser("next")
    initialize = commands.add_parser("init")
    initialize.add_argument("--plan-id", required=True)
    initialize.add_argument("--phase-id", required=True)
    initialize.add_argument("--owner-approval", required=True)
    initialize.add_argument("--issue", action="append", required=True)
    initialize.add_argument("--state-path", default="")
    update = commands.add_parser("set-status")
    update.add_argument("--issue-id", required=True)
    update.add_argument("--status", required=True)
    update.add_argument("--evidence", action="append", default=[])
    commands.add_parser("close")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "init":
        try:
            issues = []
            for raw in args.issue:
                parts = raw.split("|", 2)
                if len(parts) != 3:
                    raise ValueError("--issue ต้องเป็น ISSUE_ID|ZONE_A|คำอธิบาย")
                issue_id, zone, summary = (part.strip() for part in parts)
                issues.append({
                    "issue_id": issue_id, "zone": zone, "status": "pending",
                    "summary": summary, "evidence": [],
                })
            path = Path(args.state_path).expanduser().resolve() if args.state_path else Path(args.cwd).expanduser().resolve() / ".project/phase-state.json"
            state = validate_state({
                "schema": SCHEMA, "active": True,
                "plan_id": args.plan_id, "phase_id": args.phase_id,
                "approved_scope": {"owner_approval": args.owner_approval, "question_budget": 0},
                "issues": issues, "owner_question_used": False,
            })
            atomic_write(path, state)
            print(json.dumps({"ok": True, **phase_summary(state), "path": str(path)}, ensure_ascii=False, sort_keys=True))
            return 0
        except (OSError, ValueError) as exc:
            print(json.dumps({"ok": False, "reason": str(exc)}, ensure_ascii=False))
            return 2
    path = find_state_path(args.cwd)
    if path is None:
        print(json.dumps({"ok": False, "reason": "PHASE_STATE_MISSING"}, ensure_ascii=False))
        return 2
    try:
        state = load_state(path)
        if args.command == "set-status":
            result = set_status(path, args.issue_id, args.status, args.evidence)
        elif args.command == "close":
            result = phase_summary(state)
            if result["pending"]:
                raise ValueError("ปิดเฟสไม่ได้เพราะยังมี Issue ที่ไม่ verified")
            state["active"] = False
            atomic_write(path, state)
            result["active"] = False
        else:
            result = phase_summary(state)
            if args.command == "next":
                result = {"next_safe_issue": result["next_safe_issue"]}
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
