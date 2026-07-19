"""ตรวจคำตอบสรุปก่อน Hermes ส่งให้ผู้ใช้."""

from __future__ import annotations

from dataclasses import dataclass
import re


HEADINGS = ("ขั้นตอนถัดไป", "next action", "next step")
HUMAN_SUMMARY_HEADINGS = ("สรุปภาษาคน", "plain-language summary")
PHASE_HEADINGS = ("สรุป Phase", "Phase summary")
NEXT_WORK_HEADINGS = ("งานต่อไปคืออะไร", "what is the next work")
CONTINUATION_PROMPT_HEADINGS = ("Prompt ที่ควรใช้ต่อ", "continuation prompt")
PHASE_TABLE_HEADERS = ("phase", "สถานะ n/m", "%", "แปลเป็นภาษาคน")
EXTERNAL_PENDING_SENTENCE = (
    "งานในเครื่องจบแล้ว เหลือ merge/ระบบภายนอกที่ต้องได้รับอนุมัติหรือสิทธิ์เพิ่ม"
)
FIELDS = (
    ("ผู้ทำต่อ:", "ผู้ทำ:", "responsible party:", "responsible:"),
    ("ขั้นถัดไป:", "งานถัดไป:", "next task:", "next action:"),
    ("เริ่มเมื่อ:", "start condition:", "start when:"),
    ("หลักฐานปิดด่าน:", "gate evidence:", "done when:", "verification:"),
    ("เจ้าของต้องทำตอนนี้:", "owner action now:"),
    ("เหตุผลที่หยุด:", "stop reason:"),
)
RESUME_FIELDS = ("กลับมาทำต่อที่:", "resume at:", "resume point:")

SUMMARY_RE = re.compile(
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
SUMMARY_TERMS = (
    "สรุป", "ผลการทำงาน", "ผลตรวจ", "สถานะ", "ผ่าน", "ค้าง", "เสร็จ",
    "ปิดงาน", "ข้อขัดข้อง", "ส่งต่อ", "summary", "result", "status",
    "passed", "blocked", "complete", "handoff",
)
STATUS_LINE_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:สถานะ|status)\s*:\s*([^\n]+)$"
)
NUMERIC_RE = re.compile(r"(?:\b\d+\s*/\s*\d+\b|\b\d{1,3}\s*%)")
PENDING_COUNT_RE = re.compile(
    r"(?:ค้าง|เหลือ|remaining|pending)\s*[:=]?\s*([1-9]\d*)\s*/\s*\d+",
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


@dataclass(frozen=True)
class ContractResult:
    required: bool
    violations: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.violations

    @property
    def must_continue(self) -> bool:
        return "safe work remains for AI" in self.violations


def requires_contract(message: str) -> bool:
    """คืน True เมื่อข้อความเป็นรายงานงานที่ต้องมีขั้นถัดไป."""
    if not message:
        return False
    if SUMMARY_RE.search(message):
        return True
    lowered = message.casefold()
    term_count = sum(1 for term in SUMMARY_TERMS if term.casefold() in lowered)
    return bool(EVIDENCE_RE.search(message) and term_count >= 2)


def _next_section(message: str) -> str:
    matches: list[tuple[int, str]] = []
    lowered = message.casefold()
    for heading in HEADINGS:
        index = lowered.rfind(heading.casefold())
        if index >= 0:
            matches.append((index, heading))
    if not matches:
        return ""
    return message[max(matches)[0] :]


def _named_section(message: str, headings: tuple[str, ...]) -> str:
    """คืนเนื้อหาของหัวข้อที่ตรง จนถึงหัวข้อ Markdown ถัดไป."""
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


def _field_value(section: str, aliases: tuple[str, ...]) -> str:
    for line in section.splitlines():
        clean = line.strip().lstrip("-* ").strip()
        lowered = clean.casefold()
        for alias in aliases:
            if lowered.startswith(alias.casefold()):
                return clean[len(alias) :].strip()
    return ""


def closeout_only(message: str) -> bool:
    """คืน True เมื่อโมเดลส่งมาเฉพาะบรรทัดสถานะและส่วนขั้นถัดไป."""
    section = _next_section(message)
    if not section:
        return False
    prefix = message[: message.rfind(section)].strip()
    prefix = STATUS_LINE_RE.sub("", prefix).strip().strip("# ")
    return not prefix


def inspect_contract(message: str) -> ContractResult:
    """ตรวจข้อบังคับโดยไม่เปลี่ยนข้อความต้นฉบับ."""
    if not requires_contract(message):
        return ContractResult(required=False, violations=())

    violations: list[str] = []
    human_summary = _named_section(message, HUMAN_SUMMARY_HEADINGS)
    if not human_summary:
        violations.append("missing human summary")
    else:
        if not _starts_with_human_summary(message):
            violations.append("human summary is not first")
        summary_lines = [line for line in human_summary.splitlines() if line.strip()]
        if len(summary_lines) > 5:
            violations.append("human summary exceeds 5 lines")

    if not _has_phase_table(message):
        violations.append("missing Phase table")
    elif not _phase_table_is_complete(message):
        violations.append("Phase table rows missing N/M or %")

    next_work = _named_section(message, NEXT_WORK_HEADINGS)
    if not next_work:
        violations.append("missing single next work")
    else:
        work_items = [
            line for line in next_work.splitlines()
            if re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", line)
        ]
        if len(work_items) > 1:
            violations.append("next work contains more than one item")

    status_match = STATUS_LINE_RE.search(message)
    if (
        not status_match
        or not re.search(r"\b\d+\s*/\s*\d+\b", status_match.group(1))
        or not re.search(r"\b\d{1,3}(?:\.\d+)?\s*%", status_match.group(1))
    ):
        violations.append("missing numeric status")

    section = _next_section(message)
    if not section:
        violations.append("missing Next Action heading")

    missing = [
        aliases[0].rstrip(":")
        for aliases in FIELDS
        if not _field_value(section, aliases)
    ]
    if missing:
        violations.append("missing fields: " + ", ".join(missing))

    if ASK_CONTINUE_RE.search(message):
        violations.append("asks the owner to reply continue")
    if FALSE_COMPLETION_RE.search(message):
        violations.append("claims 100% while pending work remains")

    responsible = _field_value(section, FIELDS[0])
    start_when = _field_value(section, FIELDS[2])
    if (
        AI_RE.search(responsible)
        and IMMEDIATE_RE.search(start_when)
        and PENDING_COUNT_RE.search(message)
    ):
        violations.append("safe work remains for AI")

    if OWNER_OR_EXTERNAL_RE.search(responsible):
        if not _named_section(message, CONTINUATION_PROMPT_HEADINGS):
            violations.append("missing continuation prompt")
        if not any(_field_value(section, (field,)) for field in RESUME_FIELDS):
            violations.append("missing resume point")

    if EXTERNAL_PENDING_RE.search(message) and EXTERNAL_PENDING_SENTENCE not in message:
        violations.append("missing local-done external-pending sentence")

    claim_lines = _claim_lines_without_counts(message)
    if claim_lines:
        violations.append("completion claims missing N/M and %")

    return ContractResult(required=True, violations=tuple(violations))


def repair_instruction(
    violations: tuple[str, ...],
    *,
    section_only: bool = False,
) -> str:
    """สร้างคำสั่งภายในหนึ่งรอบสำหรับแก้คำตอบหรือกลับไปทำงานต่อ."""
    details = "; ".join(violations)
    if "safe work remains for AI" in violations:
        return (
            "[System: The previous response cannot be released because it says "
            "the AI owns immediate work while verified work is still pending. "
            "Continue the approved in-scope work now. Use the available tools, "
            "verify the result, and do not send a final response until the task is "
            "complete or a concrete permission, external-state, scope, or project-rule "
            "blocker is proven. Preserve the original scope and facts.]"
        )
    fields = (
        "a Thai plain-language summary of at most 5 lines, the Phase table with "
        "Phase / Status N/M / % / plain-language meaning, exactly one next-work "
        "item, numeric Status, Responsible party, Next task, Start condition, "
        "Gate evidence, Owner action now, and Stop reason"
    )
    if section_only:
        return (
            "[System: Your previous work summary cannot be released because its "
            f"closeout is incomplete ({details}). Return only the localized Status "
            f"line and Next Action section with: {fields}. If owner or external "
            "action is required, also include the exact resume point. Do not repeat "
            "the summary and do not call tools.]"
        )
    return (
        "[System: Your previous response is a work summary and cannot be released "
        f"because it violates the Next Action Contract ({details}). Rewrite the full "
        "final response in the user's language. Preserve all facts, paths, test "
        f"counts, risks, and status labels. Include {fields}. If owner or external "
        "action is required, request only the smallest action and include the exact "
        "resume point. Never ask the user to reply continue. Do not call tools.]"
    )


def failure_footer(violations: tuple[str, ...]) -> str:
    """แสดงการบล็อกอย่างตรงไปตรงมาเมื่อหมดโอกาสซ่อมคำตอบ."""
    details = "; ".join(violations)
    return (
        "NEXT_ACTION_CONTRACT_BLOCKED\n\n"
        "## สรุปภาษาคน\n\n"
        "ระบบยังจัดคำตอบให้อ่านง่ายไม่สำเร็จ 0/1 = 0% และค้าง 1/1 = 100%\n\n"
        "## สรุป Phase\n\n"
        "| Phase | สถานะ N/M | % | แปลเป็นภาษาคน |\n"
        "|---|---:|---:|---|\n"
        "| จัดรูปคำตอบ | 0/1 | 0% | ยังส่งคำตอบสรุปที่ครบกติกาไม่ได้ |\n\n"
        "## งานต่อไปคืออะไร\n\n"
        "- จัดรูปคำตอบใหม่จากหลักฐานเดิมหนึ่งครั้ง\n\n"
        "สถานะ: ด่านคำตอบผ่าน 0/1 = 0% · ค้าง 1/1 = 100%\n\n"
        "## ขั้นตอนถัดไป\n\n"
        "- ผู้ทำต่อ: AI\n"
        "- ขั้นถัดไป: ไม่ปล่อยคำกล่าวอ้างว่างานครบจนกว่าจะสร้างสรุปจากหลักฐานเดิมได้ถูกต้อง\n"
        "- เริ่มเมื่อ: เมื่อวงสนทนามีรอบเรียกโมเดลเหลือ\n"
        "- หลักฐานปิดด่าน: ด่านคำตอบผ่าน 1/1 โดยไม่แต่งจำนวนหรือสถานะใหม่\n"
        "- เจ้าของต้องทำตอนนี้: ไม่ต้องทำอะไร\n"
        f"- เหตุผลที่หยุด: งบรอบสนทนาหมดหลังด่านพบ {details}"
    )
