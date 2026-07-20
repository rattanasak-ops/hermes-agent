#!/usr/bin/env python3
"""Convert explicit owner messages into S1 evidence records.

Accepted owner-only forms:
  SPEC ANSWER <answer>
  SPEC APPROVE <manifest-short-hash>
  SPEC WAIVE <64-char-diff-hash> <reason>
Other prompts are ignored, so ordinary conversation is never treated as consent.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys


ANSWER = re.compile(r"^SPEC\s+ANSWER\s+(.+)$", re.IGNORECASE | re.DOTALL)
APPROVE = re.compile(r"^SPEC\s+APPROVE\s+([a-f0-9]{8})$", re.IGNORECASE)
WAIVE = re.compile(r"^SPEC\s+WAIVE\s+([a-f0-9]{64})\s+(.+)$", re.IGNORECASE | re.DOTALL)


def root_at(cwd: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "-c", f"safe.directory={cwd}", "rev-parse", "--show-toplevel"],
        cwd=cwd, text=True, capture_output=True,
    )
    return Path(proc.stdout.strip()).resolve() if proc.returncode == 0 else None


def prompt(payload: dict) -> str:
    for key in ("prompt", "user_message", "user_prompt", "last_user_message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def tool_at(root: Path) -> Path:
    candidates = [
        Path(os.environ.get("HERMES_SPEC_INTERVIEW_TOOL", "")),
        Path.home() / ".hermes/spec-tools/spec_interview.py",
        root / "scripts/spec-interview/spec_interview.py",
    ]
    return next((path for path in candidates if str(path) and path.is_file()), candidates[1])


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
    if not isinstance(value, dict):
        raise ValueError("คำตอบ broker ผิดรูปแบบ")
    return value


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    root = root_at(Path(str(payload.get("cwd") or Path.cwd())).resolve())
    if root is None:
        return 0
    cfg_path = root / ".project/spec-gate.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    text = prompt(payload)
    answer, approve, waive = ANSWER.fullmatch(text), APPROVE.fullmatch(text), WAIVE.fullmatch(text)
    if not any((answer, approve, waive)):
        return 0
    if cfg.get("backend") == "os-broker":
        request = {
            "action": "owner-candidate",
            "repo": str(root),
            "plan_id": str(cfg.get("plan_id", "")),
            "spec": str(root / str(cfg.get("spec_path", ""))),
            "text": text,
        }
        if answer:
            request["kind"] = "answer"
        elif approve:
            request.update({"kind": "approve", "manifest_short_hash": approve.group(1).lower()})
        else:
            request.update({"kind": "waive", "diff_hash": waive.group(1).lower()})
        try:
            result = broker_call(cfg, request)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[Hermes SPEC Owner Hook] ส่ง candidate ไม่ได้: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("ok") else 2
    tool = tool_at(root)
    if not tool.is_file():
        print("[Hermes SPEC Owner Hook] ไม่พบ spec-interview", file=sys.stderr)
        return 2
    base = [sys.executable, str(tool)]
    common = ["--repo", str(root), "--plan-id", str(cfg.get("plan_id", ""))]
    if answer:
        args = ["record-answer", *common, "--from-owner-hook"]
    elif approve:
        # The owner must echo the manifest's visible short hash.
        manifest = subprocess.run(
            [*base, "manifest", *common, "--spec", str(root / str(cfg.get("spec_path", "")))],
            text=True, capture_output=True,
        )
        try:
            current = json.loads(manifest.stdout).get("manifest_hash", "")
        except json.JSONDecodeError:
            current = ""
        if manifest.returncode or not current.startswith(approve.group(1).lower()):
            print("[Hermes SPEC Owner Hook] รหัส manifest ไม่ตรง", file=sys.stderr)
            return 2
        args = ["approve", *common, "--spec", str(root / str(cfg.get("spec_path", ""))), "--from-owner-hook"]
    else:
        args = ["waive", *common, "--diff-hash", waive.group(1).lower(), "--from-owner-hook"]
    forwarded = dict(payload)
    forwarded["hook_event_name"] = "UserPromptSubmit"
    proc = subprocess.run(base + args, input=json.dumps(forwarded, ensure_ascii=False), text=True, capture_output=True)
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
