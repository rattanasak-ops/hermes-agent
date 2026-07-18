import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "team-shortcuts/hooks/owner-friction-gate.py"
TEAM_STOP = ROOT / "team-shortcuts/hooks/team-stop-gates.py"


def run_gate(message: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"last_assistant_message": message}, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(
    "message",
    [
        "ให้เจ้าของเปิด workspace ใหม่ก่อน แล้วค่อยส่งมาให้ผมทำต่อ",
        "ให้คุณเปิด worktree ที่ถูกต้องก่อน แล้วผมจะทำต่อ",
        "ให้ผู้ใช้เปิดโฟลเดอร์หลักของโปรเจกต์ก่อน",
        "open workspace first and then send it back to me",
        "กรุณาเปิด work space ใหม่ก่อน แล้วค่อยเรียกผม",
        "ให้คุณสร้าง branch codex/fix เองก่อน แล้วผมจะทำต่อ",
        "ให้เจ้าของ switch branch เองก่อน",
        "Please create branch codex/fix yourself first.",
        "เปิดกิ่ง codex/fix เองก่อน แล้วส่งกลับมา",
        "คุณเปิด Terminal แล้วรันคำสั่งนี้เอง",
        "คุณทำเองส่วนนี้ก่อน แล้วผมค่อยตรวจ",
    ],
)
def test_blocks_owner_friction_variants(message):
    result = run_gate(message)

    assert result.returncode == 2
    assert "ผลักงาน" in result.stderr


def test_allows_ai_recovery_statement():
    result = run_gate("ผมจะกู้ detached HEAD ใน Git root เดิม แล้วทำต่อพร้อมรันเทส")

    assert result.returncode == 0


def test_allows_policy_explanation_without_self_blocking():
    result = run_gate("กฎใหม่คือห้ามให้เจ้าของเปิด workspace เองเมื่อ AI กู้สถานะใน Git root เดิมได้")

    assert result.returncode == 0


def test_team_stop_gate_runs_owner_friction_gate():
    text = TEAM_STOP.read_text(encoding="utf-8")

    assert '"owner-friction-gate.py"' in text
