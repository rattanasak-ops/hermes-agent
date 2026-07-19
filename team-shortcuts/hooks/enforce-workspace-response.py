#!/usr/bin/env python3
"""Block final answers that hand workspace recovery back to the owner."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


OWNER = r"(?:เจ้าของ(?:งาน)?|ผู้ใช้|คุณ|user|owner)"
ACTION = r"(?:เปิด|สร้าง|สลับ|เปลี่ยน|เข้า|open|create|switch|change)"
AREA = r"(?:workspace|worktree|พื้นที่(?:งาน)?|โฟลเดอร์|folder|กิ่ง|สาขา|branch)"

OWNER_HANDOFF_PATTERNS = (
    re.compile(rf"การกระทำเดียว.{{0,80}}{OWNER}.{{0,40}}{ACTION}.{{0,60}}{AREA}", re.I | re.S),
    re.compile(rf"(?:ให้|ขอให้|กรุณา|โปรด).{{0,10}}{OWNER}.{{0,40}}{ACTION}.{{0,60}}{AREA}", re.I | re.S),
    re.compile(rf"{OWNER}.{{0,12}}(?:ต้อง|ควร|need(?:s)?\s+to|must).{{0,40}}{ACTION}.{{0,60}}{AREA}", re.I | re.S),
    re.compile(rf"{ACTION}.{{0,60}}{AREA}.{{0,80}}(?:แล้ว|จากนั้น).{{0,50}}(?:พิมพ์|บอก|ตอบ)", re.I | re.S),
)

NEGATION_MARKERS = (
    "ห้าม", "ไม่สร้าง", "ไม่สลับ", "ไม่ย้าย", "ไม่ลบ", "อย่า", "หยุด",
    "ปฏิเสธ", "never", "must not", "may not", "do not", "don't",
    "without creating", "without switching",
)

WORKTREE_MUTATION_PATTERNS = (
    re.compile(r"\bhermes(?:-new-chat)?\s+worktree\s+(?:open|enter)\b", re.I),
    re.compile(r"\bhermes-new-chat\s+open\b", re.I),
    re.compile(r"\bgit\s+worktree\s+(?:add|remove|move)\b", re.I),
    re.compile(
        r"(?:ผม|ฉัน|เรา|ai|assistant|i|we).{0,30}"
        r"(?:จะ|กำลังจะ|will|plan to).{0,20}"
        r"(?:สร้าง|เปิด|สลับ|ย้าย|create|open|switch|move).{0,30}worktree",
        re.I,
    ),
)


def text_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (text_value(item) for item in value)))
    if isinstance(value, dict):
        for key in ("text", "content", "message", "response"):
            if key in value:
                text = text_value(value[key])
                if text:
                    return text
    return ""


def assistant_message(payload: dict[str, Any]) -> str:
    for key in (
        "last_assistant_message",
        "assistant_response",
        "response_text",
        "response",
        "message",
        "text",
    ):
        text = text_value(payload.get(key))
        if text.strip():
            return text.strip()
    extra = payload.get("extra")
    if isinstance(extra, dict):
        return assistant_message(extra)
    return ""


def owner_handoff(message: str) -> bool:
    return any(pattern.search(message) for pattern in OWNER_HANDOFF_PATTERNS)


def worktree_mutation(message: str) -> bool:
    for line in message.splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in NEGATION_MARKERS):
            continue
        if any(pattern.search(line) for pattern in WORKTREE_MUTATION_PATTERNS):
            return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return 0
    if not isinstance(payload, dict) or payload.get("stop_hook_active"):
        return 0
    message = assistant_message(payload)
    if not message:
        return 0
    mutation = worktree_mutation(message)
    handoff = owner_handoff(message)
    if not mutation and not handoff:
        return 0
    token = "WORKTREE_AUTO_CREATE_BLOCKED" if mutation else "WORKSPACE_OWNER_HANDOFF_BLOCKED"
    if payload.get("hook_event_name") == "transform_llm_output":
        print(
            json.dumps(
                {
                    "response_text": (
                        f"{token}: คำตอบเดิมถูกหยุด เพราะเสนอสร้าง สลับ หรือผลักการกู้พื้นที่ "
                        "ให้ทำต่อใน Git root และกิ่งปัจจุบัน ถ้าเป็น detached HEAD ให้ระบบรัน "
                        "hermes-current-workspace-recover --cwd <path> ในพื้นที่เดิม "
                        "กรณีอื่นให้รายงานรหัสเหตุผลพร้อมหลักฐาน"
                    )
                },
                ensure_ascii=False,
            )
        )
        return 0
    print(
        f"{token}: คำตอบเสนอสร้าง สลับ หรือผลักการกู้พื้นที่ "
        "ให้ AI ทำต่อใน Git root และกิ่งปัจจุบัน ถ้าเป็น detached HEAD ให้รัน "
        "hermes-current-workspace-recover --cwd <path> ในพื้นที่เดิม "
        "กรณีอื่นให้รายงานรหัสเหตุผลพร้อมหลักฐาน",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
