#!/usr/bin/env python3
"""Default-deny S1 pre-write hook."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
import sys


GATE_VERSION = "1.0.0"
WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit", "applypatch", "apply_patch", "patch"}
DELEGATION_TOOLS = {"task", "agent", "delegate", "subagent", "spawn_agent"}
OWNER_ACTIONS = {"record-answer", "approve", "waive"}
READ_ONLY = {"rg", "grep", "ls", "pwd", "head", "tail", "cat", "awk", "wc", "stat", "du", "df", "jq", "realpath", "diff"}
PATCH_PATH = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)


def block(reason: str) -> int:
    message = f"[Hermes SPEC Gate] BLOCKED: {reason}"
    print(message, file=sys.stderr)
    print(json.dumps({"decision": "block", "reason": message}, ensure_ascii=False))
    return 2


def git_root(cwd: Path) -> Path | None:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, text=True, capture_output=True)
    return Path(proc.stdout.strip()).resolve() if proc.returncode == 0 else None


def config(root: Path) -> dict | None:
    path = root / ".project" / "spec-gate.json"
    if not path.exists():
        # Old projects with no S1 marker remain report-only. Once a project has
        # a spec directory, removing the gate configuration must fail closed.
        return {"invalid": True} if (root / ".project" / "spec").exists() else None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"invalid": True}
    return value if isinstance(value, dict) else {"invalid": True}


def core_tool(root: Path) -> Path:
    choices = [
        Path(os.environ.get("HERMES_SPEC_INTERVIEW_TOOL", "")),
        root / "scripts/spec-interview/spec_interview.py",
        Path.home() / ".hermes/spec-tools/spec_interview.py",
    ]
    return next((path for path in choices if str(path) and path.is_file()), choices[1])


def broker_call(cfg: dict, request: dict) -> dict:
    socket_path = str(cfg.get("broker_request_socket") or "/var/run/hermes-spec/request.sock")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(socket_path)
        client.sendall(json.dumps(request, ensure_ascii=False).encode("utf-8") + b"\n")
        raw = b""
        while not raw.endswith(b"\n"):
            part = client.recv(65536)
            if not part:
                break
            raw += part
    value = json.loads(raw)
    return value if isinstance(value, dict) else {"ok": False}


def approved(root: Path, cfg: dict) -> bool:
    if cfg.get("backend") == "os-broker":
        try:
            data = broker_call(cfg, {
                "action": "verify", "repo": str(root),
                "plan_id": str(cfg.get("plan_id", "")),
                "spec": str(root / str(cfg.get("spec_path", ""))),
            })
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        return bool(
            data.get("ok")
            and data.get("broker_version") == GATE_VERSION
            and data.get("approved_manifest_match")
            and int(data.get("service_uid", -1)) != os.geteuid()
        )
    tool = core_tool(root)
    spec = root / str(cfg.get("spec_path", ""))
    if cfg.get("schema") != "hermes-spec-gate-v1" or cfg.get("gate_version") != GATE_VERSION:
        return False
    if not tool.is_file() or not spec.is_file():
        return False
    proc = subprocess.run([
        sys.executable, str(tool), "verify", "--repo", str(root),
        "--plan-id", str(cfg.get("plan_id", "")), "--spec", str(spec),
    ], text=True, capture_output=True)
    if proc.returncode:
        return False
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False
    return bool(data.get("ok") and data.get("tool_version") == GATE_VERSION and data.get("approved_manifest_match"))


def tool_version_ok(root: Path) -> bool:
    tool = core_tool(root)
    if not tool.is_file():
        return False
    proc = subprocess.run([sys.executable, str(tool), "--version"], text=True, capture_output=True)
    return proc.returncode == 0 and proc.stdout.strip() == GATE_VERSION


def configured_writer_ok(root: Path, cfg: dict) -> bool:
    if cfg.get("backend") != "os-broker":
        return tool_version_ok(root)
    try:
        data = broker_call(cfg, {"action": "health"})
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return bool(
        data.get("ok")
        and data.get("version") == GATE_VERSION
        and int(data.get("service_uid", -1)) != os.geteuid()
    )


def targets(tool: str, data: dict, cwd: Path) -> list[Path]:
    values: list[str] = []
    path = data.get("file_path") or data.get("path")
    if isinstance(path, str):
        values.append(path)
    if tool in {"applypatch", "apply_patch", "patch"}:
        values.extend(PATCH_PATH.findall(str(data.get("patch") or data.get("input") or "")))
    return [(Path(value) if Path(value).is_absolute() else cwd / value) for value in values]


def inside(path: Path, base: Path) -> bool:
    resolved, base = path.resolve(), base.resolve()
    return resolved == base or base in resolved.parents


def draft_target_allowed(path: Path, root: Path, cfg: dict) -> bool:
    allowed = [root / item for item in cfg.get("draft_allowlist", []) if isinstance(item, str)]
    return any(inside(path, item) for item in allowed)


def protected_target(path: Path, root: Path) -> bool:
    protected = [root / "scripts/spec-interview", root / "team-shortcuts/hooks/enforce-spec-gate.py"]
    return any(inside(path, item) for item in protected)


def shell_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def owner_action(tokens: list[str]) -> bool:
    for index, token in enumerate(tokens):
        if Path(token).name in {"spec-interview", "spec_interview.py"}:
            return any(item in OWNER_ACTIONS for item in tokens[index + 1:])
    return False


def spec_command(tokens: list[str]) -> str:
    for index, token in enumerate(tokens):
        if Path(token).name in {
            "spec-interview", "spec_interview.py",
            "hermes-spec-broker-client", "spec_broker_client.py",
        }:
            return next((item for item in tokens[index + 1:] if not item.startswith("-")), "")
    return ""


def read_only_shell(command: str) -> bool:
    if any(mark in command for mark in (">", "|", ";", "&&", "||", "$(", "`")):
        return False
    tokens = shell_tokens(command)
    if not tokens:
        return False
    first = Path(tokens[0]).name
    if first == "git":
        if len(tokens) < 2:
            return False
        if tokens[1] == "branch":
            return all(item in {"--show-current", "--list", "-a", "--all", "-r", "--remotes", "-v", "-vv"} for item in tokens[2:])
        return tokens[1] in {"status", "diff", "show", "log", "ls-files", "check-ignore", "rev-parse"}
    if spec_command(tokens):
        return spec_command(tokens) in {"verify", "manifest", "record-question", "guarded-write"}
    return first in READ_ONLY


def run(payload: dict) -> int:
    raw_tool = str(payload.get("tool_name") or "")
    tool = re.split(r"[.:/]", raw_tool)[-1].lower()
    cwd = Path(str(payload.get("cwd") or Path.cwd())).resolve()
    root = git_root(cwd)
    if root is None:
        return 0
    cfg = config(root)
    if cfg is None:
        return 0
    if cfg.get("invalid") or cfg.get("schema") != "hermes-spec-gate-v1" or cfg.get("gate_version") != GATE_VERSION:
        return block("ไฟล์ตั้งค่าด่านหาย เสีย หรือรุ่นไม่ตรง")
    raw = payload.get("tool_input")
    data = raw if isinstance(raw, dict) else {}
    is_approved = approved(root, cfg)

    if tool in DELEGATION_TOOLS and not is_approved:
        return block("สเปคยังไม่อนุมัติ; ห้ามส่งงานให้ relay/subagent")
    if tool in {"bash", "exec_command", "terminal", "shell", "run_shell_command"}:
        command = str(data.get("command") or data.get("cmd") or "")
        tokens = shell_tokens(command)
        if owner_action(tokens):
            return block("ห้าม AI บันทึกคำตอบ อนุมัติ หรือสร้าง waiver แทนเจ้าของ")
        if spec_command(tokens) in {"guarded-write", "guarded-write-batch"} and not configured_writer_ok(root, cfg):
            return block("ตัวเขียนที่ถือล็อกหายหรือรุ่นไม่ตรง")
        if not read_only_shell(command):
            reason = "สเปคยังไม่อนุมัติ; shell ปิดโดยปริยาย" if not is_approved else "งานเขียนหลังอนุมัติต้องผ่าน spec-interview guarded-write เพื่อกันการแทรกระหว่างตรวจ-เขียน"
            return block(reason)
        return 0
    if tool in WRITE_TOOLS:
        paths = targets(tool, data, cwd)
        if not paths:
            return block("คำสั่งเขียนไม่มี path ให้ตรวจ")
        if any(not inside(path, root) for path in paths):
            return block("ห้ามเขียนข้าม Git root หรือหนีผ่าน symlink")
        if any(protected_target(path, root) for path in paths):
            return block("ห้ามแก้ตัวด่านหรือตัวบันทึกหลักฐาน")
        outside_draft = any(not draft_target_allowed(path, root, cfg) for path in paths)
        if outside_draft:
            if not is_approved:
                return block("สเปคยังไม่อนุมัติ; เขียนได้เฉพาะไฟล์สเปค แผน และ scratchpad")
            return block("ไฟล์ระบบต้องเขียนผ่าน spec-interview guarded-write เพื่อถือ lock และตรวจสเปคซ้ำ")
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return block("อ่าน hook payload ไม่ได้")
    return run(payload) if isinstance(payload, dict) else block("hook payload ต้องเป็น object")


if __name__ == "__main__":
    raise SystemExit(main())
