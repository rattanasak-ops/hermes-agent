#!/usr/bin/env python3
"""Run the three team response gates from one Stop hook."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parent
GATES = (
    "validate-thai-language.py",
    "enforce-codex-review.py",
    "enforce-prompt-evidence.py",
    "owner-friction-gate.py",
    "enforce-workspace-response.py",
    "enforce-phase-autonomy.py",
)

NEXT_ACTION_HEADINGS = (
    "ขั้นตอนถัดไป",
    "next action",
    "next step",
)
HUMAN_SUMMARY_HEADINGS = ("สรุปภาษาคน", "plain-language summary")
NEXT_WORK_HEADINGS = ("งานต่อไปคืออะไร", "what is the next work")
CONTINUATION_PROMPT_HEADINGS = ("Prompt ที่ควรใช้ต่อ", "continuation prompt")
PHASE_TABLE_HEADERS = ("phase", "สถานะ n/m", "%", "แปลเป็นภาษาคน")
EXTERNAL_PENDING_SENTENCE = (
    "งานในเครื่องจบแล้ว เหลือ merge/ระบบภายนอกที่ต้องได้รับอนุมัติหรือสิทธิ์เพิ่ม"
)

NEXT_ACTION_FIELDS = (
    ("ผู้ทำต่อ:", "ผู้ทำ:", "responsible party:", "responsible:"),
    ("ขั้นถัดไป:", "งานถัดไป:", "next task:", "next action:"),
    ("เริ่มเมื่อ:", "start condition:", "start when:"),
    ("หลักฐานปิดด่าน:", "gate evidence:", "done when:", "verification:"),
    ("เจ้าของต้องทำตอนนี้:", "owner action now:"),
    ("เหตุผลที่หยุด:", "stop reason:"),
)

RESUME_FIELDS = ("กลับมาทำต่อที่:", "resume at:", "resume point:")

SUMMARY_TERMS = (
    "สรุป",
    "ผลการทำงาน",
    "ผลตรวจ",
    "สถานะ",
    "ผ่าน",
    "ค้าง",
    "เสร็จ",
    "ปิดงาน",
    "ข้อขัดข้อง",
    "ส่งต่อ",
    "summary",
    "result",
    "status",
    "passed",
    "blocked",
    "complete",
    "handoff",
)

STRONG_SUMMARY_RE = re.compile(
    r"(?:^|\n)\s{0,3}(?:#{1,4}\s*)?"
    r"(?:สรุป(?:ผล)?|ผลการทำงาน|ผลตรวจ|สถานะล่าสุด|ข้อขัดข้อง|ส่งต่องาน|"
    r"summary|results?|status|closeout|handoff)\b",
    re.IGNORECASE,
)

EVIDENCE_RE = re.compile(
    r"(?:\b\d+\s*/\s*\d+\b|\b\d{1,3}\s*%|pytest|tests?\b|"
    r"owner-pending|claimed|verified|tier\s*5|PR\s*#?\d+|"
    r"ไฟล์|ด่าน|หลักฐาน|ผ่าน|ค้าง)",
    re.IGNORECASE,
)

ASK_CONTINUE_RE = re.compile(
    r"(?:พิมพ์|ตอบ|บอก).{0,24}[“\"']?ต่อ[”\"']?|"
    r"ส่ง(?:คำว่า|ข้อความ)\s*[“\"']?ต่อ[”\"']?|"
    r"หากต้องการ.{0,36}ทำต่อ|if you want me to continue|reply.{0,20}continue",
    re.IGNORECASE | re.DOTALL,
)

PENDING_RE = re.compile(
    r"owner[- ]?pending|รอเจ้าของ|PR.{0,20}(?:เปิด|ค้าง|open)|"
    r"merge.{0,20}(?:ค้าง|pending)|tier\s*5.{0,20}0\s*/\s*1|"
    r"ด่าน.{0,20}ค้าง|หลักฐาน.{0,20}ค้าง|\bblocked\b|\bclaimed\b",
    re.IGNORECASE | re.DOTALL,
)
FALSE_COMPLETION_RE = re.compile(
    r"(?:งาน(?:ทั้งหมด)?|ภาพรวม|overall).{0,32}(?:เสร็จ|ครบ|complete)?"
    r".{0,16}\b100\s*%.{0,120}(?:owner[- ]?pending|รอเจ้าของ|ค้าง\s*[1-9]\d*\s*/|pending\s*[1-9]\d*|"
    r"PR.{0,20}(?:เปิด|open)|merge.{0,20}pending)",
    re.IGNORECASE | re.DOTALL,
)

PENDING_COUNT_RE = re.compile(
    r"(?:ค้าง|เหลือ|remaining|pending)\s*[:=]?\s*([1-9]\d*)\s*/\s*\d+",
    re.IGNORECASE,
)
AI_RE = re.compile(r"^(?:AI|เอไอ|ผู้ช่วย)", re.IGNORECASE)
IMMEDIATE_RE = re.compile(r"(?:ทันที|ตอนนี้|เดี๋ยวนี้|immediately|now)", re.IGNORECASE)
OWNER_OR_EXTERNAL_RE = re.compile(
    r"(?:เจ้าของ|ผู้ใช้|ระบบภายนอก|บุคคลภายนอก|owner|external)", re.IGNORECASE
)
CLAIM_TERM_RE = re.compile(
    r"(?:เสร็จ|ผ่าน|ค้าง|complete(?:d)?|pass(?:ed)?|pending)", re.IGNORECASE
)
EXTERNAL_PENDING_RE = re.compile(
    r"(?:งานในเครื่อง|local).{0,60}(?:จบ|เสร็จ|ครบ|complete).{0,120}"
    r"(?:merge|ระบบภายนอก|external|สิทธิ์|อนุมัติ)",
    re.IGNORECASE | re.DOTALL,
)


def _load_hook_payload(payload: str) -> dict:
    try:
        value = json.loads(payload)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _assistant_message(data: dict) -> str:
    value = (
        data.get("last_assistant_message")
        or data.get("response")
        or data.get("message")
        or ""
    )
    return value if isinstance(value, str) else ""


def requires_next_action_contract(message: str) -> bool:
    """Return True for work summaries that must state what happens next."""
    if not message or STRONG_SUMMARY_RE.search(message):
        return bool(message and STRONG_SUMMARY_RE.search(message))
    lowered = message.casefold()
    term_count = sum(1 for term in SUMMARY_TERMS if term.casefold() in lowered)
    return bool(EVIDENCE_RE.search(message) and term_count >= 2)


def _next_action_section(message: str) -> str:
    """Return the last localized next-action section."""
    matches: list[int] = []
    lowered = message.casefold()
    for heading in NEXT_ACTION_HEADINGS:
        index = lowered.rfind(heading.casefold())
        if index >= 0:
            matches.append(index)
    return message[max(matches) :] if matches else ""


def _field_value(section: str, aliases: tuple[str, ...]) -> str:
    for line in section.splitlines():
        clean = line.strip().lstrip("-* ").strip()
        lowered = clean.casefold()
        for alias in aliases:
            if lowered.startswith(alias.casefold()):
                return clean[len(alias) :].strip()
    return ""


def _named_section(message: str, headings: tuple[str, ...]) -> str:
    starts: list[int] = []
    for heading in headings:
        match = re.search(
            rf"(?im)^[ \t]{{0,3}}#{{1,6}}[ \t]*{re.escape(heading)}[ \t]*$",
            message,
        )
        if match:
            starts.append(match.start())
    if not starts:
        return ""
    start = min(starts)
    heading_end = message.find("\n", start)
    if heading_end < 0:
        return ""
    end_match = re.search(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+", message[heading_end + 1 :])
    end = len(message) if not end_match else heading_end + 1 + end_match.start()
    return message[heading_end + 1 : end].strip()


def _has_phase_table(message: str) -> bool:
    for line in message.splitlines():
        clean = [cell.strip().casefold() for cell in line.strip().strip("|").split("|")]
        if tuple(clean) == PHASE_TABLE_HEADERS:
            return True
    return False


def _phase_table_is_complete(message: str) -> bool:
    lines = message.splitlines()
    header_index = -1
    for index, line in enumerate(lines):
        clean = [cell.strip().casefold() for cell in line.strip().strip("|").split("|")]
        if tuple(clean) == PHASE_TABLE_HEADERS:
            header_index = index
            break
    if header_index < 0:
        return False
    rows: list[list[str]] = []
    for line in lines[header_index + 1 :]:
        if not line.strip().startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return bool(rows) and all(
        len(row) == 4
        and re.fullmatch(r"\d+\s*/\s*\d+", row[1])
        and re.fullmatch(r"\d{1,3}(?:\.\d+)?\s*%", row[2])
        for row in rows
    )


def _starts_with_human_summary(message: str) -> bool:
    visible = re.sub(r"^\s*<!--.*?-->\s*", "", message, count=1, flags=re.DOTALL)
    first_heading = re.search(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+([^\n]+)$", visible)
    return bool(
        first_heading
        and first_heading.group(1).strip().casefold()
        in {heading.casefold() for heading in HUMAN_SUMMARY_HEADINGS}
    )


def _claim_lines_without_counts(message: str) -> list[str]:
    bad: list[str] = []
    in_fence = False
    for raw in message.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line or line.startswith("#"):
            continue
        if CLAIM_TERM_RE.search(line) and not (
            re.search(r"\b\d+\s*/\s*\d+\b", line)
            and re.search(r"\b\d{1,3}(?:\.\d+)?\s*%", line)
        ):
            bad.append(line[:120])
    return bad


def next_action_contract_violations(payload: str) -> list[str]:
    """Inspect one Stop-hook payload without changing the response."""
    data = _load_hook_payload(payload)
    if not data or data.get("stop_hook_active"):
        return []

    message = _assistant_message(data)
    if not requires_next_action_contract(message):
        return []

    violations: list[str] = []
    section = _next_action_section(message)

    human_summary = _named_section(message, HUMAN_SUMMARY_HEADINGS)
    if not human_summary:
        violations.append("ไม่มีหัวข้อ ‘สรุปภาษาคน’")
    else:
        if not _starts_with_human_summary(message):
            violations.append("คำตอบไม่ได้ขึ้นต้นด้วยหัวข้อ ‘สรุปภาษาคน’")
        if len([line for line in human_summary.splitlines() if line.strip()]) > 5:
            violations.append("หัวข้อ ‘สรุปภาษาคน’ ยาวเกิน 5 บรรทัด")

    if not _has_phase_table(message):
        violations.append("ไม่มีตาราง Phase ที่มี Phase / สถานะ N/M / % / แปลเป็นภาษาคน")
    elif not _phase_table_is_complete(message):
        violations.append("ตาราง Phase ไม่มีแถวข้อมูล N/M และ % ที่ถูกต้อง")

    next_work = _named_section(message, NEXT_WORK_HEADINGS)
    if not next_work:
        violations.append("ไม่มีหัวข้อ ‘งานต่อไปคืออะไร’ ที่ระบุงานเดียว")
    elif len([
        line for line in next_work.splitlines()
        if re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", line)
    ]) > 1:
        violations.append("หัวข้อ ‘งานต่อไปคืออะไร’ มีมากกว่าหนึ่งงาน")

    if not section:
        violations.append("คำตอบสรุปงานแต่ไม่มีหัวข้อ ‘ขั้นตอนถัดไป’")

    missing_fields = [
        aliases[0].rstrip(":")
        for aliases in NEXT_ACTION_FIELDS
        if not _field_value(section, aliases)
    ]
    if missing_fields:
        violations.append(
            "หัวข้อขั้นตอนถัดไปขาดช่อง " + ", ".join(missing_fields)
        )

    if ASK_CONTINUE_RE.search(message):
        violations.append(
            "คำตอบผลักให้เจ้าของพิมพ์ ‘ต่อ’ แทนการเดินงานปลอดภัยในเฟสเดิม"
        )

    if FALSE_COMPLETION_RE.search(message):
        violations.append(
            "คำตอบรายงาน 100% ทั้งที่ยังมีด่านหรือสถานะค้าง"
        )

    responsible = _field_value(section, NEXT_ACTION_FIELDS[0])
    start_when = _field_value(section, NEXT_ACTION_FIELDS[2])
    if (
        AI_RE.search(responsible)
        and IMMEDIATE_RE.search(start_when)
        and PENDING_COUNT_RE.search(message)
    ):
        violations.append(
            "AI เป็นผู้ทำงานค้างต่อได้ทันที จึงต้องกลับไปทำงานในเฟสเดิมก่อนส่งคำตอบ"
        )

    if OWNER_OR_EXTERNAL_RE.search(responsible):
        if not _named_section(message, CONTINUATION_PROMPT_HEADINGS):
            violations.append("งานรอเจ้าของหรือระบบภายนอกแต่ไม่มี ‘Prompt ที่ควรใช้ต่อ’")
        if not any(_field_value(section, (field,)) for field in RESUME_FIELDS):
            violations.append("งานรอเจ้าของหรือระบบภายนอกแต่ไม่มีจุดกลับมาทำต่อ")

    if EXTERNAL_PENDING_RE.search(message) and EXTERNAL_PENDING_SENTENCE not in message:
        violations.append("งานในเครื่องจบแต่ยังไม่ใช้ประโยคบังคับสำหรับ merge/ระบบภายนอก")

    if _claim_lines_without_counts(message):
        violations.append("คำว่าเสร็จ/ผ่าน/ค้างบางบรรทัดไม่มีทั้ง N/M และ %")

    return violations


def main() -> int:
    payload = sys.stdin.read()
    transform_mode = False
    try:
        parsed_payload = json.loads(payload) if payload.strip() else {}
        transform_mode = (
            isinstance(parsed_payload, dict)
            and parsed_payload.get("hook_event_name") == "transform_llm_output"
        )
    except json.JSONDecodeError:
        transform_mode = False
    blockers: list[str] = []
    for name in GATES:
        path = HOOKS_DIR / name
        if not path.is_file():
            blockers.append(f"ไม่พบด่านตรวจ {path}")
            continue
        proc = subprocess.run(
            [sys.executable, str(path)],
            input=payload,
            text=True,
            capture_output=True,
            timeout=10,
        )
        if proc.returncode == 2:
            if transform_mode:
                text = (proc.stderr or proc.stdout or name).strip()
                print(json.dumps({"response_text": text}, ensure_ascii=False))
                return 0
            blockers.append((proc.stderr or proc.stdout or name).strip())
        elif proc.returncode != 0:
            blockers.append(f"ด่าน {name} ทำงานผิดปกติ exit={proc.returncode}")
        elif transform_mode and proc.stdout.strip():
            try:
                transformed = json.loads(proc.stdout)
            except json.JSONDecodeError:
                transformed = {}
            if isinstance(transformed, dict) and isinstance(
                transformed.get("response_text"), str
            ):
                print(
                    json.dumps(
                        {"response_text": transformed["response_text"]},
                        ensure_ascii=False,
                    )
                )
                return 0

    blockers.extend(next_action_contract_violations(payload))

    if blockers:
        if transform_mode:
            print(
                json.dumps(
                    {"response_text": "\n".join(blockers)},
                    ensure_ascii=False,
                )
            )
            return 0
        print("[Hermes Team Stop Gate] ไม่อนุญาตให้ส่งคำตอบรอบนี้", file=sys.stderr)
        for item in blockers:
            print(f"- {item}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
