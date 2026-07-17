#!/usr/bin/env python3
"""Open or resume a writable task with Worktree + permit + Relay state."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def run_json(command: list[str], env: dict[str, str]) -> dict:
    proc = subprocess.run(command, text=True, capture_output=True, env=env)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError((proc.stderr or proc.stdout or "คำสั่งไม่คืน JSON").strip())
    if proc.returncode or not data.get("ok"):
        raise RuntimeError(data.get("message") or data.get("reason") or "คำสั่งถูกบล็อก")
    return data


def state_root() -> Path:
    root = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "new-chat" / "sessions"
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    return root


def state_path(task_id: str) -> Path:
    key = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:16]
    return state_root() / f"{task_id}-{key}.json"


def save_state(path: Path, data: dict) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.chmod(0o600)
    os.replace(temp, path)


def find_tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"ไม่พบ {name}; ให้ติดตั้งชุด New Chat ของ Hermes ก่อน")
    return found


def open_task(args: argparse.Namespace) -> dict:
    env = os.environ.copy()
    if args.registry:
        env["HERMES_WORKTREE_REGISTRY"] = args.registry
    command = [
        find_tool("hermes-worktree"), "open", "--project-id", args.project,
        "--staff-id", args.staff_id, "--task-id", args.task_id, "--slug", args.slug,
        "--repo", str(Path(args.repo).expanduser().resolve()), "--base-branch", args.base_branch,
        "--lease-hours", str(args.lease_hours), "--json", "--apply",
    ]
    if args.root:
        command += ["--root", args.root]
    if args.machine_id:
        command += ["--machine-id", args.machine_id]
    if args.registry:
        command += ["--registry", args.registry]
    opened = run_json(command, env)
    task = opened["task"]
    worktree = Path(task["worktree_path"]).resolve()
    base_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=worktree, text=True).strip()
    permit = [
        find_tool("hermes-write-permit"), "acquire", "--cwd", str(worktree),
        "--task-id", args.task_id, "--branch", task["branch"], "--base-sha", base_sha,
        "--approval", args.approval, "--ttl-minutes", str(args.lease_hours * 60),
    ]
    for value in args.allowed_path:
        permit += ["--allowed-path", value]
    permit_data = run_json(permit, env)
    state = {
        "schema": "hermes-new-chat-v1", "status": "NEW_CHAT_READY", "wtl": "WTL_READY",
        "relay": "RELAY_REQUIRED", "task_id": args.task_id, "project": args.project,
        "staff_id": args.staff_id, "machine_id": task.get("machine_id"),
        "canonical_repo": str(Path(args.repo).expanduser().resolve()), "worktree": str(worktree),
        "branch": task["branch"], "base_sha": base_sha, "allowed_paths": sorted(set(args.allowed_path)),
        "registry": args.registry or env.get("HERMES_WORKTREE_REGISTRY", ""),
        "opened_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "permit_expires_at": permit_data["permit"]["expires_at"],
    }
    save_state(state_path(args.task_id), state)
    return state


def status_task(args: argparse.Namespace) -> dict:
    path = state_path(args.task_id)
    if not path.is_file():
        raise RuntimeError("ไม่พบ session ของ task นี้; ต้องเปิดด้วย hermes-new-chat open ก่อน")
    state = json.loads(path.read_text(encoding="utf-8"))
    env = os.environ.copy()
    if state.get("registry"):
        env["HERMES_WORKTREE_REGISTRY"] = state["registry"]
    command = [find_tool("hermes-worktree"), "status", "--task-id", args.task_id, "--json"]
    if state.get("registry"):
        command += ["--registry", state["registry"]]
    live = run_json(command, env)
    state["wtl"] = live["decision"]
    state["status"] = "NEW_CHAT_READY" if live["decision"] == "WTL_READY" else "NEW_CHAT_BLOCKED"
    return state


def main() -> int:
    parser = argparse.ArgumentParser(prog="hermes-new-chat")
    subs = parser.add_subparsers(dest="action", required=True)
    opened = subs.add_parser("open")
    for name in ("project", "staff-id", "task-id", "slug", "repo", "approval"):
        opened.add_argument("--" + name, required=True)
    opened.add_argument("--root")
    opened.add_argument("--registry")
    opened.add_argument("--machine-id")
    opened.add_argument("--base-branch", default="main")
    opened.add_argument("--lease-hours", type=int, default=12)
    opened.add_argument("--allowed-path", action="append", default=[])
    status = subs.add_parser("status")
    status.add_argument("--task-id", required=True)
    args = parser.parse_args()
    try:
        if args.action == "open" and not args.allowed_path:
            args.allowed_path = ["."]
        result = open_task(args) if args.action == "open" else status_task(args)
    except (RuntimeError, OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(json.dumps({"ok": False, "status": "NEW_CHAT_BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
