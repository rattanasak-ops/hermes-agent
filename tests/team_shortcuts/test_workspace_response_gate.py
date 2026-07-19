from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "team-shortcuts/hooks/enforce-workspace-response.py"
PHASE_GATE = ROOT / "team-shortcuts/hooks/enforce-phase-autonomy.py"


def run_gate(message: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps({"last_assistant_message": message}, ensure_ascii=False),
        capture_output=True,
        text=True,
    )


def run_hermes_transform(message: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps(
            {
                "hook_event_name": "transform_llm_output",
                "extra": {"response_text": message},
            },
            ensure_ascii=False,
        ),
        capture_output=True,
        text=True,
    )


def test_blocks_answer_that_pushes_branch_or_workspace_handling_to_owner():
    result = run_gate(
        "การกระทำเดียวที่ต้องให้เจ้าของทำ: เปิดหรือสร้างกิ่งงาน S1 ให้ workspace นี้ก่อน"
    )

    assert result.returncode == 2
    assert "WORKSPACE_OWNER_HANDOFF_BLOCKED" in result.stderr
    assert "hermes-current-workspace-recover" in result.stderr


def test_allows_ai_owned_recovery_or_machine_conflict_report():
    recovered = run_gate(
        "ผมกู้กิ่งเดิมด้วย hermes-current-workspace-recover ใน Git root เดิมแล้ว ไฟล์ค้างอยู่ครบ"
    )
    conflict = run_gate(
        "RECOVERY_CONFLICT: ไฟล์ค้างอยู่บน SHA คนละจุด จึงหยุดเพื่อรักษางาน"
    )

    assert recovered.returncode == 0, recovered.stderr
    assert conflict.returncode == 0, conflict.stderr


def test_hermes_replaces_owner_handoff_with_machine_action():
    result = run_hermes_transform(
        "ให้เจ้าของเปิด branch ที่ถูกต้อง แล้วพิมพ์ ok เพื่อทำงานต่อ"
    )

    assert result.returncode == 0
    replacement = json.loads(result.stdout)["response_text"]
    assert replacement.startswith("WORKSPACE_OWNER_HANDOFF_BLOCKED")
    assert "ถ้าเป็น detached HEAD" in replacement


def test_team_stop_bundle_runs_workspace_response_gate():
    bundle = (ROOT / "team-shortcuts/hooks/team-stop-gates.py").read_text(encoding="utf-8")

    assert '"enforce-workspace-response.py"' in bundle
    assert '"enforce-phase-autonomy.py"' in bundle


def test_blocks_reapproval_question_while_safe_phase_work_remains():
    result = subprocess.run(
        [sys.executable, str(PHASE_GATE)],
        input=json.dumps(
            {
                "last_assistant_message": (
                    "SPEC-P6-I1 ผ่านแล้ว แต่ I2-I4 ยังไม่ทำ "
                    "อนุมัติให้ผมทำ I2-I4 ต่อไหมครับ"
                )
            },
            ensure_ascii=False,
        ),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "PHASE_CONTINUATION_REQUIRED" in result.stderr


def test_allows_one_evidence_backed_external_blocker_question():
    result = subprocess.run(
        [sys.executable, str(PHASE_GATE)],
        input=json.dumps(
            {
                "last_assistant_message": (
                    "OWNER_INPUT_REQUIRED: LOGIN_REQUIRED\n"
                    "หลักฐาน: ระบบตอบ 401 หลังเรียกบัญชีจริง 3/3 รอบ\n"
                    "กรุณาเข้าสู่ระบบหนึ่งครั้ง แล้วผมจะทำเฟสเดิมต่อ"
                )
            },
            ensure_ascii=False,
        ),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
