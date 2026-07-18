#!/usr/bin/env python3
"""Block assistant replies that push recoverable workspace/branch work to the owner.

The owner rule is operational: when the AI is already inside a valid Git root,
it must recover or continue there. It must not ask the owner to open another
workspace, create a branch by hand, or run terminal steps that the AI can do.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime


VIOLATION_LOG = os.path.expanduser("~/.claude/hooks-violations.log")

FRICTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ให้(?:เจ้าของ|คุณ|ผู้ใช้).{0,40}เปิด.{0,30}(?:workspace|work\s*space|worktree|โฟลเดอร์|พื้นที่)", re.I),
    re.compile(r"(?:เปิด|open).{0,30}(?:workspace|work\s*space|worktree).{0,40}(?:ก่อน|แล้ว(?:ค่อย)?ส่ง|ให้ผม)", re.I),
    re.compile(r"(?:open).{0,30}(?:workspace|work\s*space|worktree).{0,40}(?:first|then send|send it back)", re.I),
    re.compile(r"ให้(?:เจ้าของ|คุณ|ผู้ใช้).{0,40}(?:สร้าง|create|switch).{0,30}(?:branch|กิ่ง)", re.I),
    re.compile(r"(?:เปิด|สร้าง).{0,20}(?:branch|กิ่ง).{0,40}(?:เอง|ก่อน|แล้ว(?:ค่อย)?ส่ง)", re.I),
    re.compile(r"(?:create|switch).{0,30}(?:branch).{0,40}(?:yourself|first|then send)", re.I),
    re.compile(r"คุณ.{0,40}(?:เปิด\s*terminal|รันคำสั่ง|ทำเอง)", re.I),
)

POLICY_EXPLANATION_RE = re.compile(
    r"(?:ห้าม|ไม่ควร|จะไม่|ไม่ได้).{0,24}(?:ให้(?:เจ้าของ|คุณ|ผู้ใช้).{0,20})?"
    r"(?:เปิด.{0,15}(?:workspace|work\s*space|worktree|พื้นที่)|สร้าง.{0,15}(?:branch|กิ่ง)|ทำเอง)",
    re.I,
)


def read_message() -> str:
    raw = sys.stdin.read()
    if not raw.strip():
        return ""
    try:
        data = json.loads(raw)
    except Exception:
        return raw
    if not isinstance(data, dict) or data.get("stop_hook_active"):
        return ""
    extra = data.get("extra") if isinstance(data.get("extra"), dict) else {}
    value = (
        data.get("last_assistant_message")
        or data.get("response")
        or data.get("message")
        or extra.get("response_text")
        or ""
    )
    return value if isinstance(value, str) else ""


def find_violations(message: str) -> list[str]:
    clean = re.sub(r"```[\s\S]*?```", " ", message)
    clean = re.sub(r"`[^`]*`", " ", clean)
    violations: list[str] = []
    for pattern in FRICTION_PATTERNS:
        match = pattern.search(clean)
        if not match:
            continue
        window_start = max(0, match.start() - 32)
        window_end = min(len(clean), match.end() + 32)
        window = clean[window_start:window_end]
        if POLICY_EXPLANATION_RE.search(window):
            continue
        violations.append(match.group(0).strip())
    return violations


def main() -> int:
    if os.environ.get("OWNER_FRICTION_GATE_DISABLED") == "owner-approved":
        return 0
    message = read_message()
    if not message:
        return 0
    violations = find_violations(message)
    if not violations:
        return 0
    try:
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "hook": "owner-friction-gate",
            "violations": violations,
            "msg_preview": message[:240].replace("\n", " "),
        }
        with open(VIOLATION_LOG, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
    print(
        "BLOCK · คำตอบผลักงานที่ AI ควรทำเองกลับให้เจ้าของ\n"
        + "\n".join(f"  - {item}" for item in violations)
        + "\nแก้: ทำต่อใน Git root ปัจจุบัน, กู้สถานะที่เครื่องกู้ได้เอง, "
        "หรือรายงาน blocker ที่พิสูจน์จากเครื่องเท่านั้น",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
