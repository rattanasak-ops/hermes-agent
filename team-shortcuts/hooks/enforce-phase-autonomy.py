#!/usr/bin/env python3
"""Block repeated approval questions while safe work remains in the active phase."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


ALLOWED_OWNER_INPUT = {
    "LOGIN_REQUIRED",
    "TOKEN_REQUIRED",
    "CREDENTIAL_REQUIRED",
    "PRODUCTION_APPROVAL_REQUIRED",
    "DESTRUCTIVE_APPROVAL_REQUIRED",
    "SCOPE_CHANGE_REQUIRED",
    "EXTERNAL_DECISION_REQUIRED",
    "IDENTITY_REQUIRED",
}
OWNER_INPUT_PATTERN = re.compile(r"OWNER_INPUT_REQUIRED:\s*([A-Z_]+)")
EVIDENCE_PATTERN = re.compile(r"(?:หลักฐาน|evidence)\s*:", re.I)
REAPPROVAL_PATTERNS = (
    re.compile(
        r"(?:อนุมัติ|ยืนยัน|ตกลง|ให้ผม|ต้องการให้ผม|อยากให้ผม).{0,100}"
        r"(?:ไหม|หรือไม่|\?)",
        re.I | re.S,
    ),
    re.compile(
        r"(?:ตอบ|พิมพ์|บอก).{0,80}(?:ok|โอเค|อนุมัติ|ยืนยัน|ทำต่อ)",
        re.I | re.S,
    ),
    re.compile(r"(?:มี\s*\d+\s*ทาง|เลือก.{0,30}(?:ทาง|ข้อ))", re.I | re.S),
    re.compile(
        r"(?:do you want me to|shall i|would you like me to|please approve|please confirm)",
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


def valid_external_blocker(message: str) -> bool:
    match = OWNER_INPUT_PATTERN.search(message)
    return bool(
        match
        and match.group(1) in ALLOWED_OWNER_INPUT
        and EVIDENCE_PATTERN.search(message)
    )


def repeated_approval(message: str) -> bool:
    return any(pattern.search(message) for pattern in REAPPROVAL_PATTERNS)


def replacement() -> str:
    return (
        "PHASE_CONTINUATION_REQUIRED: คำตอบเดิมถูกหยุด เพราะขออนุมัติซ้ำทั้งที่ยังมี"
        "งานปลอดภัยในเฟสเดิม AI ต้องทำงานต่อจนถึงด่านปิดเฟส หากติดสิทธิ์หรือผลกระทบ"
        "ภายนอกจริง ให้รายงาน OWNER_INPUT_REQUIRED พร้อมรหัสเหตุผลและหลักฐานจากเครื่อง"
        "เพียงครั้งเดียว"
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return 0
    if not isinstance(payload, dict) or payload.get("stop_hook_active"):
        return 0
    message = assistant_message(payload)
    if not message or not repeated_approval(message) or valid_external_blocker(message):
        return 0
    if payload.get("hook_event_name") == "transform_llm_output":
        print(json.dumps({"response_text": replacement()}, ensure_ascii=False))
        return 0
    print(replacement(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
