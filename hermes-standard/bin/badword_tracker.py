#!/usr/bin/env python3
"""Badword Tracker lab core. It never touches the live hook unless called explicitly."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUSES = {
    "new",
    "investigating",
    "planning",
    "fixing",
    "awaiting_verification",
    "fixed",
    "reopened",
}
TRANSITIONS = {
    "new": {"investigating"},
    "investigating": {"planning"},
    "planning": {"fixing"},
    "fixing": {"awaiting_verification"},
    "awaiting_verification": {"fixing", "fixed"},
    "fixed": {"reopened"},
    "reopened": {"investigating"},
}

TARGET_PATTERNS = {
    "hermes": ("fuck you hermes", "fuck u hermes", "f u hermes", "เหี้ย hermes", "hermes เหี้ย"),
    "output": ("fuck you output", "fuck u output", "f u output", "output เหี้ย", "ผลลัพธ์เหี้ย"),
    "codex": ("fuck you codex", "fuck u codex", "f u codex"),
    "opus": ("fuck you opus", "fuck u opus", "f u opus"),
    "claude": ("fuck you claude", "fuck u claude", "fuck you ai", "fuck u ai", "f u ai"),
    "gemini": ("fuck you gemini", "fuck u gemini", "f u gemini"),
    "grok": ("fuck you grok", "fuck u grok", "f u grok"),
    "fable": ("fuck you fable", "fuck u fable", "fuck you faber", "fuck u faber"),
    "agent": ("fuck you agent", "fuck u agent", "f u agent"),
}
GENERIC_CURSES = (
    "fuck", "fuk", "fck", "f*ck", "f**k", "stfu", "wtf", "bullshit",
    "เหี้ย", "เชี่ย", "ควย", "สัส", "สัด", "แม่ง", "ฉิบหาย", "ชิบหาย",
    "ระยำ", "ส้นตีน", "พ่อง", "มึง",
)

CATEGORY_RULES = (
    ("premature_stop", "AI หยุดงานก่อนจบ", ("งานยังไม่เสร็จ", "ทำไมถึงหยุด", "หยุดทั้งที่ยังไม่เสร็จ", "ทำต่อให้จบ")),
    ("routing", "ส่งงานผิดทาง", ("ผิดห้อง", "ส่งผิด", "ผิดคน", "ผิด ai", "ผิดตัว", "routing")),
    ("preference_memory", "AI ไม่จำข้อกำหนดที่เจ้าของยืนยันแล้ว", ("บอกรอบที่", "บอกไปกี่รอบ", "ไม่ได้ใช้ slack", "กูไม่ได้ใช้")),
    ("memory", "ถามหรือทำเรื่องเดิมซ้ำ", ("ถามซ้ำ", "จำไม่ได้", "ลืม", "ความจำ", "เรื่องเดิมซ้ำ")),
    ("verification", "ไม่ได้ตรวจผลจริงก่อนตอบ", ("ไม่ตรวจ", "ลิงก์เสีย", "ลิงก์ใช้ไม่ได้", "เปิดไม่ได้", "ไม่ได้ทดสอบ")),
    ("tracking", "ระบบติดตามบันทึกไม่ครบ", ("tracking", "ติดตาม", "บันทึกไม่ครบ", "จับไม่ครบ", "ทะเบียน")),
    ("analysis", "วิเคราะห์ไม่ตรงปัญหา", ("ไม่วิเคราะห์", "วิเคราะห์ผิด", "สรุปผิด", "ไม่เข้าใจเป้าหมาย")),
    ("output_quality", "ผลลัพธ์ไม่ตรงคำสั่ง", ("output", "ผลลัพธ์", "คำตอบผิด", "ทำผิด", "ไม่ตรงคำสั่ง")),
    ("language", "ไม่ใช้ภาษาคน", ("ภาษาคน", "อ่านไม่รู้เรื่อง", "ศัพท์ยาก")),
)


@dataclass(frozen=True)
class Classification:
    category: str
    subject: str
    confidence: int
    method: str
    ai_target: str
    trigger_phrase: str
    match_key: str | None


@dataclass(frozen=True)
class Receipt:
    event_id: str
    issue_id: str | None
    category: str
    subject: str
    duplicate: str
    status: str
    count: int

    def text(self) -> str:
        issue = self.issue_id or "ยังไม่เชื่อม"
        labels = {
            "new": "เรื่องใหม่",
            "duplicate": "เรื่องซ้ำ",
            "reopened": "กลับมาเกิดหลังแก้",
            "pending_classification": "รอจัดหมวด",
        }
        return (
            f"บันทึกแล้ว · {self.event_id} · หมวด: {self.category} · เรื่อง: {self.subject} · "
            f"{labels[self.duplicate]} · ปัญหา: {issue} · ครั้งที่ {self.count} · สถานะ: {self.status}"
        )


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS issues (
  issue_id TEXT PRIMARY KEY,
  match_key TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  root_cause TEXT,
  status TEXT NOT NULL,
  owner_id TEXT,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  occurrence_count INTEGER NOT NULL DEFAULT 0,
  fix_count INTEGER NOT NULL DEFAULT 0,
  reopen_count INTEGER NOT NULL DEFAULT 0,
  current_plan TEXT,
  verification_evidence TEXT
);
CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  source_key TEXT NOT NULL UNIQUE,
  occurred_at TEXT NOT NULL,
  received_at TEXT NOT NULL,
  staff_id TEXT NOT NULL,
  device_id TEXT NOT NULL,
  host TEXT NOT NULL,
  project_id TEXT NOT NULL,
  cwd TEXT,
  channel TEXT NOT NULL,
  ai_target TEXT NOT NULL,
  trigger_phrase TEXT NOT NULL,
  message_excerpt_redacted TEXT NOT NULL,
  message_fingerprint TEXT NOT NULL,
  category TEXT NOT NULL,
  subject TEXT NOT NULL,
  classification_confidence INTEGER NOT NULL,
  classification_method TEXT NOT NULL,
  issue_id TEXT REFERENCES issues(issue_id),
  duplicate_state TEXT NOT NULL,
  occurrence_number INTEGER NOT NULL,
  receipt_status TEXT NOT NULL,
  source_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS event_issue_history (
  history_id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL REFERENCES events(event_id),
  issue_id TEXT REFERENCES issues(issue_id),
  action TEXT NOT NULL,
  reason TEXT NOT NULL,
  confidence INTEGER NOT NULL,
  actor TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS status_history (
  history_id INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id TEXT NOT NULL REFERENCES issues(issue_id),
  from_status TEXT,
  to_status TEXT NOT NULL,
  actor TEXT NOT NULL,
  evidence TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS issue_action_history (
  history_id INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id TEXT NOT NULL REFERENCES issues(issue_id),
  action TEXT NOT NULL,
  details TEXT NOT NULL,
  actor TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS delivery_receipts (
  delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT REFERENCES events(event_id),
  destination TEXT NOT NULL,
  status TEXT NOT NULL,
  error TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS device_registry (
  device_id TEXT PRIMARY KEY,
  staff_id TEXT NOT NULL,
  host TEXT NOT NULL,
  platform TEXT NOT NULL,
  rules_version TEXT NOT NULL,
  last_seen_at TEXT,
  enabled INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS outbound_queue (
  queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL REFERENCES events(event_id),
  destination TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending',
  attempt_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(event_id, destination)
);
CREATE INDEX IF NOT EXISTS idx_events_issue ON events(issue_id);
CREATE INDEX IF NOT EXISTS idx_events_dimensions ON events(staff_id, device_id, project_id, ai_target, channel);
CREATE INDEX IF NOT EXISTS idx_outbound_state ON outbound_queue(state, updated_at);

CREATE TABLE IF NOT EXISTS ai_jobs (
  job_id TEXT PRIMARY KEY,
  dedupe_key TEXT NOT NULL,
  action_type TEXT NOT NULL,
  status TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 50,
  title TEXT NOT NULL,
  prompt TEXT NOT NULL,
  event_ids_json TEXT NOT NULL,
  issue_ids_json TEXT NOT NULL,
  filter_snapshot_json TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  result_text TEXT,
  result_saved_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  actor TEXT NOT NULL,
  cancel_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_ai_jobs_status_priority
  ON ai_jobs(status, priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_ai_jobs_dedupe
  ON ai_jobs(dedupe_key, action_type, status);
"""
# Partial unique index is created AFTER migrate_active_ai_job_duplicates()
# so existing active duplicates are resolved safely before the constraint lands.
AI_JOBS_ACTIVE_DEDUPE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_jobs_active_dedupe
  ON ai_jobs(dedupe_key, action_type)
  WHERE status IN ('queued', 'in_progress', 'result_saved');
"""


# AI job queue is status-only: never runs shell, git, relay, or edits product code.
AI_JOB_ACTIONS = {"analyze", "approve"}
AI_JOB_ACTIVE = {"queued", "in_progress", "result_saved"}
AI_JOB_STATUSES = AI_JOB_ACTIVE | {"approved", "cancelled"}
AI_JOB_TRANSITIONS = {
    "queued": {"in_progress", "cancelled", "result_saved", "approved"},
    "in_progress": {"result_saved", "cancelled", "approved"},
    "result_saved": {"approved", "cancelled"},
    "approved": set(),
    "cancelled": set(),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(kind: str) -> str:
    return f"BWT-{kind}-{uuid.uuid4().hex[:12].upper()}"


def normalize_text(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def redact_message(message: str, limit: int = 240) -> str:
    """Strip secrets/PII from free text. Safe for prompts, logs, and UI excerpts."""
    text = str(message or "")
    text = re.sub(r"(?i)(api[_ -]?key|token|password|secret)\s*[:=]\s*\S+", r"\1=[ตัดข้อมูล]", text)
    text = re.sub(
        r"(?i)\b(authorization|bearer)\s+[A-Za-z0-9._\-+/=]+\b",
        r"\1 [ตัดข้อมูล]",
        text,
    )
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[อีเมล]", text)
    text = re.sub(r"(?<!\d)(?:\+?66|0)\d{8,9}(?!\d)", "[โทรศัพท์]", text)
    # Absolute home paths often embed usernames (POSIX + Windows, single or doubled \)
    text = re.sub(r"(?i)(/Users|/home)/[^/\s]+", r"\1/[ผู้ใช้]", text)
    text = re.sub(
        r"(?i)(?:\\\\+|\\)Users(?:\\\\+|\\)[^\\\s]+",
        r"\\Users\\[ผู้ใช้]",
        text,
    )
    return " ".join(text.split())[:limit]


def alias_for(kind: str, value: str) -> str:
    """Stable non-reversible display alias for people/machines (not the real id)."""
    raw = str(value or "").strip() or "unknown"
    digest = hashlib.sha256(f"{kind}|{raw}".encode("utf-8")).hexdigest()[:4].upper()
    labels = {
        "staff": "คน",
        "device": "เครื่อง",
        "host": "โฮสต์",
        "actor": "ผู้ทำ",
    }
    prefix = labels.get(kind, "รหัส")
    return f"{prefix}-{digest}"


def redact_path(path: str) -> str:
    """Keep only a project folder hint — never full home paths with usernames."""
    text = str(path or "").strip()
    if not text:
        return ""
    name = Path(text).name
    return name if name and name not in {".", "/"} else "[โฟลเดอร์]"


def redact_export_text(value: Any, *, limit: int = 2000) -> str:
    """Redact free-text fields that leave the DB via prompts/API/exports."""
    if value is None:
        return ""
    return redact_message(str(value), limit=limit)


# Keys that must never leave export as raw people/machine identifiers.
_IDENTITY_EXPORT_KEYS = {
    "staff_id": ("staff", "staff_alias"),
    "device_id": ("device", "device_alias"),
    "host": ("host", "host_alias"),
    "actor": ("actor", "actor"),
}


def sanitize_json_tree(value: Any, *, str_limit: int = 2000) -> Any:
    """Recursively redact every string leaf in a JSON-compatible tree (export defense).

    Used for evidence_json of older queue rows that may predate write-time redaction.
    Non-string leaves (int/float/bool/None) are kept as-is. Known identity keys
    (staff_id/device_id/host/actor) become stable aliases so raw ids never export.
    """
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            safe_key = redact_export_text(str(key), limit=120)
            cleaned = sanitize_json_tree(item, str_limit=str_limit)
            if safe_key in _IDENTITY_EXPORT_KEYS and isinstance(cleaned, str) and cleaned:
                kind, export_key = _IDENTITY_EXPORT_KEYS[safe_key]
                if not cleaned.startswith(("คน-", "เครื่อง-", "โฮสต์-", "ผู้ทำ-")):
                    cleaned = alias_for(kind, cleaned)
                # Prefer alias field names on export (drop raw id keys)
                out[export_key] = cleaned
                continue
            out[safe_key] = cleaned
        return out
    if isinstance(value, list):
        return [sanitize_json_tree(item, str_limit=str_limit) for item in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact_export_text(value, limit=str_limit)


def sanitize_filter_snapshot(snapshot: Any) -> dict[str, Any]:
    """Deep-copy filter_snapshot and redact string leaves before storage/export."""
    cleaned = sanitize_json_tree(snapshot if isinstance(snapshot, dict) else {}, str_limit=240)
    return cleaned if isinstance(cleaned, dict) else {}


def sanitize_issue_export(issue: dict[str, Any]) -> dict[str, Any]:
    """Redact title/root_cause/current_plan/verification_evidence for export."""
    out = dict(issue)
    for field, limit in (
        ("title", 240),
        ("root_cause", 2000),
        ("current_plan", 2000),
        ("verification_evidence", 2000),
    ):
        if field in out and out[field] is not None:
            out[field] = redact_export_text(out[field], limit=limit)
    return out


def sanitize_ai_job_export(job: dict[str, Any]) -> dict[str, Any]:
    """Redact job fields returned by CLI/API (title, prompt, snapshot, evidence, result).

    Always re-sanitizes evidence_json on get/list so older queue rows with
    pre-redaction blobs cannot leak PII through the API.
    """
    out = dict(job)
    if out.get("title") is not None:
        out["title"] = redact_export_text(out["title"], limit=240)
    if out.get("prompt") is not None:
        out["prompt"] = redact_export_text(out["prompt"], limit=20000)
    if out.get("result_text") is not None:
        out["result_text"] = redact_export_text(out["result_text"], limit=8000)
    if out.get("cancel_reason") is not None:
        out["cancel_reason"] = redact_export_text(out["cancel_reason"], limit=240)
    actor = str(out.get("actor") or "")
    if actor and not actor.startswith(("คน-", "เครื่อง-", "โฮสต์-", "ผู้ทำ-")):
        out["actor"] = alias_for("actor", actor)
    raw_snap = out.get("filter_snapshot_json")
    if isinstance(raw_snap, str) and raw_snap.strip():
        try:
            parsed = json.loads(raw_snap)
        except json.JSONDecodeError:
            parsed = {}
        out["filter_snapshot_json"] = json.dumps(
            sanitize_filter_snapshot(parsed), ensure_ascii=False
        )
    elif "filter_snapshot" in out:
        out["filter_snapshot"] = sanitize_filter_snapshot(out.get("filter_snapshot"))
    # evidence_json: parse → deep-redact every string value → re-serialize
    raw_evidence = out.get("evidence_json")
    if isinstance(raw_evidence, str) and raw_evidence.strip():
        try:
            parsed_ev = json.loads(raw_evidence)
        except json.JSONDecodeError:
            parsed_ev = {}
        out["evidence_json"] = json.dumps(
            sanitize_json_tree(parsed_ev, str_limit=2000), ensure_ascii=False
        )
    elif "evidence" in out and out["evidence"] is not None:
        out["evidence"] = sanitize_json_tree(out["evidence"], str_limit=2000)
    return out


def detect_target(message: str) -> tuple[str, str]:
    low = normalize_text(message)
    for target, phrases in TARGET_PATTERNS.items():
        for phrase in phrases:
            if phrase in low:
                return target, phrase
    for phrase in GENERIC_CURSES:
        if phrase in low:
            return "unknown", phrase
    if "ภาษาคน" in low:
        return "unknown", "ภาษาคน"
    return "unknown", ""


def classify_message(message: str, project_id: str, ai_target: str | None = None) -> Classification:
    low = normalize_text(message)
    detected_target, trigger = detect_target(low)
    target = ai_target or detected_target
    for category, subject, phrases in CATEGORY_RULES:
        if any(phrase in low for phrase in phrases):
            confidence = 92 if category != "output_quality" else 82
            # AI ที่ถูกด่าเป็นมิติรายงาน ไม่ใช่ตัวตัดว่าเป็นคนละปัญหา
            # ปัญหาเดียวกันในโครงการเดียวกันต้องรวมกันแม้เกิดกับ AI คนละตัว
            key_source = f"{project_id}|{category}|{subject}"
            match_key = hashlib.sha256(key_source.encode("utf-8")).hexdigest()
            return Classification(category, subject, confidence, "rule", target, trigger, match_key)
    return Classification(
        "unclassified",
        "รอระบุปัญหา",
        20,
        "rule",
        target,
        trigger,
        None,
    )


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate_active_ai_job_duplicates(conn: sqlite3.Connection) -> dict[str, int]:
    """Resolve active duplicate jobs before the partial unique index is applied.

    Keeps one row per (dedupe_key, action_type) among active statuses
    (highest priority, then earliest created_at, then job_id). Cancels the rest.
    Safe to re-run: no-op when no active duplicates remain.
    """
    rows = list(
        conn.execute(
            """SELECT job_id, dedupe_key, action_type, status, priority, created_at
            FROM ai_jobs
            WHERE status IN ('queued', 'in_progress', 'result_saved')
            ORDER BY dedupe_key, action_type, priority DESC, created_at ASC, job_id ASC"""
        )
    )
    keep: dict[tuple[str, str], str] = {}
    cancel_ids: list[str] = []
    for row in rows:
        key = (row["dedupe_key"], row["action_type"])
        if key not in keep:
            keep[key] = row["job_id"]
        else:
            cancel_ids.append(row["job_id"])
    stamp = now_iso()
    reason = "ยกเลิกอัตโนมัติ: ซ้ำกับคิวก่อน partial unique index (migrate_active_ai_job_duplicates)"
    for job_id in cancel_ids:
        conn.execute(
            """UPDATE ai_jobs
            SET status='cancelled', cancel_reason=?, updated_at=?
            WHERE job_id=? AND status IN ('queued','in_progress','result_saved')""",
            (reason, stamp, job_id),
        )
    return {"kept_active": len(keep), "cancelled_duplicates": len(cancel_ids)}


def ensure_ai_jobs_active_dedupe_index(conn: sqlite3.Connection) -> dict[str, int]:
    """Migrate active duplicates then create partial unique index (idempotent)."""
    stats = migrate_active_ai_job_duplicates(conn)
    conn.execute(AI_JOBS_ACTIVE_DEDUPE_INDEX_SQL)
    return stats


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        ensure_ai_jobs_active_dedupe_index(conn)


def source_key_for(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("source_key") or "").strip()
    if explicit:
        return explicit
    stable = "|".join(
        str(payload.get(key) or "")
        for key in ("ts", "host", "cwd", "category", "phrase", "message")
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _insert_pending_event(conn: sqlite3.Connection, row: dict[str, Any], source_version: str) -> bool:
    source_key = source_key_for(row)
    if conn.execute("SELECT 1 FROM events WHERE source_key=?", (source_key,)).fetchone():
        return False
    event_id = new_id("E")
    occurred = str(row.get("ts") or now_iso())
    excerpt = redact_message(str(row.get("phrase") or row.get("message") or ""))
    fingerprint = hashlib.sha256(excerpt.lower().encode("utf-8")).hexdigest()
    conn.execute(
        """INSERT INTO events (
        event_id, source_key, occurred_at, received_at, staff_id, device_id, host,
        project_id, cwd, channel, ai_target, trigger_phrase, message_excerpt_redacted,
        message_fingerprint, category, subject, classification_confidence,
        classification_method, issue_id, duplicate_state, occurrence_number,
        receipt_status, source_version
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            event_id, source_key, occurred, now_iso(), "owner", str(row.get("host") or "unknown"),
            str(row.get("host") or "unknown"), Path(str(row.get("cwd") or "unknown")).name or "unknown",
            str(row.get("cwd") or ""), "legacy_hook", str(row.get("target") or "unknown"),
            str(row.get("phrase") or ""), excerpt, fingerprint, "unclassified", "รอระบุปัญหา",
            0, "legacy_migration", None, "pending_classification", 1, "pending", source_version,
        ),
    )
    conn.execute(
        """INSERT INTO event_issue_history
        (event_id, issue_id, action, reason, confidence, actor, created_at)
        VALUES (?,NULL,'pending','ข้อมูลเดิมไม่มีรหัสปัญหา ห้ามเดาความสัมพันธ์',0,'migration',?)""",
        (event_id, now_iso()),
    )
    return True


def migrate_jsonl(db_path: Path, source_path: Path, source_version: str = "legacy-v1") -> dict[str, int]:
    init_db(db_path)
    imported = skipped = invalid = 0
    with connect(db_path) as conn, source_path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                invalid += 1
                continue
            if not isinstance(row, dict):
                invalid += 1
                continue
            if _insert_pending_event(conn, row, source_version):
                imported += 1
            else:
                skipped += 1
    return {"imported": imported, "skipped": skipped, "invalid": invalid}


def backfill_phrases_from_jsonl(db_path: Path, source_path: Path, tolerance_seconds: float = 2.0) -> dict[str, int]:
    """เติมคำที่ตัวจับพบให้เหตุการณ์รุ่นก่อน โดยจับคู่เวลา เครื่อง และโฟลเดอร์เดิม."""
    init_db(db_path)
    candidates: list[dict[str, Any]] = []
    invalid = 0
    with source_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                occurred = datetime.fromisoformat(str(row.get("ts") or "").replace("Z", "+00:00"))
            except (json.JSONDecodeError, ValueError):
                invalid += 1
                continue
            phrase = str(row.get("phrase") or "").strip()
            if phrase:
                candidates.append({**row, "occurred": occurred, "phrase": phrase})

    updated = 0
    used_events: set[str] = set()
    with connect(db_path) as conn:
        empty_events = list(conn.execute(
            "SELECT event_id, occurred_at, host, cwd FROM events WHERE trigger_phrase='' AND channel='claude-hook'"
        ))
        for source in candidates:
            matches: list[tuple[float, sqlite3.Row]] = []
            for event in empty_events:
                if event["event_id"] in used_events:
                    continue
                if event["host"] != str(source.get("host") or "") or event["cwd"] != str(source.get("cwd") or ""):
                    continue
                try:
                    event_time = datetime.fromisoformat(str(event["occurred_at"]).replace("Z", "+00:00"))
                except ValueError:
                    continue
                delta = abs((event_time - source["occurred"]).total_seconds())
                if delta <= tolerance_seconds:
                    matches.append((delta, event))
            if not matches:
                continue
            _, event = min(matches, key=lambda item: item[0])
            conn.execute("UPDATE events SET trigger_phrase=? WHERE event_id=?", (source["phrase"], event["event_id"]))
            used_events.add(event["event_id"])
            updated += 1
    return {"updated": updated, "unmatched": len(candidates) - updated, "invalid": invalid}


def record_event(
    db_path: Path,
    message: str,
    *,
    staff_id: str,
    device_id: str,
    host: str,
    project_id: str,
    cwd: str,
    channel: str,
    ai_target: str | None = None,
    trigger_phrase: str | None = None,
    source_key: str | None = None,
    source_version: str = "lab-v1",
) -> Receipt:
    init_db(db_path)
    occurred = now_iso()
    payload = {"source_key": source_key, "ts": occurred, "host": host, "cwd": cwd, "message": message}
    stable_source_key = source_key_for(payload)
    excerpt = redact_message(message)
    classification = classify_message(excerpt, project_id, ai_target)
    detected_phrase = str(trigger_phrase or classification.trigger_phrase or "").strip()
    event_id = new_id("E")
    fingerprint = hashlib.sha256(excerpt.lower().encode("utf-8")).hexdigest()

    with connect(db_path) as conn:
        existing_event = conn.execute(
            "SELECT event_id, issue_id, category, subject, duplicate_state, occurrence_number FROM events WHERE source_key=?",
            (stable_source_key,),
        ).fetchone()
        if existing_event:
            issue_status = "pending"
            if existing_event["issue_id"]:
                row = conn.execute("SELECT status FROM issues WHERE issue_id=?", (existing_event["issue_id"],)).fetchone()
                issue_status = row["status"] if row else "unknown"
            return Receipt(
                existing_event["event_id"], existing_event["issue_id"], existing_event["category"],
                existing_event["subject"], existing_event["duplicate_state"], issue_status,
                existing_event["occurrence_number"],
            )

        issue_id: str | None = None
        duplicate_state = "pending_classification"
        occurrence_number = 1
        issue_status = "pending"

        if classification.match_key and classification.confidence >= 70:
            issue = conn.execute("SELECT * FROM issues WHERE match_key=?", (classification.match_key,)).fetchone()
            if issue is None:
                issue_id = new_id("I")
                issue_status = "new"
                duplicate_state = "new"
                conn.execute(
                    """INSERT INTO issues
                    (issue_id, match_key, title, category, status, first_seen_at, last_seen_at, occurrence_count)
                    VALUES (?,?,?,?,?,?,?,1)""",
                    (issue_id, classification.match_key, classification.subject, classification.category, issue_status, occurred, occurred),
                )
                conn.execute(
                    """INSERT INTO status_history
                    (issue_id, from_status, to_status, actor, evidence, created_at)
                    VALUES (?,NULL,'new','system','สร้างจากกฎที่ผ่านเกณฑ์',?)""",
                    (issue_id, occurred),
                )
            else:
                issue_id = issue["issue_id"]
                occurrence_number = int(issue["occurrence_count"]) + 1
                if issue["status"] == "fixed":
                    duplicate_state = "reopened"
                    issue_status = "reopened"
                    conn.execute(
                        """UPDATE issues SET status='reopened', last_seen_at=?, occurrence_count=?, reopen_count=reopen_count+1
                        WHERE issue_id=?""",
                        (occurred, occurrence_number, issue_id),
                    )
                    conn.execute(
                        """INSERT INTO status_history
                        (issue_id, from_status, to_status, actor, evidence, created_at)
                        VALUES (?,'fixed','reopened','system','มีเหตุการณ์ใหม่หลังแก้',?)""",
                        (issue_id, occurred),
                    )
                else:
                    duplicate_state = "duplicate"
                    issue_status = issue["status"]
                    conn.execute(
                        "UPDATE issues SET last_seen_at=?, occurrence_count=? WHERE issue_id=?",
                        (occurred, occurrence_number, issue_id),
                    )

        conn.execute(
            """INSERT INTO events (
            event_id, source_key, occurred_at, received_at, staff_id, device_id, host,
            project_id, cwd, channel, ai_target, trigger_phrase, message_excerpt_redacted,
            message_fingerprint, category, subject, classification_confidence,
            classification_method, issue_id, duplicate_state, occurrence_number,
            receipt_status, source_version
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event_id, stable_source_key, occurred, now_iso(), staff_id, device_id, host,
                project_id, cwd, channel, classification.ai_target, detected_phrase,
                excerpt, fingerprint, classification.category, classification.subject,
                classification.confidence, classification.method, issue_id, duplicate_state,
                occurrence_number, "shown", source_version,
            ),
        )
        conn.execute(
            """INSERT INTO event_issue_history
            (event_id, issue_id, action, reason, confidence, actor, created_at)
            VALUES (?,?,?,?,?,'system',?)""",
            (
                event_id, issue_id, "linked" if issue_id else "pending",
                "ผ่านกฎและเกณฑ์" if issue_id else "หลักฐานไม่พอ ห้ามเดาความสัมพันธ์",
                classification.confidence, occurred,
            ),
        )
    return Receipt(event_id, issue_id, classification.category, classification.subject, duplicate_state, issue_status, occurrence_number)


def transition_issue(db_path: Path, issue_id: str, to_status: str, actor: str, evidence: str = "") -> None:
    if to_status not in STATUSES:
        raise ValueError(f"ไม่รู้จักสถานะ: {to_status}")
    with connect(db_path) as conn:
        row = conn.execute("SELECT status FROM issues WHERE issue_id=?", (issue_id,)).fetchone()
        if row is None:
            raise ValueError(f"ไม่พบปัญหา: {issue_id}")
        current = row["status"]
        if to_status not in TRANSITIONS.get(current, set()):
            raise ValueError(f"เปลี่ยนสถานะไม่ได้: {current} -> {to_status}")
        fix_add = 1 if to_status == "fixed" else 0
        conn.execute(
            "UPDATE issues SET status=?, fix_count=fix_count+? WHERE issue_id=?",
            (to_status, fix_add, issue_id),
        )
        conn.execute(
            """INSERT INTO status_history
            (issue_id, from_status, to_status, actor, evidence, created_at)
            VALUES (?,?,?,?,?,?)""",
            (issue_id, current, to_status, actor, evidence, now_iso()),
        )


def update_issue_work(
    db_path: Path,
    issue_id: str,
    *,
    actor: str,
    owner_id: str | None = None,
    current_plan: str | None = None,
    verification_evidence: str | None = None,
) -> None:
    values = {
        "owner_id": owner_id,
        "current_plan": current_plan,
        "verification_evidence": verification_evidence,
    }
    changes = {key: value.strip() for key, value in values.items() if value is not None and value.strip()}
    if not changes:
        raise ValueError("ต้องส่งผู้รับผิดชอบ แผนแก้ หรือหลักฐานอย่างน้อย 1 ช่อง")
    with connect(db_path) as conn:
        if conn.execute("SELECT 1 FROM issues WHERE issue_id=?", (issue_id,)).fetchone() is None:
            raise ValueError(f"ไม่พบปัญหา: {issue_id}")
        assignments = ", ".join(f"{column}=?" for column in changes)
        conn.execute(
            f"UPDATE issues SET {assignments} WHERE issue_id=?",
            (*changes.values(), issue_id),
        )
        conn.execute(
            """INSERT INTO issue_action_history
            (issue_id, action, details, actor, created_at) VALUES (?,?,?,?,?)""",
            (issue_id, "work_updated", json.dumps(changes, ensure_ascii=False), actor, now_iso()),
        )


def register_device(
    db_path: Path,
    *,
    device_id: str,
    staff_id: str,
    host: str,
    platform: str,
    rules_version: str,
    enabled: bool = False,
) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """INSERT INTO device_registry
            (device_id, staff_id, host, platform, rules_version, last_seen_at, enabled)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(device_id) DO UPDATE SET
              staff_id=excluded.staff_id,
              host=excluded.host,
              platform=excluded.platform,
              rules_version=excluded.rules_version,
              last_seen_at=excluded.last_seen_at,
              enabled=excluded.enabled""",
            (device_id, staff_id, host, platform, rules_version, now_iso(), int(enabled)),
        )


def queue_delivery(db_path: Path, event_id: str, destination: str) -> bool:
    """Queue once per event and destination; return False for an existing item."""
    with connect(db_path) as conn:
        if conn.execute("SELECT 1 FROM events WHERE event_id=?", (event_id,)).fetchone() is None:
            raise ValueError(f"ไม่พบเหตุการณ์: {event_id}")
        stamp = now_iso()
        cursor = conn.execute(
            """INSERT OR IGNORE INTO outbound_queue
            (event_id, destination, state, created_at, updated_at)
            VALUES (?,?,'pending',?,?)""",
            (event_id, destination, stamp, stamp),
        )
        return cursor.rowcount == 1


def mark_delivery_result(
    db_path: Path,
    event_id: str,
    destination: str,
    *,
    success: bool,
    error: str = "",
) -> None:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT queue_id FROM outbound_queue WHERE event_id=? AND destination=?",
            (event_id, destination),
        ).fetchone()
        if row is None:
            raise ValueError("ไม่พบรายการในคิวส่ง")
        state = "delivered" if success else "pending"
        cleaned_error = "" if success else redact_message(error, limit=160)
        conn.execute(
            """UPDATE outbound_queue SET state=?, attempt_count=attempt_count+1,
            last_error=?, updated_at=? WHERE queue_id=?""",
            (state, cleaned_error or None, now_iso(), row["queue_id"]),
        )
        conn.execute(
            """INSERT INTO delivery_receipts
            (event_id, destination, status, error, created_at) VALUES (?,?,?,?,?)""",
            (event_id, destination, "sent" if success else "failed", cleaned_error or None, now_iso()),
        )


def health_alerts(db_path: Path, *, stale_before: str) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    with connect(db_path) as conn:
        for row in conn.execute(
            """SELECT device_id, staff_id, last_seen_at FROM device_registry
            WHERE enabled=1 AND (last_seen_at IS NULL OR last_seen_at < ?)""",
            (stale_before,),
        ):
            device_alias = alias_for("device", row["device_id"])
            staff_alias = alias_for("staff", row["staff_id"])
            alerts.append({
                "kind": "device_stale",
                "key": device_alias,
                "message": f"เครื่อง {device_alias} ของ {staff_alias} หยุดส่งข้อมูล",
            })
        pending = conn.execute("SELECT COUNT(*) FROM outbound_queue WHERE state='pending'").fetchone()[0]
        if pending:
            alerts.append({
                "kind": "delivery_pending",
                "key": str(pending),
                "message": f"มีข้อมูลรอส่ง {pending} รายการ",
            })
    return alerts


def _refresh_issue_counts(conn: sqlite3.Connection, issue_id: str) -> None:
    """Rebuild derived counters after a manual link correction."""
    row = conn.execute(
        """SELECT COUNT(*) AS occurrences,
        SUM(CASE WHEN duplicate_state='reopened' THEN 1 ELSE 0 END) AS reopened
        FROM events WHERE issue_id=?""",
        (issue_id,),
    ).fetchone()
    conn.execute(
        "UPDATE issues SET occurrence_count=?, reopen_count=? WHERE issue_id=?",
        (int(row["occurrences"] or 0), int(row["reopened"] or 0), issue_id),
    )


def correct_event_link(
    db_path: Path,
    event_id: str,
    issue_id: str | None,
    *,
    actor: str,
    reason: str,
) -> None:
    """Move an event to another issue, or return it to pending, without erasing history."""
    if not reason.strip():
        raise ValueError("ต้องระบุเหตุผลในการแก้ความสัมพันธ์")
    with connect(db_path) as conn:
        event = conn.execute(
            "SELECT issue_id FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
        if event is None:
            raise ValueError(f"ไม่พบเหตุการณ์: {event_id}")
        old_issue_id = event["issue_id"]
        if old_issue_id == issue_id:
            raise ValueError("เหตุการณ์เชื่อมกับปัญหานี้อยู่แล้ว")
        if issue_id is not None:
            target = conn.execute(
                "SELECT status, occurrence_count FROM issues WHERE issue_id=?", (issue_id,)
            ).fetchone()
            if target is None:
                raise ValueError(f"ไม่พบปัญหา: {issue_id}")
            duplicate_state = "new" if int(target["occurrence_count"]) == 0 else "duplicate"
            occurrence_number = int(target["occurrence_count"]) + 1
            receipt_status = "shown"
            action = "relinked" if old_issue_id else "linked_manual"
        else:
            duplicate_state = "pending_classification"
            occurrence_number = 1
            receipt_status = "pending"
            action = "unlinked"
        conn.execute(
            """UPDATE events SET issue_id=?, duplicate_state=?, occurrence_number=?,
            receipt_status=?, classification_method='manual_correction'
            WHERE event_id=?""",
            (issue_id, duplicate_state, occurrence_number, receipt_status, event_id),
        )
        conn.execute(
            """INSERT INTO event_issue_history
            (event_id, issue_id, action, reason, confidence, actor, created_at)
            VALUES (?,?,?,?,100,?,?)""",
            (event_id, issue_id, action, reason.strip(), actor, now_iso()),
        )
        if old_issue_id:
            _refresh_issue_counts(conn, old_issue_id)
        if issue_id:
            _refresh_issue_counts(conn, issue_id)


def summary(db_path: Path) -> dict[str, Any]:
    init_db(db_path)
    with connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM events WHERE issue_id IS NULL").fetchone()[0]
        issues = conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
        reopened = conn.execute("SELECT COUNT(*) FROM events WHERE duplicate_state='reopened'").fetchone()[0]
        jobs = conn.execute("SELECT COUNT(*) FROM ai_jobs").fetchone()[0]
        active_jobs = conn.execute(
            "SELECT COUNT(*) FROM ai_jobs WHERE status IN ('queued','in_progress','result_saved')"
        ).fetchone()[0]
        return {
            "events": total,
            "pending": pending,
            "linked": total - pending,
            "issues": issues,
            "reopened": reopened,
            "ai_jobs": jobs,
            "ai_jobs_active": active_jobs,
        }


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def _normalize_event_ids(event_ids: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    cleaned = sorted({str(item).strip() for item in event_ids if str(item).strip()})
    if not cleaned:
        raise ValueError("ต้องระบุเหตุการณ์อย่างน้อย 1 รายการ")
    return cleaned


def _job_dedupe_key(action_type: str, event_ids: list[str]) -> str:
    payload = f"{action_type}|{'|'.join(event_ids)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_ai_prompt(
    db_path: Path,
    event_ids: list[str],
    *,
    action_type: str = "analyze",
) -> dict[str, Any]:
    """Build a redacted work-order prompt from evidence only. No side effects."""
    if action_type not in AI_JOB_ACTIONS:
        raise ValueError(f"ไม่รู้จักชนิดงาน: {action_type}")
    ids = _normalize_event_ids(event_ids)
    init_db(db_path)
    with connect(db_path) as conn:
        placeholders = ",".join("?" for _ in ids)
        events = list(
            conn.execute(
                f"""SELECT event_id, occurred_at, staff_id, device_id, host, project_id, cwd,
                channel, ai_target, trigger_phrase, message_excerpt_redacted, category, subject,
                issue_id, duplicate_state, occurrence_number, source_version
                FROM events WHERE event_id IN ({placeholders})
                ORDER BY occurred_at DESC""",
                ids,
            )
        )
        if len(events) != len(ids):
            found = {row["event_id"] for row in events}
            missing = [item for item in ids if item not in found]
            raise ValueError(f"ไม่พบเหตุการณ์: {', '.join(missing)}")

        issue_ids = sorted({row["issue_id"] for row in events if row["issue_id"]})
        issues: list[sqlite3.Row] = []
        if issue_ids:
            i_ph = ",".join("?" for _ in issue_ids)
            issues = list(
                conn.execute(
                    f"""SELECT issue_id, title, category, status, root_cause, occurrence_count,
                    fix_count, reopen_count, current_plan, verification_evidence
                    FROM issues WHERE issue_id IN ({i_ph}) ORDER BY last_seen_at DESC""",
                    issue_ids,
                )
            )

    evidence_events = []
    for row in events:
        evidence_events.append({
            "event_id": row["event_id"],
            "occurred_at": row["occurred_at"],
            # Display aliases only — real staff/device/host never leave the DB via prompts
            "staff_alias": alias_for("staff", row["staff_id"]),
            "device_alias": alias_for("device", row["device_id"]),
            "host_alias": alias_for("host", row["host"]),
            "project_id": row["project_id"],
            "channel": row["channel"],
            "ai_target": row["ai_target"],
            "trigger_phrase": row["trigger_phrase"],
            "category": row["category"],
            "subject": row["subject"],
            "issue_id": row["issue_id"],
            "duplicate_state": row["duplicate_state"],
            "occurrence_number": row["occurrence_number"],
            "message_excerpt_redacted": redact_message(row["message_excerpt_redacted"] or ""),
            "project_path_hint": redact_path(str(row["cwd"] or "")),
            "source_version": row["source_version"],
        })
    evidence_issues = []
    for row in issues:
        raw = _row_to_dict(row) or {}
        evidence_issues.append(sanitize_issue_export(raw))
    action_label = "วิเคราะห์หารากปัญหา" if action_type == "analyze" else "เตรียมอนุมัติแผนแก้ (สถานะคิวเท่านั้น)"
    lines = [
        f"# ใบงาน Badword Tracker · {action_label}",
        "",
        "กติกาบังคับ:",
        "- ใช้หลักฐานด้านล่างเท่านั้น ห้ามเดา",
        "- ข้อความถูกตัดข้อมูลส่วนตัวแล้ว (อีเมล/โทรศัพท์/token/path) · คน/เครื่องเป็นนามแฝง",
        "- ช่อง title / root_cause / current_plan / verification_evidence ถูกตัดข้อมูลส่วนตัวก่อนใส่ใบงาน",
        "- ห้ามเรียก shell, git, relay หรือแก้โค้ดจากใบงานนี้โดยตรง",
        "- งานนี้เป็นคิวสถานะ: บันทึกผล/อนุมัติ/ยกเลิกผ่าน API เท่านั้น",
        "- ยังไม่มี worker AI Auto ทั้งเส้น — คนคัดลอกใบงานไปรันภายนอกเอง",
        "",
        f"จำนวนเหตุการณ์: {len(evidence_events)}",
        f"จำนวนปัญหาที่ผูกแล้ว: {len(evidence_issues)}",
        "",
        "## เหตุการณ์ (ตัดข้อมูลส่วนตัวแล้ว · นามแฝงคน/เครื่อง)",
    ]
    for item in evidence_events:
        lines.extend([
            f"### {item['event_id']}",
            f"- เวลา: {item['occurred_at']}",
            f"- คำที่จับได้: {item['trigger_phrase'] or 'ไม่ระบุ'}",
            f"- หมวด/เรื่อง: {item['category']} / {item['subject']}",
            f"- โครงการ / AI: {item['project_id']} / {item['ai_target']}",
            f"- คน / เครื่อง / โฮสต์ / ช่องทาง: {item['staff_alias']} / {item['device_alias']} / {item['host_alias']} / {item['channel']}",
            f"- สถานะซ้ำ: {item['duplicate_state']} ครั้งที่ {item['occurrence_number']}",
            f"- ปัญหา: {item['issue_id'] or 'รอจัดหมวด'}",
            f"- โฟลเดอร์โครงการ (ชื่ออย่างเดียว): {item['project_path_hint'] or '-'}",
            f"- ข้อความย่อ: {item['message_excerpt_redacted']}",
            "",
        ])
    if evidence_issues:
        lines.append("## ปัญหาที่ผูกแล้ว")
        for issue in evidence_issues:
            lines.extend([
                f"### {issue['issue_id']}",
                f"- ชื่อ: {issue.get('title') or '-'}",
                f"- หมวด/สถานะ: {issue.get('category')} / {issue.get('status')}",
                f"- นับเหตุการณ์/แก้/กลับมาเกิด: {issue.get('occurrence_count')}/{issue.get('fix_count')}/{issue.get('reopen_count')}",
                f"- แผนปัจจุบัน: {issue.get('current_plan') or '-'}",
                f"- หลักฐานตรวจ: {issue.get('verification_evidence') or '-'}",
                f"- root cause: {issue.get('root_cause') or '-'}",
                "",
            ])
    lines.extend([
        "## สิ่งที่ต้องส่งกลับ",
        "1) สาเหตุที่เป็นไปได้ (อิงหลักฐาน)",
        "2) หลักฐานที่สนับสนุน",
        "3) แผนแก้ทีละขั้น",
        "4) วิธีตรวจหลังแก้",
        "5) ความเสี่ยงถ้ายังไม่แก้",
    ])
    # Final pass: redact any residual secrets in the assembled prompt
    prompt = redact_export_text("\n".join(lines), limit=20000)
    return {
        "action_type": action_type,
        "event_ids": ids,
        "issue_ids": issue_ids,
        "prompt": prompt,
        "evidence": {"events": evidence_events, "issues": evidence_issues},
    }


def create_ai_job(
    db_path: Path,
    event_ids: list[str],
    *,
    action_type: str = "analyze",
    priority: int = 50,
    actor: str = "owner",
    filter_snapshot: dict[str, Any] | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Queue an AI work order. Does not call models, shell, git, or relay."""
    if action_type not in AI_JOB_ACTIONS:
        raise ValueError(f"ไม่รู้จักชนิดงาน: {action_type}")
    try:
        priority_value = int(priority)
    except (TypeError, ValueError) as exc:
        raise ValueError("priority ต้องเป็นจำนวนเต็ม") from exc
    if priority_value < 1 or priority_value > 100:
        raise ValueError("priority ต้องอยู่ระหว่าง 1-100")

    built = build_ai_prompt(db_path, event_ids, action_type=action_type)
    ids = built["event_ids"]
    dedupe_key = _job_dedupe_key(action_type, ids)
    stamp = now_iso()
    actor_alias = alias_for("actor", actor)
    raw_title = title or (
        f"วิเคราะห์ {len(ids)} เหตุการณ์" if action_type == "analyze" else f"อนุมัติคิว {len(ids)} เหตุการณ์"
    )
    job_title = redact_export_text(raw_title, limit=240)
    safe_snapshot = sanitize_filter_snapshot(filter_snapshot or {})

    init_db(db_path)
    # BEGIN IMMEDIATE + partial UNIQUE index = atomic dedupe under concurrency
    conn = connect(db_path)
    try:
        # Autocommit off the implicit txn so we own BEGIN IMMEDIATE explicitly
        previous_isolation = conn.isolation_level
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        job_id = new_id("J")
        try:
            conn.execute(
                """INSERT INTO ai_jobs (
                job_id, dedupe_key, action_type, status, priority, title, prompt,
                event_ids_json, issue_ids_json, filter_snapshot_json, evidence_json,
                result_text, result_saved_at, created_at, updated_at, actor, cancel_reason
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,?,?,?,NULL)""",
                (
                    job_id,
                    dedupe_key,
                    action_type,
                    "queued",
                    priority_value,
                    job_title,
                    built["prompt"],
                    json.dumps(ids, ensure_ascii=False),
                    json.dumps(built["issue_ids"], ensure_ascii=False),
                    json.dumps(safe_snapshot, ensure_ascii=False),
                    json.dumps(built["evidence"], ensure_ascii=False),
                    stamp,
                    stamp,
                    actor_alias,
                ),
            )
            conn.execute("COMMIT")
        except sqlite3.IntegrityError:
            conn.execute("ROLLBACK")
            existing = conn.execute(
                """SELECT * FROM ai_jobs
                WHERE dedupe_key=? AND action_type=? AND status IN ('queued','in_progress','result_saved')
                ORDER BY priority DESC, created_at ASC LIMIT 1""",
                (dedupe_key, action_type),
            ).fetchone()
            if existing is None:
                raise
            row = sanitize_ai_job_export(_row_to_dict(existing) or {})
            row["created"] = False
            row["duplicate_blocked"] = True
            return row
        finally:
            conn.isolation_level = previous_isolation
        row = sanitize_ai_job_export(
            _row_to_dict(conn.execute("SELECT * FROM ai_jobs WHERE job_id=?", (job_id,)).fetchone()) or {}
        )
        row["created"] = True
        row["duplicate_blocked"] = False
        return row
    finally:
        conn.close()


def list_ai_jobs(
    db_path: Path,
    *,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    init_db(db_path)
    limit = max(1, min(int(limit), 500))
    with connect(db_path) as conn:
        if status:
            if status not in AI_JOB_STATUSES:
                raise ValueError(f"ไม่รู้จักสถานะงาน: {status}")
            rows = conn.execute(
                """SELECT * FROM ai_jobs WHERE status=?
                ORDER BY priority DESC, created_at ASC LIMIT ?""",
                (status, limit),
            )
        else:
            rows = conn.execute(
                """SELECT * FROM ai_jobs
                ORDER BY
                  CASE status
                    WHEN 'queued' THEN 0
                    WHEN 'in_progress' THEN 1
                    WHEN 'result_saved' THEN 2
                    WHEN 'approved' THEN 3
                    ELSE 4
                  END,
                  priority DESC, created_at ASC
                LIMIT ?""",
                (limit,),
            )
        return [sanitize_ai_job_export(d) for d in (_row_to_dict(row) for row in rows) if d]


def get_ai_job(db_path: Path, job_id: str) -> dict[str, Any]:
    init_db(db_path)
    with connect(db_path) as conn:
        row = _row_to_dict(conn.execute("SELECT * FROM ai_jobs WHERE job_id=?", (job_id,)).fetchone())
    if row is None:
        raise ValueError(f"ไม่พบงาน: {job_id}")
    return sanitize_ai_job_export(row)


def save_ai_job_result(db_path: Path, job_id: str, result_text: str, *, actor: str = "owner") -> dict[str, Any]:
    text = redact_message(str(result_text or "").strip(), limit=8000)
    if not text:
        raise ValueError("ต้องมีข้อความผลลัพธ์")
    stamp = now_iso()
    actor_alias = alias_for("actor", actor)
    with connect(db_path) as conn:
        row = conn.execute("SELECT status FROM ai_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise ValueError(f"ไม่พบงาน: {job_id}")
        current = row["status"]
        if "result_saved" not in AI_JOB_TRANSITIONS.get(current, set()) and current != "result_saved":
            raise ValueError(f"บันทึกผลไม่ได้จากสถานะ {current}")
        conn.execute(
            """UPDATE ai_jobs SET status='result_saved', result_text=?, result_saved_at=?,
            updated_at=?, actor=? WHERE job_id=?""",
            (text, stamp, stamp, actor_alias, job_id),
        )
    # Read after the write transaction commits — nested get inside `with` sees old status.
    return get_ai_job(db_path, job_id)


def approve_ai_job(db_path: Path, job_id: str, *, actor: str = "owner") -> dict[str, Any]:
    """Mark job approved. Status only — no code changes, shell, git, or relay."""
    stamp = now_iso()
    actor_alias = alias_for("actor", actor)
    with connect(db_path) as conn:
        row = conn.execute("SELECT status FROM ai_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise ValueError(f"ไม่พบงาน: {job_id}")
        current = row["status"]
        if "approved" not in AI_JOB_TRANSITIONS.get(current, set()):
            raise ValueError(f"อนุมัติไม่ได้จากสถานะ {current}")
        conn.execute(
            "UPDATE ai_jobs SET status='approved', updated_at=?, actor=? WHERE job_id=?",
            (stamp, actor_alias, job_id),
        )
    return get_ai_job(db_path, job_id)


def cancel_ai_job(
    db_path: Path,
    job_id: str,
    *,
    actor: str = "owner",
    reason: str = "",
) -> dict[str, Any]:
    stamp = now_iso()
    cleaned = redact_message(reason, limit=240) if reason else ""
    actor_alias = alias_for("actor", actor)
    with connect(db_path) as conn:
        row = conn.execute("SELECT status FROM ai_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise ValueError(f"ไม่พบงาน: {job_id}")
        current = row["status"]
        if "cancelled" not in AI_JOB_TRANSITIONS.get(current, set()):
            raise ValueError(f"ยกเลิกไม่ได้จากสถานะ {current}")
        conn.execute(
            """UPDATE ai_jobs SET status='cancelled', cancel_reason=?, updated_at=?, actor=?
            WHERE job_id=?""",
            (cleaned or None, stamp, actor_alias, job_id),
        )
    return get_ai_job(db_path, job_id)


def mark_ai_job_in_progress(db_path: Path, job_id: str, *, actor: str = "owner") -> dict[str, Any]:
    stamp = now_iso()
    actor_alias = alias_for("actor", actor)
    with connect(db_path) as conn:
        row = conn.execute("SELECT status FROM ai_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise ValueError(f"ไม่พบงาน: {job_id}")
        current = row["status"]
        if "in_progress" not in AI_JOB_TRANSITIONS.get(current, set()):
            raise ValueError(f"เริ่มงานไม่ได้จากสถานะ {current}")
        conn.execute(
            "UPDATE ai_jobs SET status='in_progress', updated_at=?, actor=? WHERE job_id=?",
            (stamp, actor_alias, job_id),
        )
    return get_ai_job(db_path, job_id)


def list_events(
    db_path: Path,
    *,
    limit: int = 500,
) -> list[dict[str, Any]]:
    init_db(db_path)
    limit = max(1, min(int(limit), 2000))
    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT e.*, COALESCE(i.status, 'pending') AS issue_status
            FROM events e LEFT JOIN issues i ON i.issue_id=e.issue_id
            ORDER BY e.occurred_at DESC LIMIT ?""",
            (limit,),
        )
        return [_row_to_dict(row) for row in rows]  # type: ignore[misc]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    migrate = sub.add_parser("migrate")
    migrate.add_argument("--from", dest="source", type=Path, required=True)
    backfill = sub.add_parser("backfill-phrases")
    backfill.add_argument("--from", dest="source", type=Path, required=True)
    record = sub.add_parser("record")
    record.add_argument("message")
    record.add_argument("--staff", default="owner")
    record.add_argument("--device", default="owner-mac")
    record.add_argument("--host", default="unknown")
    record.add_argument("--project", default="unknown")
    record.add_argument("--cwd", default="")
    record.add_argument("--channel", default="manual")
    record.add_argument("--target")
    record.add_argument("--phrase")
    record.add_argument("--source-key")
    status = sub.add_parser("status")
    status.add_argument("issue_id")
    status.add_argument("to_status")
    status.add_argument("--actor", default="owner")
    status.add_argument("--evidence", default="")
    unlink = sub.add_parser("unlink")
    unlink.add_argument("event_id")
    unlink.add_argument("--actor", default="owner")
    unlink.add_argument("--reason", required=True)
    link = sub.add_parser("link")
    link.add_argument("event_id")
    link.add_argument("issue_id")
    link.add_argument("--actor", default="owner")
    link.add_argument("--reason", required=True)
    queue = sub.add_parser("queue-job")
    queue.add_argument("event_ids", nargs="+")
    queue.add_argument("--action", default="analyze", choices=sorted(AI_JOB_ACTIONS))
    queue.add_argument("--priority", type=int, default=50)
    queue.add_argument("--actor", default="owner")
    queue.add_argument("--title")
    job_show = sub.add_parser("show-job")
    job_show.add_argument("job_id")
    job_list = sub.add_parser("list-jobs")
    job_list.add_argument("--status")
    job_list.add_argument("--limit", type=int, default=100)
    job_result = sub.add_parser("save-result")
    job_result.add_argument("job_id")
    job_result.add_argument("--result", required=True)
    job_result.add_argument("--actor", default="owner")
    job_approve = sub.add_parser("approve-job")
    job_approve.add_argument("job_id")
    job_approve.add_argument("--actor", default="owner")
    job_cancel = sub.add_parser("cancel-job")
    job_cancel.add_argument("job_id")
    job_cancel.add_argument("--actor", default="owner")
    job_cancel.add_argument("--reason", default="")
    sub.add_parser("summary")
    args = parser.parse_args()

    if args.command == "init":
        init_db(args.db)
        result: Any = {"status": "initialized", "db": str(args.db)}
    elif args.command == "migrate":
        result = migrate_jsonl(args.db, args.source)
    elif args.command == "backfill-phrases":
        result = backfill_phrases_from_jsonl(args.db, args.source)
    elif args.command == "record":
        receipt = record_event(
            args.db, args.message, staff_id=args.staff, device_id=args.device,
            host=args.host, project_id=args.project, cwd=args.cwd, channel=args.channel,
            ai_target=args.target, trigger_phrase=args.phrase, source_key=args.source_key,
        )
        result = {**asdict(receipt), "text": receipt.text()}
    elif args.command == "status":
        transition_issue(args.db, args.issue_id, args.to_status, args.actor, args.evidence)
        result = {"status": "updated", "issue_id": args.issue_id, "to": args.to_status}
    elif args.command == "unlink":
        correct_event_link(args.db, args.event_id, None, actor=args.actor, reason=args.reason)
        result = {"status": "pending", "event_id": args.event_id}
    elif args.command == "link":
        correct_event_link(args.db, args.event_id, args.issue_id, actor=args.actor, reason=args.reason)
        result = {"status": "linked", "event_id": args.event_id, "issue_id": args.issue_id}
    elif args.command == "queue-job":
        result = create_ai_job(
            args.db,
            args.event_ids,
            action_type=args.action,
            priority=args.priority,
            actor=args.actor,
            title=args.title,
        )
    elif args.command == "show-job":
        result = get_ai_job(args.db, args.job_id)
    elif args.command == "list-jobs":
        result = list_ai_jobs(args.db, status=args.status, limit=args.limit)
    elif args.command == "save-result":
        result = save_ai_job_result(args.db, args.job_id, args.result, actor=args.actor)
    elif args.command == "approve-job":
        result = approve_ai_job(args.db, args.job_id, actor=args.actor)
    elif args.command == "cancel-job":
        result = cancel_ai_job(args.db, args.job_id, actor=args.actor, reason=args.reason)
    else:
        result = summary(args.db)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
