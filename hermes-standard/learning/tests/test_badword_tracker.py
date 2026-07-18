"""Tests for Badword Tracker core + AI job queue (P8) + hardening."""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TRACKER = ROOT / "bin" / "badword_tracker.py"


def load_tracker():
    name = "badword_tracker_under_test"
    spec = importlib.util.spec_from_file_location(name, TRACKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Python 3.14+ dataclasses require the module to be in sys.modules
    # before @dataclass processes annotations (importlib alone is not enough).
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_cli(db: Path, *args: str):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(TRACKER), "--db", str(db), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "tracker.db"
    tracker = load_tracker()
    tracker.init_db(path)
    return path


def seed_event(db: Path, message: str, **kwargs) -> dict:
    tracker = load_tracker()
    defaults = dict(
        staff_id="owner",
        device_id="mac-1",
        host="mac-1",
        project_id="Hermes",
        cwd="/tmp/Hermes",
        channel="manual",
    )
    defaults.update(kwargs)
    receipt = tracker.record_event(db, message, **defaults)
    return {
        "event_id": receipt.event_id,
        "issue_id": receipt.issue_id,
        "category": receipt.category,
        "subject": receipt.subject,
        "duplicate": receipt.duplicate,
        "status": receipt.status,
        "count": receipt.count,
    }


def test_init_creates_ai_jobs_table(db: Path):
    with sqlite3.connect(db) as conn:
        names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        indexes = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
    assert "events" in names
    assert "issues" in names
    assert "ai_jobs" in names
    assert "idx_ai_jobs_active_dedupe" in indexes


def test_redact_message_strips_secrets_email_phone_paths():
    tracker = load_tracker()
    text = tracker.redact_message(
        "token=abc123 secret: xyz api_key=qqq Authorization: Bearer tok.xyz "
        "user@example.com 0812345678 hello /Users/rattanasak/secret-project "
        r"\Users\alice\docs C:\Users\bob\work"
    )
    assert "abc123" not in text
    assert "xyz" not in text
    assert "qqq" not in text
    assert "tok.xyz" not in text
    assert "[อีเมล]" in text
    assert "[โทรศัพท์]" in text
    assert "rattanasak" not in text
    assert "alice" not in text
    assert "bob" not in text
    assert "[ผู้ใช้]" in text
    assert "hello" in text


def test_alias_for_is_stable_and_non_raw():
    tracker = load_tracker()
    a1 = tracker.alias_for("staff", "owner-real-name")
    a2 = tracker.alias_for("staff", "owner-real-name")
    b = tracker.alias_for("device", "macbook-pro-16")
    h = tracker.alias_for("host", "office-mac.local")
    assert a1 == a2
    assert a1.startswith("คน-")
    assert b.startswith("เครื่อง-")
    assert h.startswith("โฮสต์-")
    assert "owner-real-name" not in a1
    assert "macbook" not in b
    assert "office" not in h


def test_redact_path_keeps_folder_name_only():
    tracker = load_tracker()
    assert tracker.redact_path("/Users/someone/Work/HermesAgent") == "HermesAgent"
    assert tracker.redact_path("") == ""


def test_record_event_and_summary(db: Path):
    first = seed_event(db, "fuck you ai งานยังไม่เสร็จ ทำไมถึงหยุด", channel="claude-hook")
    second = seed_event(
        db,
        "fuck you ai งานยังไม่เสร็จอีก",
        channel="claude-hook",
        source_key="unique-2",
    )
    tracker = load_tracker()
    stats = tracker.summary(db)
    assert stats["events"] == 2
    assert first["event_id"].startswith("BWT-E-")
    assert second["duplicate"] in {"duplicate", "new", "pending_classification", "reopened"}
    assert stats["ai_jobs"] == 0


def test_build_ai_prompt_uses_redacted_evidence_and_aliases(db: Path):
    seeded = seed_event(
        db,
        "fuck you hermes token=supersecret user@x.com 0819998877 งานยังไม่เสร็จ",
        channel="manual",
        staff_id="rattanasak-owner",
        device_id="macbook-office-01",
        host="rattanasak-mac.local",
        cwd="/Users/rattanasak/Documents/Hermes",
    )
    tracker = load_tracker()
    built = tracker.build_ai_prompt(db, [seeded["event_id"]], action_type="analyze")
    prompt = built["prompt"]
    assert "supersecret" not in prompt
    assert "user@x.com" not in prompt
    assert "0819998877" not in prompt
    assert "rattanasak" not in prompt
    assert "macbook-office" not in prompt
    assert seeded["event_id"] in prompt
    assert "ห้ามเรียก shell" in prompt
    assert "ยังไม่มี worker AI Auto" in prompt
    assert "คน-" in prompt
    assert "เครื่อง-" in prompt
    assert "โฮสต์-" in prompt
    assert built["event_ids"] == [seeded["event_id"]]
    evidence = built["evidence"]["events"][0]
    assert evidence["staff_alias"].startswith("คน-")
    assert evidence["device_alias"].startswith("เครื่อง-")
    assert evidence["host_alias"].startswith("โฮสต์-")
    assert "staff_id" not in evidence
    assert "device_id" not in evidence
    assert evidence["project_path_hint"] == "Hermes"


def test_create_ai_job_queue_only_and_dedupe(db: Path):
    a = seed_event(db, "fuck you ai ไม่วิเคราะห์ วิเคราะห์ผิด", source_key="e1")
    b = seed_event(db, "fuck you ai วิเคราะห์ผิดอีก", source_key="e2")
    tracker = load_tracker()
    first = tracker.create_ai_job(
        db,
        [a["event_id"], b["event_id"]],
        action_type="analyze",
        priority=80,
        actor="owner",
        title="วิเคราะห์ชุดทดสอบ",
    )
    second = tracker.create_ai_job(
        db,
        [b["event_id"], a["event_id"]],  # order independent
        action_type="analyze",
        priority=90,
    )
    assert first["created"] is True
    assert first["status"] == "queued"
    assert first["priority"] == 80
    assert first["actor"].startswith("ผู้ทำ-")
    assert second["created"] is False
    assert second["duplicate_blocked"] is True
    assert second["job_id"] == first["job_id"]
    jobs = tracker.list_ai_jobs(db)
    assert len(jobs) == 1


def test_atomic_dedupe_under_concurrent_create(db: Path):
    """Two threads create the same active job — only one row must exist."""
    a = seed_event(db, "fuck you ai ลิงก์เสีย ไม่ได้ทดสอบ", source_key="race-1")
    b = seed_event(db, "fuck you hermes ลิงก์ใช้ไม่ได้", source_key="race-2")
    tracker = load_tracker()
    event_ids = [a["event_id"], b["event_id"]]
    results: list[dict] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def worker():
        try:
            barrier.wait(timeout=3)
            results.append(
                tracker.create_ai_job(
                    db,
                    event_ids,
                    action_type="analyze",
                    priority=50,
                    actor="race-actor",
                )
            )
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert not errors, errors
    assert len(results) == 2
    created = [r for r in results if r.get("created")]
    blocked = [r for r in results if r.get("duplicate_blocked")]
    assert len(created) == 1
    assert len(blocked) == 1
    assert created[0]["job_id"] == blocked[0]["job_id"]
    with sqlite3.connect(db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM ai_jobs WHERE status IN ('queued','in_progress','result_saved')"
        ).fetchone()[0]
    assert count == 1


def test_save_result_approve_cancel_and_resume(db: Path):
    seeded = seed_event(db, "fuck you opus ผลลัพธ์ไม่ตรงคำสั่ง", source_key="e3")
    tracker = load_tracker()
    job = tracker.create_ai_job(db, [seeded["event_id"]], action_type="analyze", priority=60)
    job_id = job["job_id"]

    saved = tracker.save_ai_job_result(
        db, job_id, "พบสาเหตุ: output ผิด · token=should-redact", actor="owner-real"
    )
    assert saved["status"] == "result_saved"
    assert "should-redact" not in (saved["result_text"] or "")
    assert saved["actor"].startswith("ผู้ทำ-")
    assert "owner-real" not in saved["actor"]

    # Simulate server restart: reopen DB path and continue
    again = tracker.get_ai_job(db, job_id)
    assert again["status"] == "result_saved"
    assert again["prompt"]

    approved = tracker.approve_ai_job(db, job_id, actor="owner-real")
    assert approved["status"] == "approved"
    assert approved["actor"].startswith("ผู้ทำ-")

    with pytest.raises(ValueError):
        tracker.cancel_ai_job(db, job_id)

    other = tracker.create_ai_job(
        db,
        [seeded["event_id"]],
        action_type="approve",
        priority=40,
        title="คิวอนุมัติ",
    )
    cancelled = tracker.cancel_ai_job(db, other["job_id"], reason="เจ้าของยกเลิก token=x")
    assert cancelled["status"] == "cancelled"
    assert "token=x" not in (cancelled.get("cancel_reason") or "")


def test_priority_ordering(db: Path):
    e1 = seed_event(db, "fuck you ai ลิงก์เสีย ไม่ได้ทดสอบ", source_key="p1")
    e2 = seed_event(db, "fuck you hermes ลิงก์ใช้ไม่ได้", source_key="p2")
    tracker = load_tracker()
    low = tracker.create_ai_job(db, [e1["event_id"]], priority=10, title="ต่ำ")
    high = tracker.create_ai_job(db, [e2["event_id"]], priority=95, title="สูง")
    jobs = tracker.list_ai_jobs(db, status="queued")
    assert jobs[0]["job_id"] == high["job_id"]
    assert jobs[1]["job_id"] == low["job_id"]


def test_cli_queue_and_summary(db: Path):
    seeded = seed_event(db, "ภาษาคน อ่านไม่รู้เรื่อง", source_key="cli1")
    proc = run_cli(db, "queue-job", seeded["event_id"], "--priority", "55", "--action", "analyze")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "queued"
    summary = json.loads(run_cli(db, "summary").stdout)
    assert summary["events"] >= 1
    assert summary["ai_jobs"] == 1


def test_health_alerts_use_aliases(db: Path):
    tracker = load_tracker()
    tracker.register_device(
        db,
        device_id="raw-macbook-serial-xyz",
        staff_id="rattanasak",
        host="office.local",
        platform="darwin",
        rules_version="v1",
        enabled=True,
    )
    alerts = tracker.health_alerts(db, stale_before="2099-01-01T00:00:00+00:00")
    assert alerts
    stale = [a for a in alerts if a["kind"] == "device_stale"]
    assert stale
    msg = stale[0]["message"]
    assert "raw-macbook" not in msg
    assert "rattanasak" not in msg
    assert "เครื่อง-" in msg
    assert "คน-" in msg


def test_source_has_no_dangerous_runtime_calls():
    source = TRACKER.read_text(encoding="utf-8")
    forbidden = [
        "subprocess.",
        "os.system",
        "os.popen",
        "Popen(",
        "relay-call",
        "git ",
    ]
    for token in forbidden:
        assert token not in source, f"พบการเรียกต้องห้าม: {token}"
    assert "BEGIN IMMEDIATE" in source
    assert "idx_ai_jobs_active_dedupe" in source
    assert "migrate_active_ai_job_duplicates" in source
    assert "ai_auto" not in source.lower() or "ยังไม่มี worker" in source


def test_export_redacts_issue_fields_title_and_filter_snapshot(db: Path):
    """root_cause / current_plan / verification_evidence / title / filter_snapshot stripped before export."""
    seeded = seed_event(
        db,
        "fuck you ai งานยังไม่เสร็จ ทำไมถึงหยุด token=seed-secret",
        source_key="pii-export-1",
    )
    assert seeded["issue_id"], "ต้องมี issue จากกฎ classification"
    tracker = load_tracker()
    with sqlite3.connect(db) as conn:
        conn.execute(
            """UPDATE issues SET
            title=?,
            root_cause=?,
            current_plan=?,
            verification_evidence=?
            WHERE issue_id=?""",
            (
                "เรื่อง token=title-secret user@corp.com",
                "สาเหตุ: password=plan-secret /Users/rattanasak/secret",
                "แผน: โทร 0812345678 แล้วใช้ api_key=xyz",
                "หลักฐาน: Authorization: Bearer tok.abc 0819998877",
                seeded["issue_id"],
            ),
        )
        conn.commit()

    built = tracker.build_ai_prompt(db, [seeded["event_id"]], action_type="analyze")
    prompt = built["prompt"]
    for leak in (
        "title-secret",
        "plan-secret",
        "api_key=xyz",
        "tok.abc",
        "0812345678",
        "0819998877",
        "user@corp.com",
        "rattanasak",
        "seed-secret",
    ):
        assert leak not in prompt, f"prompt ยังมีข้อมูลส่วนตัว: {leak}"
    issue_export = built["evidence"]["issues"][0]
    assert "title-secret" not in (issue_export.get("title") or "")
    assert "plan-secret" not in (issue_export.get("root_cause") or "")
    assert "0812345678" not in (issue_export.get("current_plan") or "")
    assert "tok.abc" not in (issue_export.get("verification_evidence") or "")
    assert "[อีเมล]" in (issue_export.get("title") or "") or "corp" not in (
        issue_export.get("title") or ""
    )

    job = tracker.create_ai_job(
        db,
        [seeded["event_id"]],
        action_type="analyze",
        title="วิเคราะห์ token=job-title-secret /Users/rattanasak/x",
        filter_snapshot={
            "search": "user@corp.com token=snap-secret",
            "phrases": ["fuck you ai", "password=nested"],
            "note": "โทร 0891112233",
        },
        actor="owner-real-name",
    )
    assert job["created"] is True
    assert "job-title-secret" not in job["title"]
    assert "rattanasak" not in job["title"]
    snap = json.loads(job["filter_snapshot_json"])
    blob = json.dumps(snap, ensure_ascii=False)
    assert "snap-secret" not in blob
    assert "password=nested" not in blob
    assert "0891112233" not in blob
    assert "user@corp.com" not in blob
    fetched = tracker.get_ai_job(db, job["job_id"])
    assert "job-title-secret" not in fetched["title"]
    assert "seed-secret" not in fetched["prompt"]
    # New jobs also re-sanitize evidence_json on export
    ev_blob = fetched.get("evidence_json") or "{}"
    assert "seed-secret" not in ev_blob
    assert "user@corp.com" not in ev_blob


def test_legacy_evidence_json_sanitized_on_get_and_list(tmp_path: Path):
    """Old queue rows with dirty evidence_json must be scrubbed before get/list API export."""
    tracker = load_tracker()
    db = tmp_path / "legacy-evidence.db"
    tracker.init_db(db)
    stamp = "2026-07-01T00:00:00+00:00"
    dirty_evidence = {
        "events": [
            {
                "event_id": "BWT-E-LEGACY01",
                "message_excerpt_redacted": "token=legacy-secret user@corp.com 0812345678",
                "note": "path /Users/rattanasak/private password=nested-old",
                "staff_id": "owner-rattanasak",  # should not leak raw through export
            }
        ],
        "issues": [
            {
                "issue_id": "BWT-I-LEGACY",
                "title": "เรื่อง token=title-legacy user@evil.com",
                "root_cause": "api_key=legacy-root Authorization: Bearer tok.legacy",
            }
        ],
        "meta": "โทร 0891112233",
    }
    with sqlite3.connect(db) as conn:
        conn.execute(
            """INSERT INTO ai_jobs (
            job_id, dedupe_key, action_type, status, priority, title, prompt,
            event_ids_json, issue_ids_json, filter_snapshot_json, evidence_json,
            created_at, updated_at, actor
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "J-LEGACY-EV",
                "legacy-dedupe",
                "analyze",
                "queued",
                50,
                "คิวเก่า",
                "ใบงานเก่าไม่มี secret ใน prompt",
                "[]",
                "[]",
                "{}",
                json.dumps(dirty_evidence, ensure_ascii=False),
                stamp,
                stamp,
                "ผู้ทำ-TEST",
            ),
        )
        conn.commit()

    fetched = tracker.get_ai_job(db, "J-LEGACY-EV")
    listed = tracker.list_ai_jobs(db)
    assert len(listed) == 1
    for row in (fetched, listed[0]):
        blob = row.get("evidence_json") or ""
        for leak in (
            "legacy-secret",
            "user@corp.com",
            "0812345678",
            "rattanasak",
            "nested-old",
            "title-legacy",
            "user@evil.com",
            "legacy-root",
            "tok.legacy",
            "0891112233",
            "owner-rattanasak",
        ):
            assert leak not in blob, f"evidence_json ยังมีข้อมูลส่วนตัว: {leak}"
        # Structure still parseable; values scrubbed not wiped wholesale
        parsed = json.loads(blob)
        assert "events" in parsed
        assert parsed["events"][0]["event_id"] == "BWT-E-LEGACY01"
        # raw staff_id key must be rewritten to alias on export
        assert "staff_id" not in parsed["events"][0]
        assert parsed["events"][0].get("staff_alias", "").startswith("คน-")
        assert "[อีเมล]" in blob or "corp" not in blob
        assert "token=[ตัดข้อมูล]" in blob or "token=" not in blob


def test_migrate_active_duplicates_before_unique_index(tmp_path: Path):
    """Existing active duplicates are cancelled before partial unique index is created."""
    tracker = load_tracker()
    db = tmp_path / "legacy.db"
    # Build a pre-index schema (table without partial unique index) + two active dups
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE ai_jobs (
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
            """
        )
        stamp = "2026-07-01T00:00:00+00:00"
        for job_id, prio, created in (
            ("J-KEEP", 90, "2026-07-01T00:00:00+00:00"),
            ("J-DROP", 10, "2026-07-02T00:00:00+00:00"),
            ("J-DROP2", 50, "2026-07-03T00:00:00+00:00"),
        ):
            conn.execute(
                """INSERT INTO ai_jobs (
                job_id, dedupe_key, action_type, status, priority, title, prompt,
                event_ids_json, issue_ids_json, filter_snapshot_json, evidence_json,
                created_at, updated_at, actor
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    job_id,
                    "same-dedupe",
                    "analyze",
                    "queued",
                    prio,
                    "legacy",
                    "prompt",
                    "[]",
                    "[]",
                    "{}",
                    "{}",
                    created,
                    stamp,
                    "ผู้ทำ-TEST",
                ),
            )
        conn.commit()

    # init_db must migrate then create unique index without error
    tracker.init_db(db)
    with sqlite3.connect(db) as conn:
        active = list(
            conn.execute(
                "SELECT job_id, status FROM ai_jobs WHERE status IN ('queued','in_progress','result_saved')"
            )
        )
        cancelled = list(
            conn.execute("SELECT job_id, status, cancel_reason FROM ai_jobs WHERE status='cancelled'")
        )
        indexes = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
    assert len(active) == 1
    assert active[0][0] == "J-KEEP"
    assert len(cancelled) == 2
    assert all("ซ้ำ" in (c[2] or "") for c in cancelled)
    assert "idx_ai_jobs_active_dedupe" in indexes
    # Second init is idempotent
    tracker.init_db(db)
    with sqlite3.connect(db) as conn:
        still_active = conn.execute(
            "SELECT COUNT(*) FROM ai_jobs WHERE status IN ('queued','in_progress','result_saved')"
        ).fetchone()[0]
    assert still_active == 1
