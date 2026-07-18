#!/usr/bin/env python3
"""บันทึกคำสั่งสร้างกิ่งตรงจากเจ้าของเป็นสิทธิ์อายุสั้นต่อ Git root."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


MAX_PROMPT_CHARS = 500
MAX_PROMPT_LINES = 9
INTENT_TTL_SECONDS = 300
BRANCH_NAME = r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}"
BRANCH_REQUEST = re.compile(
    rf"(?:สร้าง|เปิด|create|make)\s*(?:new\s*)?(?:branch|สาขา|กิ่ง)"
    rf"\s*(?:ใหม่\s*)?(?:ชื่อ|name)?\s*(?:=|:)?\s*[`'\"]?({BRANCH_NAME})",
    re.IGNORECASE,
)
GIT_REQUEST = re.compile(
    rf"git\s+(?:switch\s+-c|checkout\s+-b|branch)\s+({BRANCH_NAME})",
    re.IGNORECASE,
)
NEGATION = re.compile(
    r"(?:ห้าม|อย่า|ไม่ต้อง|ไม่ให้|ไม่ควร|do\s+not|don't|never)"
    r"\s*(?:ให้\s+\S+\s*)?(?:สร้าง|เปิด|create|make|new)?\s*"
    r"(?:new\s*)?(?:branch|สาขา|กิ่ง)",
    re.IGNORECASE,
)
PASTED_MARKERS = {"ตัวอย่าง", "แชทเก่า", "เหตุการณ์เดิม", "example from", "old chat"}
PROTECTED_BRANCHES = {"main", "master", "develop", "development", "production", "prod"}


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (_text(item) for item in value)))
    if isinstance(value, dict):
        for key in ("text", "content", "message", "prompt"):
            if key in value:
                result = _text(value[key])
                if result:
                    return result
    return ""


def owner_prompt(payload: dict) -> str:
    for key in ("user_message", "prompt", "user_prompt", "last_user_message", "message"):
        result = _text(payload.get(key)).strip()
        if result:
            return result
    return ""


def git_root(payload: dict) -> Path | None:
    candidates = [payload.get("cwd"), payload.get("workspace")]
    roots = payload.get("workspace_roots")
    if isinstance(roots, list):
        candidates.extend(roots)
    candidates.append(os.getcwd())
    for value in candidates:
        if not isinstance(value, str) or not value.strip():
            continue
        path = Path(value).expanduser()
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            text=True,
            capture_output=True,
        ) if path.is_dir() else None
        if proc is not None and proc.returncode == 0:
            return Path(proc.stdout.strip()).resolve()
    return None


def valid_branch(name: str) -> bool:
    return (
        name.lower() not in PROTECTED_BRANCHES
        and not name.endswith(("/", ".", ".lock"))
        and ".." not in name
        and "@{" not in name
        and "//" not in name
    )


def requested_branch(prompt: str) -> str:
    if (
        not prompt
        or len(prompt) > MAX_PROMPT_CHARS
        or len(prompt.splitlines()) > MAX_PROMPT_LINES
        or any(marker in prompt.lower() for marker in PASTED_MARKERS)
        or NEGATION.search(prompt)
    ):
        return ""
    match = BRANCH_REQUEST.search(prompt) or GIT_REQUEST.search(prompt)
    branch = match.group(1) if match else ""
    return branch if branch and valid_branch(branch) else ""


def intent_path(root: Path) -> Path:
    key = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
    return Path.home() / ".hermes" / "owner-intents" / f"{key}.json"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        print("{}")
        return 0
    if not isinstance(payload, dict):
        print("{}")
        return 0
    root = git_root(payload)
    if root is None:
        print("{}")
        return 0
    path = intent_path(root)
    branch = requested_branch(owner_prompt(payload))
    if not branch:
        path.unlink(missing_ok=True)
        print("{}")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    expires = datetime.now(timezone.utc) + timedelta(seconds=INTENT_TTL_SECONDS)
    record = {
        "schema": "hermes-owner-branch-intent-v1",
        "git_root": str(root),
        "branch": branch,
        "expires_at": expires.isoformat(),
        "session_id": str(payload.get("session_id") or payload.get("conversation_id") or ""),
    }
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    temp.chmod(0o600)
    temp.replace(path)
    print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
