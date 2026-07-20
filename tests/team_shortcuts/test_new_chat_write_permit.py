from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "team-shortcuts/payload/skills/prompt-shortcuts/references"


def test_new_chat_checks_the_current_workspace_before_writes():
    text = (REFS / "use-new-chat.md").read_text(encoding="utf-8")

    assert 'version: "4.3"' in text
    assert "CURRENT_WORKSPACE_ONLY" in text
    assert "git rev-parse --show-toplevel" in text
    assert "git branch --show-current" in text
    assert "git rev-parse HEAD" in text
    assert "git status --short --branch" in text
    assert "CURRENT_WORKSPACE_READY" in text
    assert "ห้ามแก้ไฟล์ก่อนรายงาน" in text


def test_relay_and_continue_keep_writes_in_the_approved_phase_scope():
    relay = (REFS / "use-ai-relay.md").read_text(encoding="utf-8")
    continuation = (REFS / "use-continue.md").read_text(encoding="utf-8")

    assert 'version: "3.0"' in relay
    assert "พื้นที่และกิ่งปัจจุบันเท่านั้น" in relay
    assert "Relay ไม่มีสิทธิ์สร้างหรือสลับ Worktree/กิ่ง" in relay
    assert "task_id + branch + base_sha + allowed_paths + external_effect" in continuation
    assert "อนุมัติ Phase แล้วทำทุก issue ใน Phase ต่อเองได้" in continuation


def test_same_reviewer_method_stops_after_two_failures():
    relay = (REFS / "use-ai-relay.md").read_text(encoding="utf-8")
    new_chat = (REFS / "use-new-chat.md").read_text(encoding="utf-8")
    continuation = (REFS / "use-continue.md").read_text(encoding="utf-8")

    assert "สูงสุด 2 รอบต่อปัญหา" in relay
    assert "ห้ามยิงรอบที่ 3" in relay
    assert "เปลี่ยนเป็น test/lint/build/gate-run" in relay
    assert "ห้ามเรียกรอบที่ 3" in new_chat
    assert 'version: "5.4"' in continuation
    assert "ผู้ตรวจคนละค่าย" in continuation


def test_conditional_details_are_not_loaded_for_every_chat():
    main = (REFS / "use-new-chat.md").read_text(encoding="utf-8")
    detail = (REFS / "use-new-chat-conditional-gates.md").read_text(encoding="utf-8")

    assert "use-new-chat-conditional-gates.md" not in main
    assert "อ่านไฟล์นี้เฉพาะเมื่อ" in detail
    assert "Team Claim Gate" in detail
