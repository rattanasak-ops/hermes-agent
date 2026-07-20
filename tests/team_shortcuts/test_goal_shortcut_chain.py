from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "team-shortcuts/payload/skills/prompt-shortcuts/references"
sys.path.insert(0, str(ROOT))
PROMPTS = (
    "use-agent.md",
    "use-act-as.md",
    "use-comply.md",
    "use-continue.md",
    "use-flow-guardian.md",
    "use-save-git.md",
    "use-new-chat.md",
    "use-close-chat.md",
    "use-create-design-system.md",
    "use-migrate-web.md",
    "use-qa-qc.md",
)


def test_all_related_shortcuts_read_one_goal_contract_and_name_the_next_prompt():
    assert (REFS / "goal-contract.md").is_file()
    for name in PROMPTS:
        text = (REFS / name).read_text(encoding="utf-8")
        assert "goal-contract.md" in text, name
        assert "goal_hash" in text, name
        assert "Prompt ถัดไป:" in text or "AUTO_CONTINUE:" in text, name


def test_entry_and_execution_shortcuts_have_their_specific_duties():
    agent = (REFS / "use-agent.md").read_text(encoding="utf-8")
    comply = (REFS / "use-comply.md").read_text(encoding="utf-8")
    continued = (REFS / "use-continue.md").read_text(encoding="utf-8")
    save = (REFS / "use-save-git.md").read_text(encoding="utf-8")
    assert "ทางเข้าหลัก" in agent
    assert "kind=primary" in comply and "kind=support" in comply
    assert "ใบงาน active ชนะ plan/history/แชท" in continued
    assert "GOAL_GIT_GATE_OK" in save


def test_large_phase_shortcuts_do_not_force_repeated_owner_clicks_or_relay():
    migrate = (REFS / "use-migrate-web.md").read_text(encoding="utf-8")
    qaqc = (REFS / "use-qa-qc.md").read_text(encoding="utf-8")
    design = (REFS / "use-create-design-system.md").read_text(encoding="utf-8")
    assert "เจ้าของเป็นคนพิมพ์เลขเฟสถัดไปเองทุกครั้ง" not in migrate
    assert "เจ้าของไม่ต้องพิมพ์เลขเฟสซ้ำ" in migrate
    assert "ห้ามบังคับ Use AI Relay" in qaqc
    assert "caller_goal` ต้องคัดจาก goal" in design


def test_goal_contract_defines_semantic_memory_and_central_only_repairs():
    text = (REFS / "goal-contract.md").read_text(encoding="utf-8")
    for marker in (
        ".project/active-task.json",
        "PROJECT_GOAL_DRIFT",
        "BRANCH_FROZEN",
        "SCOPE CHANGE",
        "hermes shortcut-incident record",
        "เหตุเดิมครั้งที่ 4",
        "ผลงานหลัก",
        "งานสนับสนุน",
        "AUTO_CONTINUE:",
    ):
        assert marker in text


def test_incident_tracker_reaches_every_shortcut_in_the_goal_chain():
    from plugins.shortcut_governance.store import related_shortcuts

    related = set(related_shortcuts("Use Continue"))
    expected = {
        "Use Agent",
        "Use Act-As",
        "Use Comply",
        "Use Continue",
        "Use Flow Guardian",
        "Use Save Git",
        "Use New Chat",
        "Use Close Chat",
        "Use Create Design System",
        "Use Migrate Web",
        "Use QA QC",
    }
    assert expected <= related
