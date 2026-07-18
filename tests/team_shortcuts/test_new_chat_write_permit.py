from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "team-shortcuts/payload/skills/prompt-shortcuts/references"


def test_new_chat_uses_current_workspace_only():
    text = (REFS / "use-new-chat.md").read_text(encoding="utf-8")

    assert 'version: "4.0"' in text
    assert "CURRENT_WORKSPACE_ONLY" in text
    assert "CURRENT_WORKSPACE_READY" in text
    assert "CURRENT_WORKSPACE_READ_ONLY" in text
    assert "CURRENT_WORKSPACE_BLOCKED" in text
    assert "การพิมพ์ `Use New Chat` ไม่ใช่คำอนุมัติให้สร้าง Worktree หรือกิ่ง" in text
    assert "ห้ามเรียก `hermes-new-chat open`" in text


def test_relay_and_continue_are_confined_to_current_workspace():
    relay = (REFS / "use-ai-relay.md").read_text(encoding="utf-8")
    continuation = (REFS / "use-continue.md").read_text(encoding="utf-8")

    assert 'version: "3.0"' in relay
    assert "Current Workspace Permit" in relay
    assert "Relay ห้ามสร้าง ลบ ย้าย หรือสลับ Worktree/กิ่ง" in relay
    assert 'version: "5.0"' in continuation
    assert "Current Workspace Permit" in continuation
    assert "ห้ามสร้างหรือสลับ Worktree/กิ่งเอง" in continuation


def test_same_reviewer_method_stops_after_two_failures():
    relay = (REFS / "use-ai-relay.md").read_text(encoding="utf-8")
    continuation = (REFS / "use-continue.md").read_text(encoding="utf-8")

    assert "สูงสุด 2 รอบต่อปัญหา" in relay
    assert "ห้ามยิงรอบที่ 3" in relay
    assert "เปลี่ยนเป็น test/lint/build/gate-run" in relay
    assert "ผู้ตรวจคนละค่าย" in continuation


def test_policy_keeps_secret_and_dangerous_command_gates():
    policy = (REFS / "work-execution-policy.md").read_text(encoding="utf-8")

    for value in (".env", ".hermes", ".grok", "force push", "reset", "คำสั่งลบถาวร"):
        assert value in policy
    assert "AI Relay เป็นทางเลือก" in policy
