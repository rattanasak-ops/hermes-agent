from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "team-shortcuts/hooks/goal_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("goal_contract_under_test", MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def contract(module, **changes):
    value = {
        "schema": module.SCHEMA,
        "task_id": "SCG-GOAL-DRIFT",
        "plan_id": "SCG",
        "goal": "กัน AI ทำงานนอกเป้าหมาย",
        "deliverables": ["ด่านกลาง", "ชุดทดสอบ"],
        "branch": "task/scg",
        "base_sha": "a" * 40,
        "allowed_paths": ["team-shortcuts/hooks/**", "tests/team_shortcuts/**"],
        "forbidden_paths": ["secrets/**"],
        "work_types": ["code", "test"],
        "owner_scope_token": "อนุมัติสเปค SCG-GOAL-DRIFT 7189f34f",
        "status": "active",
        "primary_issues": ["SCG-P6-I1", "SCG-P6-I2"],
        "support_issues": ["SCG-P7-I4"],
        "next_prompt": "Use Agent — ทำ SCG Goal Drift ต่อ",
        "frozen_at": None,
        "merge_sha": None,
    }
    value.update(changes)
    value["goal_hash"] = module.goal_hash(value)
    return value


def test_one_machine_contract_is_valid_and_renders_human_view(tmp_path):
    module = load_module()
    value = module.validate_contract(contract(module))
    text = module.render_human_view(value)
    assert value["goal_hash"] in text
    assert "SCG-GOAL-DRIFT" in text
    assert "สร้างจาก .project/active-task.json" in text


@pytest.mark.parametrize(
    ("path", "work_type", "branch", "code"),
    [
        ("secrets/key.txt", "code", "task/scg", "GOAL_PATH_FORBIDDEN"),
        ("README.md", "code", "task/scg", "GOAL_PATH_OUTSIDE_SCOPE"),
        ("team-shortcuts/hooks/gate.py", "docs", "task/scg", "GOAL_WORK_TYPE_BLOCKED"),
        ("team-shortcuts/hooks/gate.py", "code", "task/other", "GOAL_BRANCH_MISMATCH"),
    ],
)
def test_write_gate_rejects_wrong_path_type_or_branch(path, work_type, branch, code):
    module = load_module()
    result = module.check_action(contract(module), [path], work_type, branch)
    assert result["ok"] is False
    assert result["code"] == code


def test_write_gate_accepts_declared_path_type_and_branch():
    module = load_module()
    result = module.check_action(
        contract(module), ["team-shortcuts/hooks/gate.py"], "code", "task/scg"
    )
    assert result == {"ok": True, "code": "GOAL_CONTRACT_OK"}


def test_general_approval_cannot_expand_scope_but_explicit_change_can():
    module = load_module()
    current = contract(module)
    with pytest.raises(ValueError, match="SCOPE_CHANGE_TOKEN_REQUIRED"):
        module.apply_scope_change(
            current,
            {"owner_command": "อนุมัติ", "new_allowed_paths": ["README.md"]},
        )
    owner_command = module.scope_change_command(
        "SCG-GOAL-DRIFT",
        "SCG-GOAL-DRIFT-2",
        "task/scg",
        ["README.md"],
        "เพิ่มเอกสารส่งมอบ",
    )
    changed = module.apply_scope_change(
        current,
        {
            "owner_command": owner_command,
            "old_task_id": "SCG-GOAL-DRIFT",
            "new_task_id": "SCG-GOAL-DRIFT-2",
            "branch": "task/scg",
            "new_allowed_paths": ["README.md"],
            "impact": "เพิ่มเอกสารส่งมอบ",
        },
    )
    assert changed["task_id"] == "SCG-GOAL-DRIFT-2"
    assert changed["allowed_paths"] == ["README.md"]
    assert changed["goal_hash"] != current["goal_hash"]

    with pytest.raises(ValueError, match="SCOPE_CHANGE_TOKEN_REQUIRED"):
        module.apply_scope_change(
            current,
            {
                "owner_command": owner_command,
                "old_task_id": "SCG-GOAL-DRIFT",
                "new_task_id": "SCG-GOAL-DRIFT-2",
                "branch": "task/scg",
                "new_allowed_paths": ["README.md", "secrets/**"],
                "impact": "เพิ่มเอกสารส่งมอบ",
            },
        )


def test_frozen_branch_rejects_new_work():
    module = load_module()
    value = contract(module, status="frozen", frozen_at="2026-07-19T10:00:00Z", merge_sha="b" * 40)
    value["goal_hash"] = module.goal_hash(value)
    result = module.check_action(value, ["team-shortcuts/hooks/gate.py"], "code", "task/scg")
    assert result["ok"] is False
    assert result["code"] == "BRANCH_FROZEN"


def test_contract_file_rejects_tampered_goal_hash(tmp_path):
    module = load_module()
    path = tmp_path / "active-task.json"
    value = contract(module)
    value["goal"] = "เปลี่ยนเป้าหมายเงียบ"
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="GOAL_HASH_MISMATCH"):
        module.load_contract(path)


@pytest.mark.parametrize("field,value", [("status", "completed"), ("frozen_at", "2026-07-19T10:00:00Z"), ("merge_sha", "b" * 40)])
def test_status_and_freeze_evidence_are_part_of_goal_hash(field, value):
    module = load_module()
    current = contract(module)
    current[field] = value
    with pytest.raises(ValueError, match="GOAL_HASH_MISMATCH"):
        module.validate_contract(current)


def test_freeze_recomputes_hash_and_returns_a_valid_contract():
    module = load_module()
    current = contract(module)
    frozen = module.freeze_contract(current, "b" * 40, "2026-07-19T10:00:00Z")
    assert frozen["status"] == "frozen"
    assert frozen["goal_hash"] != current["goal_hash"]
    assert module.validate_contract(frozen) == frozen
