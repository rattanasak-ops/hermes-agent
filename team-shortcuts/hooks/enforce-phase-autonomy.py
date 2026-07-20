#!/usr/bin/env python3
"""Keep an approved phase moving while machine-readable safe work remains."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

from phase_state import find_state_path, load_state, phase_summary


ALLOWED_OWNER_INPUT = {
    "LOGIN_REQUIRED", "TOKEN_REQUIRED", "CREDENTIAL_REQUIRED",
    "PRODUCTION_APPROVAL_REQUIRED", "DESTRUCTIVE_APPROVAL_REQUIRED",
    "SCOPE_CHANGE_REQUIRED", "EXTERNAL_DECISION_REQUIRED", "IDENTITY_REQUIRED",
}
OWNER_INPUT_PATTERN = re.compile(r"OWNER_INPUT_REQUIRED:\s*([A-Z_]+)")
EVIDENCE_PATTERN = re.compile(r"(?:หลักฐาน|evidence)\s*:", re.I)
PROGRESS_PATTERN = re.compile(r"ทำแล้ว\s*\d+\s*/\s*\d+\s*=\s*\d+%", re.I)
PENDING_PATTERN = re.compile(r"(?:ค้าง|ต้องทำต่อ)\s*\d+\s*/\s*\d+\s*=\s*\d+%", re.I)
REAPPROVAL_PATTERNS = (
    re.compile(r"(?:อนุมัติ|ยืนยัน|ตกลง|ให้ผม|ต้องการให้ผม|อยากให้ผม).{0,100}(?:ไหม|หรือไม่|\?)", re.I | re.S),
    re.compile(r"(?:ตอบ|พิมพ์|บอก).{0,80}(?:ok|โอเค|อนุมัติ|ยืนยัน|ทำต่อ)", re.I | re.S),
    re.compile(r"(?:มี\s*\d+\s*ทาง|เลือก.{0,30}(?:ทาง|ข้อ))", re.I | re.S),
    re.compile(r"(?:do you want me to|shall i|would you like me to|please approve|please confirm)", re.I),
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
    for key in ("last_assistant_message", "assistant_response", "response_text", "response", "message", "text"):
        text = text_value(payload.get(key))
        if text.strip():
            return text.strip()
    extra = payload.get("extra")
    return assistant_message(extra) if isinstance(extra, dict) else ""


def valid_external_blocker(message: str) -> bool:
    match = OWNER_INPUT_PATTERN.search(message)
    return bool(match and match.group(1) in ALLOWED_OWNER_INPUT and EVIDENCE_PATTERN.search(message))


def repeated_approval(message: str) -> bool:
    return any(pattern.search(message) for pattern in REAPPROVAL_PATTERNS)


def progress_present(message: str) -> bool:
    return bool(PROGRESS_PATTERN.search(message) and PENDING_PATTERN.search(message))


def continuation(summary: dict[str, Any]) -> str:
    return (
        "PHASE_CONTINUATION_REQUIRED: ยังมีงานปลอดภัยในเฟสที่เจ้าของอนุมัติ · "
        f"GOAL_HASH: {str(summary.get('goal_hash') or 'legacy')[:12]} · "
        f"NEXT_SAFE_ISSUE: {summary['next_safe_issue']} · "
        f"ทำแล้ว {summary['verified']}/{summary['total']} = {summary['percent']}% · "
        f"ค้าง {summary['pending']}/{summary['total']} = {summary['remaining_percent']}% · "
        f"ผลงานหลัก {summary['primary_verified']}/{summary['primary_total']} = {summary['primary_percent']}% · "
        f"งานสนับสนุน {summary['support_verified']}/{summary['support_total']} = {summary['support_percent']}% · "
        "ให้เปิดแผน ทวนขอบเขต และทำ Issue นี้ต่อ ห้ามถามอนุมัติซ้ำ"
    )


def legacy_continuation() -> str:
    return (
        "PHASE_CONTINUATION_REQUIRED: คำตอบเดิมถูกหยุด เพราะขออนุมัติซ้ำทั้งที่ยังมี"
        "งานปลอดภัยในเฟสเดิม AI ต้องทำงานต่อจนถึงด่านปิดเฟส หากติดสิทธิ์หรือผลกระทบ"
        "ภายนอกจริง ให้รายงาน OWNER_INPUT_REQUIRED พร้อมรหัสเหตุผลและหลักฐานจากเครื่อง"
        "เพียงครั้งเดียว"
    )


def progress_required(summary: dict[str, Any]) -> str:
    return (
        "PHASE_PROGRESS_REQUIRED: คำตอบต้องรายงานจากสถานะจริง · "
        f"ทำแล้ว {summary['verified']}/{summary['total']} = {summary['percent']}% · "
        f"ค้าง {summary['pending']}/{summary['total']} = {summary['remaining_percent']}% · "
        f"ผลงานหลัก {summary['primary_verified']}/{summary['primary_total']} = {summary['primary_percent']}% · "
        f"งานสนับสนุน {summary['support_verified']}/{summary['support_total']} = {summary['support_percent']}%"
    )


def emit(payload: dict[str, Any], message: str) -> int:
    if payload.get("hook_event_name") == "transform_llm_output":
        print(json.dumps({"response_text": message}, ensure_ascii=False))
        return 0
    print(message, file=sys.stderr)
    return 2


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return 0
    if not isinstance(payload, dict) or payload.get("stop_hook_active"):
        return 0
    state_path = find_state_path(payload.get("cwd") or Path.cwd())
    if state_path is None:
        message = assistant_message(payload)
        if not message or not repeated_approval(message) or valid_external_blocker(message):
            return 0
        return emit(payload, legacy_continuation())
    try:
        state = load_state(state_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return emit(payload, f"PHASE_STATE_INVALID: {exc}")
    if not state.get("active", True):
        return 0
    message = assistant_message(payload)
    summary = phase_summary(state)
    summary["goal_hash"] = state.get("goal_hash")
    if valid_external_blocker(message):
        return 0
    if summary["safe_work_remaining"]:
        return emit(payload, continuation(summary))
    if repeated_approval(message) and not valid_external_blocker(message):
        return emit(payload, "OWNER_INPUT_INVALID: ไม่มีรหัสเหตุผลและหลักฐานจากเครื่อง")
    if not progress_present(message):
        return emit(payload, progress_required(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
