#!/usr/bin/env python3
"""Expose memory-receipt drift to New Chat without modifying project files."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

from memory_receipt import verify_receipt


NEW_CHAT = re.compile(
    r"(?:use\s+new\s+chat|start\s+new\s+chat|new\s+chat\s+startup|"
    r"initialize\s+hermes\s+agent\s+chat|เริ่ม\s*new\s*chat|เปิด\s*new\s*chat|"
    r"เริ่มแชทใหม่|เปิดแชทใหม่)",
    re.I,
)


def prompt(payload: dict) -> str:
    for key in ("prompt", "user_message", "user_prompt", "last_user_message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def git_root(cwd: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={cwd}", "rev-parse", "--show-toplevel"],
        cwd=cwd, text=True, capture_output=True,
    )
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return 0
    if not isinstance(payload, dict) or not NEW_CHAT.search(prompt(payload)):
        return 0
    root = git_root(Path(str(payload.get("cwd") or Path.cwd())).resolve())
    if root is None:
        return 0
    result = verify_receipt(root)
    if result["code"] == "MEMORY_RECEIPT_OK":
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    files = ", ".join(result.get("files") or []) or "ไม่พบชื่อไฟล์"
    print(
        f"{result['code']}: {result['reason']} · ไฟล์: {files} · "
        "ให้ตรวจ Git และไฟล์จริงก่อนเชื่อสถานะ ห้ามเขียนทับเพื่อซ่อมเอง"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
