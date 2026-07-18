"""Tests for Badword Command Center dashboard + local API (P5/P8) + hardening."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.client import HTTPConnection
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TRACKER = ROOT / "bin" / "badword_tracker.py"
DASHBOARD = ROOT / "bin" / "badword_dashboard.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Python 3.14+ dataclasses require the module to be in sys.modules
    # before @dataclass processes annotations (importlib alone is not enough).
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_tracker():
    return load_module(TRACKER, "badword_tracker_for_dashboard_tests")


def load_dashboard():
    return load_module(DASHBOARD, "badword_dashboard_under_test")


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    db = tmp_path / "tracker.db"
    tracker = load_tracker()
    tracker.init_db(db)
    tracker.record_event(
        db,
        "fuck you ai งานยังไม่เสร็จ ทำไมถึงหยุด token=live-secret user@corp.com",
        staff_id="owner-rattanasak",
        device_id="macbook-a-serial",
        host="office-mac.local",
        project_id="Hermes",
        cwd="/Users/rattanasak/Documents/Hermes",
        channel="claude-hook",
        source_key="seed-1",
    )
    tracker.record_event(
        db,
        "ภาษาคน อ่านไม่รู้เรื่อง",
        staff_id="owner-rattanasak",
        device_id="macbook-a-serial",
        host="office-mac.local",
        project_id="Hermes",
        cwd="/Users/rattanasak/Documents/Hermes",
        channel="claude-hook",
        source_key="seed-2",
    )
    tracker.record_event(
        db,
        "fuck you hermes ลิงก์เสีย ไม่ได้ทดสอบ",
        staff_id="staff-b-private",
        device_id="mac-b-serial",
        host="mac-b.local",
        project_id="Other",
        cwd="/Users/staff-b/Other",
        channel="gateway",
        source_key="seed-3",
    )
    return db


def test_render_html_has_p5_and_p8_controls(seeded_db: Path, tmp_path: Path):
    dashboard = load_dashboard()
    html = dashboard.render(seeded_db)
    out = tmp_path / "out.html"
    out.write_text(html, encoding="utf-8")
    text = out.read_text(encoding="utf-8")

    must_have = [
        "ป้ายคำยอดนิยม",
        "phrase-chip",
        "กลุ่มหลัก",
        "ตัวกรองเพิ่มเติม",
        "activeFilters",
        "analyzeVisible",
        "วิเคราะห์ทั้งหมดที่เห็น",
        "ตารางงาน AI และประวัติ",
        "copyPrompt",
        "saveResult",
        "approveJob",
        "cancelJob",
        "priority",
        "ยังไม่มี worker AI Auto",
        "X-Badword-Token",
        "selectedPhrases",
        "selectedEvents",
        "renderPhraseRank",
        "ชุดที่โหลด",
        "ชุดที่โหลดทั้งหมด",
        "อันดับคำคำนวณ",
        "ชุดเดียวกับตาราง",
        "รวมป้ายคำที่เลือก",
    ]
    for token in must_have:
        assert token in text, f"missing {token}"

    # four main filter groups present
    assert text.count("กลุ่มหลัก") >= 4
    # multi-chip must not fight exclusive dropdown: phrase not in selectIds list
    assert 'const selectIds = ["source","staff","device","project","ai","category","status"]' in text
    assert "selectIds = [\"source\",\"staff\",\"device\",\"project\",\"ai\",\"category\",\"status\",\"phrase\"]" not in text
    # phrase rank must use the same subset as the table AFTER selected phrase chips
    assert "const items = selectedEvents()" in text
    assert 'const rankSource = group(items, "phrase")' in text
    assert 'group(base, "phrase")' not in text
    assert "ฐานกรองก่อนเลือกคำ" not in text
    # "ทั้งหมด" must not claim full DB when we only load a slice — use loaded-scope wording
    assert "จากทั้งหมด" not in text
    assert "จากชุดที่โหลด" in text
    assert "ชุดที่โหลดทั้งหมด" in text
    # raw identities must not appear in HTML payload
    assert "owner-rattanasak" not in text
    assert "macbook-a-serial" not in text
    assert "office-mac.local" not in text
    assert "live-secret" not in text
    assert "user@corp.com" not in text
    assert "/Users/rattanasak" not in text


def test_phrase_rank_and_event_list_share_same_dataset(seeded_db: Path):
    dashboard = load_dashboard()
    payload = dashboard.load_dashboard_payload(seeded_db)
    assert payload["dataset_size"] == len(payload["events"])
    assert payload["ai_auto_worker"] is False
    assert payload["db_event_total"] >= payload["dataset_size"]
    assert "ชุดที่โหลด" in payload["scope_label"]
    rank_total = sum(item["count"] for item in payload["phrase_rank"])
    assert rank_total == len(payload["events"])
    # aliases only
    for event in payload["events"]:
        assert event["staff"].startswith("คน-")
        assert event["device"].startswith("เครื่อง-")
        assert event["host"].startswith("โฮสต์-")
        assert event["cwd"] in {"Hermes", "Other", ""}
        assert "rattanasak" not in event["excerpt"]
        assert "live-secret" not in event["excerpt"]


def test_extract_api_token_header_only_not_query_string():
    dashboard = load_dashboard()

    class FakeHandler:
        def __init__(self, headers: dict[str, str]):
            self.headers = headers

    # header present
    h = FakeHandler({"X-Badword-Token": "from-header", "X-Api-Token": ""})
    assert dashboard.extract_api_token(h, {"token": ["from-query"]}) == "from-header"
    # query only — must be rejected (empty)
    h2 = FakeHandler({})
    assert dashboard.extract_api_token(h2, {"token": ["from-query-only"]}) == ""
    # X-Api-Token alternate header works
    h3 = FakeHandler({"X-Api-Token": "alt-header"})
    assert dashboard.extract_api_token(h3, {"token": ["ignored"]}) == "alt-header"


def test_host_and_origin_guards():
    dashboard = load_dashboard()
    assert dashboard.host_header_allowed("127.0.0.1:8765") is True
    assert dashboard.host_header_allowed("localhost:8765") is True
    assert dashboard.host_header_allowed("[::1]:8765") is True
    assert dashboard.host_header_allowed("evil.example.com") is False
    assert dashboard.host_header_allowed("0.0.0.0:8765") is False
    assert dashboard.host_header_allowed("") is False

    assert dashboard.origin_header_allowed("") is True  # curl / same-origin omit
    assert dashboard.origin_header_allowed("http://127.0.0.1:8765") is True
    assert dashboard.origin_header_allowed("http://localhost:3000") is True
    assert dashboard.origin_header_allowed("https://evil.example.com") is False


def test_tokens_match_safe():
    dashboard = load_dashboard()
    assert dashboard.tokens_match("abc", "abc") is True
    assert dashboard.tokens_match("abc", "abd") is False
    assert dashboard.tokens_match("", "abc") is False
    assert dashboard.tokens_match("short", "longer-token") is False


def test_cli_write_html(seeded_db: Path, tmp_path: Path):
    html_path = tmp_path / "dash.html"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [
            sys.executable,
            str(DASHBOARD),
            "--db",
            str(seeded_db),
            "--html",
            str(html_path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert html_path.is_file()
    body = html_path.read_text(encoding="utf-8")
    assert "Badword Command Center" in body
    # static export embeds empty token → queue API disabled by design
    assert 'const apiToken = ""' in body or "const apiToken = \"\"" in body


def _free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _http_json(method: str, url: str, payload: dict | None = None, headers: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": body}
        return err.code, parsed


def test_local_server_api_queue_only_no_side_effects(seeded_db: Path):
    dashboard = load_dashboard()
    tracker = load_tracker()
    port = _free_port()
    server_errors: list[BaseException] = []
    api_token = "test-token-hardening-001"
    Handler = dashboard.make_handler(seeded_db, None, api_token=api_token)

    def run_server():
        try:
            from http.server import ThreadingHTTPServer

            httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            httpd.timeout = 0.5
            run_server.httpd = httpd  # type: ignore[attr-defined]
            while getattr(run_server, "alive", True):
                httpd.handle_request()
            httpd.server_close()
        except BaseException as exc:  # pragma: no cover
            server_errors.append(exc)

    run_server.alive = True  # type: ignore[attr-defined]
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(0.1)
    auth = {"X-Badword-Token": api_token}

    try:
        # health (no token required, but host must be local)
        status, health = _http_json("GET", f"http://127.0.0.1:{port}/api/health")
        assert status == 200
        assert health["ok"] is True
        assert health["bind_only"] == "127.0.0.1"
        assert health["ai_auto_worker"] is False
        assert health["auth"]["token_required"] is True
        assert health["auth"]["host_origin_checked"] is True
        assert health["auth"]["header_only"] is True
        assert health["auth"]["query_string_token_accepted"] is False
        assert health["safety"]["shell"] is False
        assert health["safety"]["git"] is False
        assert health["safety"]["relay"] is False
        assert health["safety"]["code_edit"] is False

        # dashboard page embeds token for browser use
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as resp:
            page = resp.read().decode("utf-8")
        assert "Badword Command Center" in page
        assert "phrase-chip" in page
        assert api_token in page
        assert "ยังไม่มี worker AI Auto" in page
        assert "renderPhraseRank" in page
        assert "ชุดที่โหลด" in page

        # missing token → 401
        status, err = _http_json(
            "POST",
            f"http://127.0.0.1:{port}/api/jobs",
            {"action_type": "analyze", "event_ids": ["x"], "priority": 10},
        )
        assert status == 401
        assert "รหัส" in err.get("error", "")

        # query-string token alone must NOT authenticate
        status, err = _http_json(
            "GET",
            f"http://127.0.0.1:{port}/api/jobs?token={api_token}",
        )
        assert status == 401
        assert "รหัส" in err.get("error", "")

        # bad origin → 403
        status, err = _http_json(
            "GET",
            f"http://127.0.0.1:{port}/api/jobs",
            headers={**auth, "Origin": "https://evil.example.com"},
        )
        assert status == 403
        assert "Origin" in err.get("error", "")

        events = tracker.list_events(seeded_db)
        event_ids = [row["event_id"] for row in events[:2]]
        status, created = _http_json(
            "POST",
            f"http://127.0.0.1:{port}/api/jobs",
            {
                "action_type": "analyze",
                "event_ids": event_ids,
                "priority": 77,
                "title": "วิเคราะห์ token=title-leak user@corp.com",
                "filter_snapshot": {
                    "phrases": ["fuck you ai"],
                    "search": "password=snap-leak 0812345678",
                },
                "actor": "owner-rattanasak",
            },
            headers=auth,
        )
        assert status == 200
        assert created["created"] is True
        assert created["status"] == "queued"
        job_id = created["job_id"]
        assert "token=" not in created["prompt"] or "token=[ตัดข้อมูล]" in created["prompt"]
        assert "ห้ามเรียก shell" in created["prompt"]
        assert "ยังไม่มี worker AI Auto" in created["prompt"]
        assert "owner-rattanasak" not in created.get("actor", "")
        assert created["actor"].startswith("ผู้ทำ-")
        assert "rattanasak" not in created["prompt"]
        assert "title-leak" not in created.get("title", "")
        snap_raw = created.get("filter_snapshot_json") or "{}"
        assert "snap-leak" not in snap_raw
        assert "0812345678" not in snap_raw

        # events API returns aliases only
        status, listed_events = _http_json(
            "GET", f"http://127.0.0.1:{port}/api/events", headers=auth
        )
        assert status == 200
        assert listed_events["aliased"] is True
        for event in listed_events["events"]:
            assert event["staff"].startswith("คน-")
            assert "owner-rattanasak" not in json.dumps(event)

        # duplicate blocked
        status, dup = _http_json(
            "POST",
            f"http://127.0.0.1:{port}/api/jobs",
            {
                "action_type": "analyze",
                "event_ids": event_ids,
                "priority": 88,
            },
            headers=auth,
        )
        assert status == 200
        assert dup["duplicate_blocked"] is True

        # save / approve
        status, saved = _http_json(
            "POST",
            f"http://127.0.0.1:{port}/api/jobs/{job_id}/result",
            {"result_text": "สรุป: ต้องตรวจ verification token=nope"},
            headers=auth,
        )
        assert status == 200
        assert saved["status"] == "result_saved"
        assert "nope" not in (saved.get("result_text") or "")

        status, approved = _http_json(
            "POST",
            f"http://127.0.0.1:{port}/api/jobs/{job_id}/approve",
            {},
            headers=auth,
        )
        assert status == 200
        assert approved["status"] == "approved"

        # jobs list persists (resume after "restart" = re-read DB)
        status, listed = _http_json(
            "GET", f"http://127.0.0.1:{port}/api/jobs", headers=auth
        )
        assert status == 200
        assert listed["count"] >= 1
        assert any(j["job_id"] == job_id for j in listed["jobs"])

        # Source inspection: dashboard module must not shell/git/relay
        source = DASHBOARD.read_text(encoding="utf-8")
        for token in ("subprocess.", "os.system", "os.popen", "Popen(", "relay-call"):
            assert token not in source
        assert "host_header_allowed" in source
        assert "origin_header_allowed" in source
        assert "ai_auto_worker" in source
    finally:
        run_server.alive = False  # type: ignore[attr-defined]
        try:
            HTTPConnection("127.0.0.1", port, timeout=0.5).request("GET", "/api/health")
        except Exception:
            pass
        thread.join(timeout=2)
        assert not server_errors, server_errors


def test_serve_rejects_non_local_bind(seeded_db: Path):
    dashboard = load_dashboard()
    with pytest.raises(SystemExit):
        dashboard.serve(seeded_db, host="0.0.0.0", port=9999)
