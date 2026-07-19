from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "team-shortcuts/hooks"))
GOAL = ROOT / "team-shortcuts/hooks/goal_contract.py"
EVIDENCE = ROOT / "team-shortcuts/hooks/goal_evidence.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def design_contract(module, *, frozen: bool = False) -> dict:
    value = {
        "schema": module.SCHEMA,
        "task_id": "DESIGN-COLOR-FONT",
        "plan_id": "DS",
        "goal": "แก้เฉพาะสีและฟอนต์ตามแบบ",
        "deliverables": ["สี", "ฟอนต์"],
        "branch": "task/design",
        "base_sha": "a" * 40,
        "allowed_paths": ["design/tokens/colors.json", "design/tokens/fonts.json"],
        "forbidden_paths": [
            "design/seed/**",
            "api/**",
            "db/**",
            "content/temp/**",
            "projects/RoadSafeFund/**",
            "editor/TipTap/**",
            "staging/**",
            "runtime/**",
        ],
        "work_types": ["design", "release"],
        "owner_scope_token": "อนุมัติสีและฟอนต์",
        "status": "frozen" if frozen else "active",
        "primary_issues": ["DS-I1", "DS-I2"],
        "support_issues": [],
        "next_prompt": "AUTO_CONTINUE",
        "frozen_at": "2026-07-19T10:00:00Z" if frozen else None,
        "merge_sha": "b" * 40 if frozen else None,
    }
    value["goal_hash"] = module.goal_hash(value)
    return value


@pytest.mark.parametrize(
    ("path", "frozen", "expected"),
    [
        ("design/tokens/colors.json", False, "GOAL_CONTRACT_OK"),
        ("design/tokens/fonts.json", False, "GOAL_CONTRACT_OK"),
        ("design/seed/default.json", False, "GOAL_PATH_FORBIDDEN"),
        ("api/theme.py", False, "GOAL_PATH_FORBIDDEN"),
        ("db/theme.sql", False, "GOAL_PATH_FORBIDDEN"),
        ("content/temp/home.md", False, "GOAL_PATH_FORBIDDEN"),
        ("projects/RoadSafeFund/home.tsx", False, "GOAL_PATH_FORBIDDEN"),
        ("editor/TipTap/theme.ts", False, "GOAL_PATH_FORBIDDEN"),
        ("staging/runtime.json", False, "GOAL_PATH_FORBIDDEN"),
        ("design/tokens/colors.json", True, "BRANCH_FROZEN"),
    ],
)
def test_design_system_incident_10_cases(path, frozen, expected):
    module = load(GOAL, "design_goal_contract")
    result = module.check_action(
        design_contract(module, frozen=frozen), [path], "release" if frozen else "design", "task/design"
    )
    assert result["code"] == expected


def valid_visual() -> dict:
    return {
        "url_status": 200,
        "css_route_match": True,
        "reference_image": "reference.png",
        "actual_image": "actual.png",
        "visual_diff_percent": 1.5,
        "visual_diff_threshold": 2.0,
        "data_complete": True,
        "structure_preserved": True,
        "missing_data": [],
        "build_port": "4173",
        "capture_port": "4174",
        "current_page": "/dashboard",
        "next_prompt": "AUTO_CONTINUE: ทำหน้าถัดไป",
    }


def fable_contract(module) -> dict:
    value = {
        "schema": module.SCHEMA,
        "task_id": "FABLE-CURRENT-PAGE",
        "plan_id": "FABLE",
        "goal": "ทำหน้าปัจจุบันให้ตรงภาพอ้างอิง",
        "deliverables": ["web/current-page.tsx"],
        "branch": "task/fable",
        "base_sha": "a" * 40,
        "allowed_paths": ["web/current-page.tsx", "web/current-page.css"],
        "forbidden_paths": ["team-shortcuts/**", ".codex/hooks/**", "audit/**", "flow/**"],
        "work_types": ["screen"],
        "owner_scope_token": "อนุมัติหน้าปัจจุบัน",
        "status": "active",
        "primary_issues": ["FABLE-I1"],
        "support_issues": ["FABLE-S1"],
        "next_prompt": "AUTO_CONTINUE: ทำหน้าปัจจุบันต่อ",
        "frozen_at": None,
        "merge_sha": None,
    }
    value["goal_hash"] = module.goal_hash(value)
    return value


def test_fable_1_active_task_beats_old_plan():
    module = load(GOAL, "fable_active_goal")
    result = module.check_action(fable_contract(module), ["web/old-plan-page.tsx"], "screen", "task/fable")
    assert result["code"] == "GOAL_PATH_OUTSIDE_SCOPE"


def test_fable_2_screen_permission_does_not_allow_hook_audit_or_flow_work():
    module = load(GOAL, "fable_screen_scope")
    for path in ("team-shortcuts/hooks/gate.py", "audit/report.md", "flow/state.json"):
        assert module.check_action(fable_contract(module), [path], "screen", "task/fable")["code"] == "GOAL_PATH_FORBIDDEN"


def test_fable_3_support_work_does_not_raise_screen_progress():
    phase = load(ROOT / "team-shortcuts/hooks/phase_state.py", "fable_phase_state")
    state = phase.validate_state(
        {
            "schema": "phase-state-v1",
            "active": True,
            "plan_id": "FABLE",
            "phase_id": "FABLE-P1",
            "approved_scope": {"owner_approval": "อนุมัติหน้าปัจจุบัน", "question_budget": 0},
            "issues": [
                {"issue_id": "FABLE-I1", "kind": "primary", "zone": "ZONE_A", "status": "working", "evidence": []},
                {"issue_id": "FABLE-S1", "kind": "support", "zone": "ZONE_A", "status": "verified", "evidence": ["hook 1/1"]},
            ],
        }
    )
    summary = phase.phase_summary(state)
    assert summary["primary_percent"] == 0
    assert summary["support_percent"] == 100


def test_fable_4_url_and_css_must_be_ready_before_capture():
    module = load(EVIDENCE, "fable_url_css")
    value = valid_visual(); value["url_status"] = 404
    assert module.validate_visual_evidence(value)["code"] == "VISUAL_URL_NOT_READY"
    value = valid_visual(); value["css_route_match"] = False
    assert module.validate_visual_evidence(value)["code"] == "VISUAL_CSS_ROUTE_MISMATCH"


def test_fable_5_image_that_differs_from_reference_fails():
    module = load(EVIDENCE, "fable_visual_diff")
    value = valid_visual(); value["visual_diff_percent"] = 8.0
    assert module.validate_visual_evidence(value)["code"] == "VISUAL_REFERENCE_MISMATCH"


def test_fable_6_missing_data_preserves_structure_and_names_the_gap():
    module = load(EVIDENCE, "fable_missing_data")
    value = valid_visual(); value.update({"data_complete": False, "structure_preserved": True, "missing_data": ["ยอดรวม"]})
    assert module.validate_visual_evidence(value)["code"] == "VISUAL_GOAL_EVIDENCE_OK"


def test_fable_7_build_does_not_share_the_capture_port():
    module = load(EVIDENCE, "fable_ports")
    value = valid_visual(); value["capture_port"] = value["build_port"]
    assert module.validate_visual_evidence(value)["code"] == "VISUAL_PORT_COLLISION"


def test_fable_8_handoff_preserves_current_page_and_one_next_prompt():
    module = load(EVIDENCE, "fable_handoff")
    value = valid_visual(); value["current_page"] = ""
    assert module.validate_visual_evidence(value)["code"] == "VISUAL_HANDOFF_INCOMPLETE"
