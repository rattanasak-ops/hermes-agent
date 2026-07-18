#!/usr/bin/env python3
"""Badword Command Center — P5 filters + P8 AI job queue on 127.0.0.1 only.

Hardening: PII aliases, ephemeral API token, Host/Origin checks, status-only queue.
There is NO AI auto-worker — jobs are queued for a human to copy prompts externally.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import secrets
import sys
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

STATUS_LABELS = {
    "new": "ใหม่",
    "investigating": "กำลังหาสาเหตุ",
    "planning": "กำลังวางแผน",
    "fixing": "กำลังแก้",
    "awaiting_verification": "รอตรวจผล",
    "fixed": "แก้แล้ว",
    "reopened": "กลับมาเกิด",
    "pending": "รอจัดหมวด",
}
DUPLICATE_LABELS = {
    "new": "เรื่องใหม่",
    "duplicate": "เรื่องซ้ำ",
    "reopened": "กลับมาเกิด",
    "pending_classification": "รอจัดหมวด",
}
JOB_STATUS_LABELS = {
    "queued": "รอคิว",
    "in_progress": "กำลังทำ",
    "result_saved": "บันทึกผลแล้ว",
    "approved": "อนุมัติแล้ว",
    "cancelled": "ยกเลิก",
}
BANGKOK = ZoneInfo("Asia/Bangkok")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def safe_json(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def local_time(value: Any) -> tuple[str, str]:
    raw = str(value or "")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        local = parsed.astimezone(BANGKOK)
        return local.strftime("%Y-%m-%d"), local.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return raw[:10], raw


def count_log_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def load_tracker():
    path = Path(__file__).resolve().with_name("badword_tracker.py")
    spec = importlib.util.spec_from_file_location("badword_tracker_cc", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("โหลด badword_tracker.py ไม่ได้")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def distinct_values(conn, column: str) -> list[str]:
    return [
        row[0]
        for row in conn.execute(f"SELECT DISTINCT {column} FROM events ORDER BY {column}")
        if row[0]
    ]


def host_header_allowed(host_header: str) -> bool:
    raw = (host_header or "").strip().lower()
    if not raw:
        return False
    if raw.startswith("["):
        # [::1]:port
        end = raw.find("]")
        hostname = raw[1:end] if end != -1 else raw
        return hostname in LOCAL_HOSTS
    hostname = raw.split(":", 1)[0]
    return hostname in LOCAL_HOSTS


def origin_header_allowed(origin_header: str) -> bool:
    origin = (origin_header or "").strip()
    if not origin:
        # curl / non-browser / same-origin navigations often omit Origin
        return True
    parsed = urlparse(origin)
    host = (parsed.hostname or "").lower()
    return host in LOCAL_HOSTS


def extract_api_token(handler: BaseHTTPRequestHandler, query: dict[str, list[str]] | None = None) -> str:
    """Accept API token from headers only — never from query string (leaks into logs/history)."""
    del query  # query string tokens are intentionally ignored
    header = (handler.headers.get("X-Badword-Token") or handler.headers.get("X-Api-Token") or "").strip()
    return header


def tokens_match(provided: str, expected: str) -> bool:
    """Constant-time compare that never raises on length/type mismatch."""
    if not provided or not expected:
        return False
    try:
        return secrets.compare_digest(str(provided), str(expected))
    except (TypeError, ValueError):
        return False


def load_dashboard_payload(db_path: Path, log_path: Path | None = None) -> dict[str, Any]:
    tracker = load_tracker()
    tracker.init_db(db_path)
    log_path = log_path or db_path.parent / "log.jsonl"
    with tracker.connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM events WHERE issue_id IS NULL").fetchone()[0]
        issue_count = conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
        reopened = conn.execute(
            "SELECT COUNT(*) FROM events WHERE duplicate_state='reopened'"
        ).fetchone()[0]
        issue_rows = list(
            conn.execute(
                """SELECT i.*,
                (SELECT e.event_id FROM events e WHERE e.issue_id=i.issue_id
                 ORDER BY e.occurred_at LIMIT 1) AS first_event
                FROM issues i ORDER BY i.last_seen_at DESC"""
            )
        )
        # Single shared slice for both the event table and phrase ranking
        event_rows = list(
            conn.execute(
                """SELECT e.*, COALESCE(i.status, 'pending') AS issue_status
                FROM events e LEFT JOIN issues i ON i.issue_id=e.issue_id
                ORDER BY e.occurred_at DESC LIMIT 500"""
            )
        )
        jobs = [
            {key: row[key] for key in row.keys()}
            for row in conn.execute(
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
                LIMIT 100"""
            )
        ]

    issue_html = []
    for issue in issue_rows:
        event_link = (
            f'<a href="#event-{esc(issue["first_event"])}">ดูเหตุการณ์</a>'
            if issue["first_event"]
            else "-"
        )
        issue_html.append(
            f'<tr id="issue-{esc(issue["issue_id"])}"><td><strong>{esc(issue["title"])}</strong>'
            f'<small>{esc(issue["issue_id"])}</small></td>'
            f'<td>{esc(issue["category"])}</td>'
            f'<td>{esc(STATUS_LABELS.get(issue["status"], issue["status"]))}</td>'
            f'<td>{issue["occurrence_count"]}</td><td>{issue["fix_count"]}</td>'
            f'<td>{issue["reopen_count"]}</td><td>{event_link}</td></tr>'
        )
    if not issue_html:
        issue_html.append('<tr><td colspan="7">ยังไม่มีเหตุการณ์ที่ผ่านเกณฑ์เชื่อมเป็นปัญหา</td></tr>')

    events: list[dict[str, Any]] = []
    staff_aliases: set[str] = set()
    device_aliases: set[str] = set()
    project_ids: set[str] = set()
    channels: set[str] = set()
    ai_targets: set[str] = set()
    phrases: set[str] = set()
    categories: set[str] = set()
    statuses: set[str] = set()
    phrase_counter: Counter[str] = Counter()

    for event in event_rows:
        date_value, display_time = local_time(event["occurred_at"])
        staff_alias = tracker.alias_for("staff", event["staff_id"])
        device_alias = tracker.alias_for("device", event["device_id"])
        host_alias = tracker.alias_for("host", event["host"])
        phrase = event["trigger_phrase"] or "ไม่พบคำเฉพาะ"
        excerpt = tracker.redact_message(event["message_excerpt_redacted"] or "", limit=240)
        path_hint = tracker.redact_path(event["cwd"] or "")
        staff_aliases.add(staff_alias)
        device_aliases.add(device_alias)
        if event["project_id"]:
            project_ids.add(event["project_id"])
        if event["channel"]:
            channels.add(event["channel"])
        if event["ai_target"]:
            ai_targets.add(event["ai_target"])
        phrases.add(phrase)
        if event["category"]:
            categories.add(event["category"])
        statuses.add(event["issue_status"] or "pending")
        phrase_counter[phrase] += 1
        events.append(
            {
                "id": event["event_id"],
                "occurredAt": event["occurred_at"],
                "date": date_value,
                "displayTime": display_time,
                "staff": staff_alias,
                "device": device_alias,
                "host": host_alias,
                "project": event["project_id"],
                "cwd": path_hint,
                "source": event["channel"],
                "ai": event["ai_target"],
                "phrase": phrase,
                "category": event["category"],
                "subject": event["subject"],
                "status": event["issue_status"],
                "statusLabel": STATUS_LABELS.get(event["issue_status"], event["issue_status"]),
                "duplicate": event["duplicate_state"],
                "duplicateLabel": DUPLICATE_LABELS.get(
                    event["duplicate_state"], event["duplicate_state"]
                ),
                "occurrence": event["occurrence_number"],
                "issue": event["issue_id"] or "",
                "version": event["source_version"],
                "excerpt": excerpt,
            }
        )

    # Rank phrases from the same 500-row dataset as the event list (not a separate full-table SQL)
    phrase_rank = [
        {"phrase": phrase, "count": count}
        for phrase, count in sorted(phrase_counter.items(), key=lambda item: (-item[1], item[0]))[:40]
    ]

    filters: dict[str, list[str]] = {
        "staff_id": sorted(staff_aliases),
        "device_id": sorted(device_aliases),
        "project_id": sorted(project_ids),
        "channel": sorted(channels),
        "ai_target": sorted(ai_targets),
        "trigger_phrase": sorted(phrases),
        "category": sorted(categories),
        "status": sorted(statuses),
    }

    job_payload = []
    for job in jobs:
        created_date, created_display = local_time(job["created_at"])
        actor_raw = job["actor"] or ""
        # Actor may already be aliased at write time; re-alias only if it looks raw
        actor_display = (
            actor_raw
            if str(actor_raw).startswith(("คน-", "เครื่อง-", "โฮสต์-", "ผู้ทำ-"))
            else tracker.alias_for("actor", actor_raw)
        )
        safe_title = tracker.redact_export_text(job["title"] or "", limit=240)
        safe_prompt = tracker.redact_export_text(job["prompt"] or "", limit=20000)
        job_payload.append(
            {
                "id": job["job_id"],
                "action": job["action_type"],
                "status": job["status"],
                "statusLabel": JOB_STATUS_LABELS.get(job["status"], job["status"]),
                "priority": job["priority"],
                "title": safe_title,
                "prompt": safe_prompt,
                "eventIds": json.loads(job["event_ids_json"] or "[]"),
                "issueIds": json.loads(job["issue_ids_json"] or "[]"),
                "result": tracker.redact_message(job["result_text"] or "", limit=8000),
                "createdAt": job["created_at"],
                "createdDate": created_date,
                "createdDisplay": created_display,
                "updatedAt": job["updated_at"],
                "actor": actor_display,
                "cancelReason": tracker.redact_message(job["cancel_reason"] or "", limit=240),
            }
        )

    dataset_size = len(events)
    return {
        "total": total,
        "pending": pending,
        "issue_count": issue_count,
        "reopened": reopened,
        "raw_log_rows": count_log_rows(log_path),
        # Do not expose file:// paths that may include usernames
        "log_link": "",
        "generated": datetime.now().astimezone().strftime("%d/%m/%Y %H:%M"),
        "filters": filters,
        "phrase_rank": phrase_rank,
        "issue_html": "".join(issue_html),
        "events": events,
        "jobs": job_payload,
        "dataset_size": dataset_size,
        # Full DB may be larger than the loaded slice (safe historical scope = LIMIT 500)
        "db_event_total": total,
        "scope_label": (
            f"ชุดที่โหลด {dataset_size} เหตุการณ์ (สูงสุด 500 · ฐานมี {total})"
            if total > dataset_size
            else f"ชุดที่โหลด {dataset_size} เหตุการณ์"
        ),
        "ai_auto_worker": False,
    }


def options(values: list[str]) -> str:
    return '<option value="">ทั้งหมด</option>' + "".join(
        f'<option value="{esc(value)}">{esc(value)}</option>' for value in values if value
    )


def render(db_path: Path, log_path: Path | None = None, *, api_token: str = "") -> str:
    data = load_dashboard_payload(db_path, log_path)
    filters = data["filters"]
    phrase_chips = "".join(
        f'<button type="button" class="chip phrase-chip" data-phrase="{esc(item["phrase"])}">'
        f'{esc(item["phrase"])} <b>{item["count"]}</b></button>'
        for item in data["phrase_rank"]
    ) or '<span class="muted">ยังไม่มีคำในฐาน</span>'
    token_js = safe_json(api_token or "")

    return f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Badword Command Center</title>
<style>
:root{{--bg:#f4f6f8;--panel:#fff;--text:#17202a;--muted:#66717d;--line:#dde3e9;--blue:#1769e0;--blue-soft:#eaf2ff;--green:#087f5b;--green-soft:#e6f7f1;--orange:#b45f06;--orange-soft:#fff4e5;--red:#b42318;--shadow:0 10px 30px rgba(23,32,42,.06)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Tahoma,sans-serif}}
main{{width:min(1440px,calc(100% - 32px));margin:24px auto 56px}}h1{{margin:0;font-size:clamp(1.6rem,3vw,2.35rem)}}h2{{margin:28px 0 12px;font-size:1.2rem}}h3{{margin:0 0 10px;font-size:.98rem}}small,.muted{{color:var(--muted)}}
.topline{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}}.source-file{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:9px 12px;box-shadow:var(--shadow)}}
.notice{{padding:11px 14px;border-left:4px solid var(--green);background:#f0fbf7;margin:14px 0 18px;border-radius:0 8px 8px 0}}
.stats{{display:grid;grid-template-columns:repeat(5,minmax(140px,1fr));gap:12px}}.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px;box-shadow:var(--shadow);min-height:98px}}
.card strong{{display:block;font-size:1.7rem;margin-top:4px}}.card em{{font-style:normal;color:var(--green);font-size:.8rem}}
.filter-shell,.panel{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px;box-shadow:var(--shadow)}}
.group-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}.group{{border:1px solid var(--line);border-radius:12px;padding:12px;background:#fbfcfd}}.group h3{{display:flex;justify-content:space-between;align-items:center}}
.chip-row,.quick{{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px}}
.chip,button{{border:1px solid var(--line);background:#fff;color:var(--text);border-radius:999px;padding:7px 12px;cursor:pointer;font:inherit}}
.chip:hover,button:hover,button.active,.chip.active{{border-color:var(--blue);background:var(--blue-soft);color:var(--blue)}}
.chip b{{margin-left:4px}}.chip.active b{{color:inherit}}
button.primary{{background:var(--blue);border-color:var(--blue);color:#fff}}button.primary:hover{{filter:brightness(.95);color:#fff}}
button.danger{{border-color:#f3c1bd;background:#fff5f4;color:var(--red)}}button.reset{{margin-left:auto}}
.fields{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}label{{font-size:.79rem;color:var(--muted)}}select,input,textarea{{display:block;width:100%;margin-top:4px;padding:8px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--text);font:inherit}}
textarea{{min-height:90px;resize:vertical}}
.active-filters{{display:flex;gap:8px;flex-wrap:wrap;min-height:34px;align-items:center}}.active-filters .chip{{background:var(--orange-soft);border-color:#f0d0a8;color:var(--orange)}}
.table-wrap{{overflow:auto;border:1px solid var(--line);background:var(--panel);border-radius:12px}}table{{width:100%;border-collapse:collapse;min-width:980px}}th,td{{padding:10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{color:var(--muted);font-size:.82rem;background:#fafbfc;position:sticky;top:0}}td{{font-size:.88rem}}a{{color:var(--blue)}}
.pill{{display:inline-block;border-radius:999px;padding:3px 8px;background:var(--blue-soft);color:var(--blue);font-size:.76rem;cursor:pointer;border:0}}.pill.green{{background:var(--green-soft);color:var(--green)}}.pill.orange{{background:var(--orange-soft);color:var(--orange)}}
.section-head{{display:flex;justify-content:space-between;align-items:end;gap:12px;flex-wrap:wrap}}#visibleCount{{font-weight:700;color:var(--green)}}.empty{{padding:22px;text-align:center;color:var(--muted)}}
.toolbar{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
.modal{{position:fixed;inset:0;background:rgba(23,32,42,.45);display:none;align-items:center;justify-content:center;padding:18px;z-index:40}}
.modal.open{{display:flex}}.modal-card{{width:min(860px,100%);max-height:90vh;overflow:auto;background:#fff;border-radius:14px;padding:18px;box-shadow:var(--shadow)}}
.modal pre{{white-space:pre-wrap;background:#f6f8fa;border:1px solid var(--line);border-radius:10px;padding:12px;font-size:.84rem;line-height:1.5}}
.toast{{position:fixed;right:16px;bottom:16px;background:#17202a;color:#fff;padding:10px 14px;border-radius:10px;display:none;z-index:50;max-width:min(420px,90vw)}}
.toast.show{{display:block}}
@media(max-width:1050px){{.stats{{grid-template-columns:repeat(3,1fr)}}.group-grid{{grid-template-columns:1fr}}}}
@media(max-width:700px){{main{{width:min(100% - 20px,1440px);margin-top:14px}}.stats{{grid-template-columns:repeat(2,1fr)}}.fields{{grid-template-columns:1fr}}button.reset{{margin-left:0}}}}
</style></head><body><main>
<header class="topline"><div><h1>Badword Command Center</h1>
<small>อัปเดต {esc(data["generated"])} · ฐานกลางบนเครื่องนี้ · {esc(data["scope_label"])} · อันดับคำคำนวณจากชุดเดียวกับตาราง (รวมป้ายคำที่เลือก) · เซิร์ฟเวอร์ฟังเฉพาะ 127.0.0.1 · คน/เครื่องเป็นนามแฝง</small></div>
<div class="source-file"><strong>สมุดบันทึกเดิมยังอยู่</strong><br>
<small>{data["raw_log_rows"]} บรรทัดใน log.jsonl (ไม่เปิด path ดิบในหน้านี้)</small></div></header>
<div class="notice">P5 = กรองคำ/ค้นหา/ป้ายกดได้ (multi-chip กับ dropdown ใช้ชุดคำเดียวกัน · อันดับคำคำนวณใหม่จากชุดเดียวกับตารางหลังรวมป้ายคำที่เลือก) · P8 = คิวงาน AI <strong>สถานะอย่างเดียว</strong> — ยังไม่มี worker AI Auto ทั้งเส้น · ห้าม shell/git/relay/แก้โค้ดจาก API · ปิดเซิร์ฟเวอร์แล้วยังเปิดฐานเดิมทำต่อได้ · token รับเฉพาะ header</div>

<section class="stats" aria-label="สรุป">
<div class="card">เหตุการณ์ตามตัวกรอง<strong id="kpiTotal">{data["dataset_size"]}</strong><em id="kpiCoverage">จากชุดที่โหลด {data["dataset_size"]}{"" if data["db_event_total"] <= data["dataset_size"] else f" · ฐานมี {data['db_event_total']}"}</em></div>
<div class="card">คำที่พบบ่อยที่สุด<strong id="kpiPhrase">—</strong><em id="kpiPhraseCount">0 ครั้ง</em></div>
<div class="card">แหล่งที่มาหลัก<strong id="kpiSource">—</strong><em id="kpiSourceCount">0 ครั้ง</em></div>
<div class="card">คนที่แจ้งมากที่สุด<strong id="kpiStaff">—</strong><em id="kpiStaffCount">0 ครั้ง</em></div>
<div class="card">รอจัดหมวด<strong id="kpiPending">{data["pending"]}</strong><em>ทะเบียนปัญหา {data["issue_count"]} เรื่อง · กลับมาเกิด {data["reopened"]}</em></div>
</section>

<h2>P5 · ป้ายคำยอดนิยม (กดเลือกหลายคำได้)</h2>
<section class="panel"><div class="chip-row" id="phraseChips">{phrase_chips}</div>
<div class="toolbar"><button type="button" id="clearPhrases">ล้างคำที่เลือก</button>
<small class="muted">กดป้ายคำเพื่อกรอง · กดซ้ำเพื่อเอาออก · เลือกหลายคำพร้อมกันได้</small></div></section>

<h2>ค้นหาและกรองข้อมูล</h2>
<section class="filter-shell">
<div class="quick" aria-label="ช่วงเวลาด่วน">
<button type="button" data-range="1">24 ชั่วโมง</button>
<button type="button" data-range="7">7 วัน</button>
<button type="button" data-range="30">30 วัน</button>
<button type="button" data-range="90">90 วัน</button>
<button type="button" data-range="all" class="active">ชุดที่โหลดทั้งหมด</button>
<button type="button" class="reset" id="reset">ล้างตัวกรองทั้งหมด</button>
</div>
<div class="active-filters" id="activeFilters" aria-label="ป้ายตัวกรองที่ใช้"></div>
<form class="group-grid" id="filters" autocomplete="off">
<article class="group"><h3>1) เวลา <small class="muted">กลุ่มหลัก</small></h3>
<div class="fields">
<label>เริ่มวันที่<input id="dateFrom" type="date"></label>
<label>ถึงวันที่<input id="dateTo" type="date"></label>
</div></article>
<article class="group"><h3>2) คำและค้นหา <small class="muted">กลุ่มหลัก</small></h3>
<div class="fields">
<label>ค้นหาคำหรือเรื่อง<input id="search" type="search" placeholder="เช่น ภาษาคน หรือ หยุดงาน"></label>
<label>เพิ่มคำเข้า multi-chip (ไม่ชนกับป้ายด้านบน)<select id="phrase">{options(filters["trigger_phrase"])}</select></label>
</div>
<small class="muted">dropdown นี้เติมเข้าชุดคำเดียวกับป้ายยอดนิยม — ไม่กรองแยกแบบ AND ที่ทำให้ว่าง</small></article>
<article class="group"><h3>3) ต้นทาง <small class="muted">กลุ่มหลัก</small></h3>
<div class="fields">
<label>แหล่งที่มา<select id="source">{options(filters["channel"])}</select></label>
<label>เฉพาะคน<select id="staff">{options(filters["staff_id"])}</select></label>
<label>เครื่อง<select id="device">{options(filters["device_id"])}</select></label>
</div></article>
<article class="group"><h3>4) งานและสถานะ <small class="muted">กลุ่มหลัก</small></h3>
<div class="fields">
<label>โครงการ<select id="project">{options(filters["project_id"])}</select></label>
<label>AI ที่ถูกตำหนิ<select id="ai">{options(filters["ai_target"])}</select></label>
<label>หมวดปัญหา<select id="category">{options(filters["category"])}</select></label>
<label>สถานะ<select id="status">{options(filters["status"])}</select></label>
</div></article>
<article class="group" style="grid-column:1/-1"><h3>ตัวกรองเพิ่มเติม</h3>
<div class="fields">
<label>ความสำคัญงานคิว (1-100)<input id="priority" type="number" min="1" max="100" value="50"></label>
<label>ชื่อใบงาน (ถ้ามี)<input id="jobTitle" type="text" placeholder="เช่น วิเคราะห์คำภาษาคนสัปดาห์นี้"></label>
</div>
<div class="toolbar" style="margin-top:10px">
<button type="button" class="primary" id="analyzeVisible">วิเคราะห์ทั้งหมดที่เห็น</button>
<button type="button" id="approveQueueSelected">สร้างคิวอนุมัติจากที่เห็น</button>
<small class="muted">ปุ่มนี้สร้างคิวและสถานะเท่านั้น · ไม่เรียก AI / shell / git / relay</small>
</div></article>
</form>
</section>

<div class="section-head"><h2>สมุดบันทึกเหตุการณ์ <span id="visibleCount">{len(data["events"])}</span> รายการ</h2>
<small>ป้ายคำในตารางกดได้เพื่อเพิ่มตัวกรอง · ใช้ “ดู Source” ดูรายละเอียด</small></div>
<div class="table-wrap"><table><thead><tr>
<th>เวลา</th><th>คำที่จับได้</th><th>คน</th><th>แหล่งที่มา</th><th>โครงการ / AI</th><th>เรื่อง</th><th>ประเภท</th><th>ปัญหา</th><th>Source</th>
</tr></thead><tbody id="events"></tbody></table></div>

<h2>ทะเบียนสาเหตุ</h2>
<div class="table-wrap"><table><thead><tr><th>ปัญหา</th><th>หมวด</th><th>สถานะ</th><th>เหตุการณ์</th><th>แก้</th><th>กลับมาเกิด</th><th>เชื่อมโยง</th></tr></thead>
<tbody>{data["issue_html"]}</tbody></table></div>

<div class="section-head"><h2>P8 · ตารางงาน AI และประวัติ</h2>
<small id="jobCount">{len(data["jobs"])} งาน</small></div>
<div class="table-wrap"><table><thead><tr>
<th>เวลา</th><th>งาน</th><th>ชนิด</th><th>สถานะ</th><th>priority</th><th>เหตุการณ์</th><th>การทำงาน</th>
</tr></thead><tbody id="jobs"></tbody></table></div>
</main>

<div class="modal" id="jobModal" role="dialog" aria-modal="true" aria-labelledby="jobModalTitle">
<div class="modal-card">
<div class="section-head"><h2 id="jobModalTitle">ใบงาน</h2>
<button type="button" id="closeModal">ปิด</button></div>
<p class="muted" id="jobMeta"></p>
<pre id="jobPrompt"></pre>
<div class="toolbar">
<button type="button" class="primary" id="copyPrompt">คัดลอกใบงาน</button>
</div>
<label>บันทึกผล (ตัดข้อมูลส่วนตัวฝั่งเซิร์ฟเวอร์อีกชั้น)<textarea id="resultText" placeholder="วางผลวิเคราะห์จาก AI ภายนอกที่นี่"></textarea></label>
<div class="toolbar" style="margin-top:10px">
<button type="button" id="saveResult">บันทึกผล</button>
<button type="button" class="primary" id="approveJob">อนุมัติ (สถานะอย่างเดียว)</button>
<button type="button" class="danger" id="cancelJob">ยกเลิก</button>
</div>
</div></div>
<div class="toast" id="toast"></div>

<script>
const allEvents = {safe_json(data["events"])};
const initialJobs = {safe_json(data["jobs"])};
const apiToken = {token_js};
// phrase is multi-chip only — NOT in exclusive selectIds (prevents dropdown fighting chips)
const selectIds = ["source","staff","device","project","ai","category","status"];
const labelMap = {{
  search:"ค้นหา", source:"แหล่งที่มา", staff:"คน", device:"เครื่อง",
  project:"โครงการ", ai:"AI", category:"หมวด", status:"สถานะ", dateFrom:"ตั้งแต่", dateTo:"ถึง",
  phrases:"คำยอดนิยม"
}};
const byId = id => document.getElementById(id);
const text = v => String(v ?? "");
const escapeHtml = v => text(v).replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[c]));
const group = (items, key) => {{
  const out = {{}};
  items.forEach(x => {{ const label = text(x[key]) || "ไม่ระบุ"; out[label] = (out[label] || 0) + 1; }});
  return Object.entries(out).sort((a,b) => b[1]-a[1] || a[0].localeCompare(b[0], "th"));
}};
let selectedPhrases = new Set();
let jobs = initialJobs.slice();
let activeJobId = null;
const apiBase = window.location.protocol.startsWith("http") ? "" : null;

function toast(msg) {{
  const el = byId("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2800);
}}

const fieldMap = {{source:"source", staff:"staff", device:"device", project:"project", ai:"ai", category:"category", status:"status"}};
/** Non-phrase filters only (date/search/dropdowns). Used as input to selectedEvents(). */
function baseFilteredEvents() {{
  const from = byId("dateFrom").value, to = byId("dateTo").value, q = byId("search").value.trim().toLowerCase();
  return allEvents.filter(e => {{
    for (const id of selectIds) {{
      const wanted = byId(id).value;
      if (wanted && text(e[fieldMap[id]]) !== wanted) return false;
    }}
    if (from && e.date < from) return false;
    if (to && e.date > to) return false;
    if (q && !([e.phrase,e.subject,e.project,e.source,e.staff,e.ai,e.excerpt].some(v => text(v).toLowerCase().includes(q)))) return false;
    return true;
  }});
}}
/** Final table subset = base filters + selected phrase chips (OR). Rank and table both use this. */
function selectedEvents() {{
  const base = baseFilteredEvents();
  if (!selectedPhrases.size) return base;
  return base.filter(e => selectedPhrases.has(text(e.phrase)));
}}

function renderActiveFilters() {{
  const chips = [];
  if (selectedPhrases.size) {{
    [...selectedPhrases].forEach(p => chips.push({{id:"phrases:"+p, label:`คำ: ${{p}}`}}));
  }}
  selectIds.forEach(id => {{
    const v = byId(id).value;
    if (v) chips.push({{id:id, label:`${{labelMap[id]}}: ${{v}}`}});
  }});
  ["dateFrom","dateTo","search"].forEach(id => {{
    const v = byId(id).value;
    if (v) chips.push({{id:id, label:`${{labelMap[id]}}: ${{v}}`}});
  }});
  const box = byId("activeFilters");
  if (!chips.length) {{
    box.innerHTML = '<span class="muted">ยังไม่มีตัวกรองที่ใช้อยู่</span>';
    return;
  }}
  box.innerHTML = chips.map(c => `<button type="button" class="chip" data-clear="${{escapeHtml(c.id)}}">${{escapeHtml(c.label)}} ×</button>`).join("");
  box.querySelectorAll("[data-clear]").forEach(btn => btn.addEventListener("click", () => clearOne(btn.dataset.clear)));
}}

function clearOne(key) {{
  if (key.startsWith("phrases:")) {{
    selectedPhrases.delete(key.slice(8));
    syncPhraseChips();
  }} else if (byId(key)) {{
    byId(key).value = "";
  }}
  update();
}}

function syncPhraseChips() {{
  document.querySelectorAll(".phrase-chip").forEach(btn => {{
    btn.classList.toggle("active", selectedPhrases.has(btn.dataset.phrase));
  }});
}}

function renderTable(items) {{
  const body = byId("events");
  if (!items.length) {{
    body.innerHTML = '<tr><td colspan="9" class="empty">ไม่พบเหตุการณ์ตามตัวกรอง</td></tr>';
    return;
  }}
  body.innerHTML = items.map(e => `<tr id="event-${{escapeHtml(e.id)}}">
    <td>${{escapeHtml(e.displayTime)}}</td>
    <td><button type="button" class="pill phrase-in-table" data-phrase="${{escapeHtml(e.phrase)}}">${{escapeHtml(e.phrase)}}</button></td>
    <td>${{escapeHtml(e.staff)}}<small>${{escapeHtml(e.device)}}</small></td>
    <td>${{escapeHtml(e.source)}}</td>
    <td>${{escapeHtml(e.project)}}<small>${{escapeHtml(e.ai)}}</small></td>
    <td>${{escapeHtml(e.subject)}}<small>${{escapeHtml(e.category)}}</small></td>
    <td><span class="pill green">${{escapeHtml(e.duplicateLabel)}}</span><small>ครั้งที่ ${{e.occurrence}}</small></td>
    <td>${{e.issue ? `<a href="#issue-${{escapeHtml(e.issue)}}">${{escapeHtml(e.issue)}}</a>` : "รอจัดหมวด"}}</td>
    <td><details><summary>ดู Source</summary><div>ช่องทาง: ${{escapeHtml(e.source)}}<br>คน: ${{escapeHtml(e.staff)}}<br>เครื่อง: ${{escapeHtml(e.host)}}<br>โครงการ: ${{escapeHtml(e.project)}}<br>ตำแหน่ง: ${{escapeHtml(e.cwd||"ไม่ระบุ")}}<br>รุ่นกติกา: ${{escapeHtml(e.version)}}<br>รหัสเหตุการณ์: ${{escapeHtml(e.id)}}</div></details></td>
  </tr>`).join("");
  body.querySelectorAll(".phrase-in-table").forEach(btn => btn.addEventListener("click", () => {{
    const p = btn.dataset.phrase;
    if (selectedPhrases.has(p)) selectedPhrases.delete(p); else selectedPhrases.add(p);
    syncPhraseChips();
    update();
  }}));
}}

function renderJobs() {{
  const body = byId("jobs");
  byId("jobCount").textContent = `${{jobs.length}} งาน`;
  if (!jobs.length) {{
    body.innerHTML = '<tr><td colspan="7" class="empty">ยังไม่มีคิวงาน AI</td></tr>';
    return;
  }}
  body.innerHTML = jobs.map(j => `<tr>
    <td>${{escapeHtml(j.createdDisplay || j.createdAt)}}</td>
    <td><strong>${{escapeHtml(j.title)}}</strong><small>${{escapeHtml(j.id)}}</small></td>
    <td>${{escapeHtml(j.action)}}</td>
    <td><span class="pill orange">${{escapeHtml(j.statusLabel || j.status)}}</span></td>
    <td>${{escapeHtml(j.priority)}}</td>
    <td>${{Array.isArray(j.eventIds) ? j.eventIds.length : 0}}</td>
    <td><button type="button" data-open-job="${{escapeHtml(j.id)}}">ดู/คัดลอกใบงาน</button></td>
  </tr>`).join("");
  body.querySelectorAll("[data-open-job]").forEach(btn => btn.addEventListener("click", () => openJob(btn.dataset.openJob)));
}}

function renderPhraseRank(rankPairs) {{
  // Rebuild phrase chips from the filtered list so rank matches what the table shows.
  const box = byId("phraseChips");
  if (!rankPairs.length) {{
    box.innerHTML = '<span class="muted">ไม่มีคำในรายการหลังกรอง</span>';
    return;
  }}
  box.innerHTML = rankPairs.slice(0, 40).map(([phrase, count]) => {{
    const active = selectedPhrases.has(phrase) ? " active" : "";
    return `<button type="button" class="phrase-chip${{active}}" data-phrase="${{escapeHtml(phrase)}}">${{escapeHtml(phrase)}} <strong>${{count}}</strong></button>`;
  }}).join("");
  box.querySelectorAll(".phrase-chip").forEach(btn => btn.addEventListener("click", () => {{
    const p = btn.dataset.phrase;
    if (selectedPhrases.has(p)) selectedPhrases.delete(p); else selectedPhrases.add(p);
    byId("phrase").value = "";
    update();
  }}));
}}

function update() {{
  // Phrase rank and event table share one subset: all filters INCLUDING selected phrase chips.
  const items = selectedEvents();
  const rankSource = group(items, "phrase");
  const phrases = rankSource;
  const sources = group(items, "source");
  const staff = group(items, "staff");
  byId("kpiTotal").textContent = items.length;
  byId("kpiCoverage").textContent = `จากชุดที่โหลด ${{allEvents.length}} · หลังกรอง ${{items.length}}`;
  byId("kpiPhrase").textContent = phrases[0]?.[0] || "—";
  byId("kpiPhraseCount").textContent = `${{phrases[0]?.[1] || 0}} ครั้ง`;
  byId("kpiSource").textContent = sources[0]?.[0] || "—";
  byId("kpiSourceCount").textContent = `${{sources[0]?.[1] || 0}} ครั้ง`;
  byId("kpiStaff").textContent = staff[0]?.[0] || "—";
  byId("kpiStaffCount").textContent = `${{staff[0]?.[1] || 0}} ครั้ง`;
  byId("kpiPending").textContent = items.filter(e => !e.issue).length;
  byId("visibleCount").textContent = items.length;
  renderPhraseRank(rankSource);
  renderTable(items);
  renderJobs();
  renderActiveFilters();
  syncPhraseChips();
}}

function setRange(value, button) {{
  document.querySelectorAll("[data-range]").forEach(b => b.classList.remove("active"));
  button.classList.add("active");
  if (value === "all") {{
    byId("dateFrom").value = "";
    byId("dateTo").value = "";
  }} else {{
    const latest = allEvents.map(e => e.date).sort().at(-1) || new Date().toISOString().slice(0,10);
    const end = new Date(latest + "T12:00:00");
    const start = new Date(end);
    start.setDate(start.getDate() - (Number(value) - 1));
    byId("dateFrom").value = start.toISOString().slice(0,10);
    byId("dateTo").value = latest;
  }}
  update();
}}

function filterSnapshot() {{
  const snap = {{ phrases: [...selectedPhrases] }};
  selectIds.concat(["dateFrom","dateTo","search"]).forEach(id => {{
    const v = byId(id).value;
    if (v) snap[id] = v;
  }});
  return snap;
}}

async function api(path, options={{}}) {{
  if (!apiBase && apiBase !== "") {{
    throw new Error("ต้องเปิดผ่านเซิร์ฟเวอร์ local (python badword_dashboard.py serve) เพื่อใช้คิวงาน");
  }}
  if (!apiToken) {{
    throw new Error("ไม่มีรหัสใช้งานชั่วคราว — เปิดผ่าน serve เท่านั้น");
  }}
  const headers = {{
    "Content-Type":"application/json",
    "X-Badword-Token": apiToken,
    ...(options.headers || {{}}),
  }};
  const res = await fetch(path, {{
    ...options,
    headers,
  }});
  const data = await res.json().catch(() => ({{error: "ตอบกลับไม่ใช่ JSON"}}));
  if (!res.ok) throw new Error(data.error || `HTTP ${{res.status}}`);
  return data;
}}

async function queueJobs(action) {{
  const items = selectedEvents();
  if (!items.length) {{ toast("ไม่มีรายการที่เห็นให้สร้างคิว"); return; }}
  const priority = Number(byId("priority").value || 50);
  const title = byId("jobTitle").value.trim();
  try {{
    const data = await api("/api/jobs", {{
      method: "POST",
      body: JSON.stringify({{
        action_type: action,
        event_ids: items.map(e => e.id),
        priority,
        title: title || undefined,
        filter_snapshot: filterSnapshot(),
        actor: "owner",
      }}),
    }});
    if (data.duplicate_blocked) toast("กันงานซ้ำ: มีคิวค้างอยู่แล้วสำหรับชุดนี้");
    else toast(`สร้างคิวแล้ว · ${{data.job_id || data.id}}`);
    await refreshJobs();
  }} catch (err) {{
    toast(String(err.message || err));
  }}
}}

async function refreshJobs() {{
  try {{
    const data = await api("/api/jobs");
    jobs = (data.jobs || []).map(normalizeJob);
    renderJobs();
  }} catch (err) {{
    // static HTML export can still show initial jobs
  }}
}}

function normalizeJob(j) {{
  return {{
    id: j.job_id || j.id,
    action: j.action_type || j.action,
    status: j.status,
    statusLabel: j.statusLabel || j.status,
    priority: j.priority,
    title: j.title,
    prompt: j.prompt,
    eventIds: typeof j.event_ids_json === "string" ? JSON.parse(j.event_ids_json || "[]") : (j.eventIds || j.event_ids || []),
    issueIds: typeof j.issue_ids_json === "string" ? JSON.parse(j.issue_ids_json || "[]") : (j.issueIds || j.issue_ids || []),
    result: j.result_text || j.result || "",
    createdAt: j.created_at || j.createdAt,
    createdDisplay: j.createdDisplay || j.created_at || j.createdAt,
    updatedAt: j.updated_at || j.updatedAt,
    actor: j.actor,
    cancelReason: j.cancel_reason || j.cancelReason || "",
  }};
}}

function openJob(id) {{
  const job = jobs.find(j => j.id === id);
  if (!job) return;
  activeJobId = id;
  byId("jobModalTitle").textContent = job.title || "ใบงาน";
  byId("jobMeta").textContent = `${{job.id}} · ${{job.action}} · ${{job.statusLabel || job.status}} · priority ${{job.priority}} · เหตุการณ์ ${{(job.eventIds||[]).length}}`;
  byId("jobPrompt").textContent = job.prompt || "";
  byId("resultText").value = job.result || "";
  byId("jobModal").classList.add("open");
}}

async function saveResult() {{
  if (!activeJobId) return;
  try {{
    const data = await api(`/api/jobs/${{encodeURIComponent(activeJobId)}}/result`, {{
      method: "POST",
      body: JSON.stringify({{ result_text: byId("resultText").value, actor: "owner" }}),
    }});
    toast("บันทึกผลแล้ว");
    await refreshJobs();
    openJob(data.job_id || activeJobId);
  }} catch (err) {{ toast(String(err.message || err)); }}
}}

async function approveJob() {{
  if (!activeJobId) return;
  try {{
    await api(`/api/jobs/${{encodeURIComponent(activeJobId)}}/approve`, {{
      method: "POST",
      body: JSON.stringify({{ actor: "owner" }}),
    }});
    toast("อนุมัติสถานะแล้ว (ไม่ได้แก้โค้ด/ไม่เรียก shell)");
    await refreshJobs();
    openJob(activeJobId);
  }} catch (err) {{ toast(String(err.message || err)); }}
}}

async function cancelJob() {{
  if (!activeJobId) return;
  try {{
    await api(`/api/jobs/${{encodeURIComponent(activeJobId)}}/cancel`, {{
      method: "POST",
      body: JSON.stringify({{ actor: "owner", reason: "ยกเลิกจากหน้า command center" }}),
    }});
    toast("ยกเลิกคิวแล้ว");
    await refreshJobs();
    openJob(activeJobId);
  }} catch (err) {{ toast(String(err.message || err)); }}
}}

document.querySelectorAll("[data-range]").forEach(b => b.addEventListener("click", () => setRange(b.dataset.range, b)));
// Phrase chip clicks are bound inside renderPhraseRank() after each recompute.
// Dropdown adds into the same selectedPhrases set, then clears itself
byId("phrase").addEventListener("change", () => {{
  const p = byId("phrase").value;
  if (p) {{
    selectedPhrases.add(p);
    byId("phrase").value = "";
  }}
  update();
}});
byId("clearPhrases").addEventListener("click", () => {{ selectedPhrases.clear(); byId("phrase").value = ""; update(); }});
byId("filters").addEventListener("input", (ev) => {{ if (ev.target && ev.target.id === "phrase") return; update(); }});
byId("filters").addEventListener("change", (ev) => {{ if (ev.target && ev.target.id === "phrase") return; update(); }});
byId("reset").addEventListener("click", () => {{
  byId("filters").reset();
  selectedPhrases.clear();
  byId("priority").value = "50";
  document.querySelector('[data-range="all"]').click();
}});
byId("analyzeVisible").addEventListener("click", () => queueJobs("analyze"));
byId("approveQueueSelected").addEventListener("click", () => queueJobs("approve"));
byId("closeModal").addEventListener("click", () => byId("jobModal").classList.remove("open"));
byId("copyPrompt").addEventListener("click", async () => {{
  try {{
    await navigator.clipboard.writeText(byId("jobPrompt").textContent || "");
    toast("คัดลอกใบงานแล้ว");
  }} catch {{
    toast("คัดลอกไม่สำเร็จ — เลือกข้อความในกล่องใบงานเองได้");
  }}
}});
byId("saveResult").addEventListener("click", saveResult);
byId("approveJob").addEventListener("click", approveJob);
byId("cancelJob").addEventListener("click", cancelJob);
byId("filters").reset();
update();
refreshJobs();
</script></body></html>"""


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    if length > 2_000_000:
        raise ValueError("คำขอใหญ่เกินกำหนด")
    raw = handler.rfile.read(length)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("body ต้องเป็น object")
    return data


def _public_job_view(tracker: Any, job: dict[str, Any]) -> dict[str, Any]:
    """Strip residual PII from job API payloads (title/prompt/snapshot/evidence/result/actor)."""
    return tracker.sanitize_ai_job_export(job)


def make_handler(db_path: Path, log_path: Path | None, api_token: str | None = None):
    tracker = load_tracker()
    token = api_token if api_token is not None else secrets.token_urlsafe(18)

    class Handler(BaseHTTPRequestHandler):
        server_version = "BadwordCommandCenter/1.1"
        api_token = token

        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def _guard_local_api(self, qs: dict[str, list[str]], *, require_token: bool = True) -> str | None:
            """Return error message if Host/Origin/token fail; None if OK."""
            if not host_header_allowed(self.headers.get("Host", "")):
                return "Host ไม่อนุญาต — ใช้เฉพาะ 127.0.0.1 / localhost"
            if not origin_header_allowed(self.headers.get("Origin", "")):
                return "Origin ไม่อนุญาต — ใช้เฉพาะ local"
            if require_token:
                # Header only — query-string tokens are never accepted
                provided = extract_api_token(self, qs)
                if not tokens_match(provided, self.api_token):
                    return "ต้องใช้รหัสใช้งานชั่วคราว (header X-Badword-Token เท่านั้น · ไม่รับ query string)"
            return None

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = parse_qs(parsed.query)
            try:
                if path == "/":
                    # Page itself is local-only; token is embedded for subsequent API calls
                    guard = self._guard_local_api(qs, require_token=False)
                    if guard:
                        _json_response(self, 403, {"error": guard})
                        return
                    page = render(db_path, log_path, api_token=self.api_token).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(page)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(page)
                    return
                if path == "/api/health":
                    guard = self._guard_local_api(qs, require_token=False)
                    if guard:
                        _json_response(self, 403, {"error": guard})
                        return
                    _json_response(
                        self,
                        200,
                        {
                            "ok": True,
                            "host": DEFAULT_HOST,
                            "bind_only": "127.0.0.1",
                            "summary": tracker.summary(db_path),
                            "auth": {
                                "token_required": True,
                                "header": "X-Badword-Token",
                                "header_only": True,
                                "query_string_token_accepted": False,
                                "host_origin_checked": True,
                            },
                            "ai_auto_worker": False,
                            "safety": {
                                "shell": False,
                                "git": False,
                                "relay": False,
                                "code_edit": False,
                            },
                        },
                    )
                    return
                guard = self._guard_local_api(qs, require_token=True)
                if guard:
                    _json_response(self, 401 if "รหัส" in guard else 403, {"error": guard})
                    return
                if path == "/api/events":
                    # Aliased public view only — never raw staff/device/host/cwd
                    payload = load_dashboard_payload(db_path, log_path)
                    limit = int((qs.get("limit") or ["500"])[0])
                    events = payload["events"][: max(1, min(limit, 500))]
                    _json_response(self, 200, {"events": events, "count": len(events), "aliased": True})
                    return
                if path == "/api/jobs":
                    status = (qs.get("status") or [None])[0]
                    limit = int((qs.get("limit") or ["100"])[0])
                    jobs = [
                        _public_job_view(tracker, job)
                        for job in tracker.list_ai_jobs(db_path, status=status, limit=limit)
                    ]
                    _json_response(self, 200, {"jobs": jobs, "count": len(jobs)})
                    return
                match = re.fullmatch(r"/api/jobs/([^/]+)", path)
                if match:
                    job = _public_job_view(tracker, tracker.get_ai_job(db_path, match.group(1)))
                    _json_response(self, 200, {"job": job})
                    return
                _json_response(self, 404, {"error": "ไม่พบเส้นทาง"})
            except Exception as exc:  # noqa: BLE001 - API boundary
                _json_response(self, 400, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = parse_qs(parsed.query)
            try:
                guard = self._guard_local_api(qs, require_token=True)
                if guard:
                    _json_response(self, 401 if "รหัส" in guard else 403, {"error": guard})
                    return
                body = _read_json_body(self)
                if path == "/api/jobs":
                    event_ids = body.get("event_ids") or body.get("eventIds") or []
                    if not isinstance(event_ids, list):
                        raise ValueError("event_ids ต้องเป็น list")
                    job = tracker.create_ai_job(
                        db_path,
                        event_ids,
                        action_type=str(body.get("action_type") or body.get("action") or "analyze"),
                        priority=int(body.get("priority") or 50),
                        actor=str(body.get("actor") or "owner"),
                        filter_snapshot=body.get("filter_snapshot") or body.get("filterSnapshot") or {},
                        title=body.get("title"),
                    )
                    # status only — no shell/git/relay/code mutation / no AI auto-worker
                    _json_response(self, 200, _public_job_view(tracker, job))
                    return
                match_result = re.fullmatch(r"/api/jobs/([^/]+)/result", path)
                if match_result:
                    job = tracker.save_ai_job_result(
                        db_path,
                        match_result.group(1),
                        str(body.get("result_text") or body.get("result") or ""),
                        actor=str(body.get("actor") or "owner"),
                    )
                    _json_response(self, 200, _public_job_view(tracker, job))
                    return
                match_approve = re.fullmatch(r"/api/jobs/([^/]+)/approve", path)
                if match_approve:
                    job = tracker.approve_ai_job(
                        db_path,
                        match_approve.group(1),
                        actor=str(body.get("actor") or "owner"),
                    )
                    _json_response(self, 200, _public_job_view(tracker, job))
                    return
                match_cancel = re.fullmatch(r"/api/jobs/([^/]+)/cancel", path)
                if match_cancel:
                    job = tracker.cancel_ai_job(
                        db_path,
                        match_cancel.group(1),
                        actor=str(body.get("actor") or "owner"),
                        reason=str(body.get("reason") or ""),
                    )
                    _json_response(self, 200, _public_job_view(tracker, job))
                    return
                _json_response(self, 404, {"error": "ไม่พบเส้นทาง"})
            except Exception as exc:  # noqa: BLE001 - API boundary
                _json_response(self, 400, {"error": str(exc)})

    return Handler


def serve(db_path: Path, host: str, port: int, log_path: Path | None = None) -> int:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("เพื่อความปลอดภัย อนุญาตฟังเฉพาะ 127.0.0.1 / localhost / ::1 เท่านั้น")
    bind_host = "127.0.0.1" if host in {"127.0.0.1", "localhost"} else host
    tracker = load_tracker()
    tracker.init_db(db_path)
    api_token = secrets.token_urlsafe(18)
    handler = make_handler(db_path, log_path, api_token=api_token)
    server = ThreadingHTTPServer((bind_host, port), handler)
    print(
        json.dumps(
            {
                "status": "listening",
                "url": f"http://{bind_host}:{port}/",
                "db": str(db_path),
                "bind": bind_host,
                "api_token_header": "X-Badword-Token",
                "api_token": api_token,
                "ai_auto_worker": False,
                "safety": "API queues status only; Host/Origin checked; no shell/git/relay/code edits; no AI auto-worker",
            },
            ensure_ascii=False,
        )
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(json.dumps({"status": "stopped"}, ensure_ascii=False))
    finally:
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Badword Command Center dashboard + local API")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--log", type=Path)
    # backward compatible: python badword_dashboard.py --db X --html Y
    parser.add_argument("--html", type=Path)
    sub = parser.add_subparsers(dest="command")

    write = sub.add_parser("write", help="เขียนไฟล์ HTML แบบ static")
    write.add_argument("--html", type=Path, dest="write_html", required=True)

    serve_cmd = sub.add_parser("serve", help="เปิดเซิร์ฟเวอร์ local ที่ 127.0.0.1")
    serve_cmd.add_argument("--host", default=DEFAULT_HOST)
    serve_cmd.add_argument("--port", type=int, default=DEFAULT_PORT)

    args = parser.parse_args()

    if args.command == "serve":
        return serve(args.db, args.host, args.port, args.log)

    html_path = getattr(args, "write_html", None) or args.html
    if html_path is not None:
        html_path.parent.mkdir(parents=True, exist_ok=True)
        # Static export has empty token — queue API disabled by design
        html_path.write_text(render(args.db, args.log, api_token=""), encoding="utf-8")
        print(html_path)
        return 0
    raise SystemExit("ใช้: --html PATH หรือ write --html PATH หรือ serve --host 127.0.0.1 --port 8765")


if __name__ == "__main__":
    raise SystemExit(main())
