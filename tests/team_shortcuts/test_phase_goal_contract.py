from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
HOOK_DIR = ROOT / "team-shortcuts/hooks"
sys.path.insert(0, str(HOOK_DIR))

import goal_contract  # noqa: E402
from phase_state import load_state  # noqa: E402


def write_contract(root: Path) -> dict:
    value = {
        "schema": goal_contract.SCHEMA,
        "task_id": "SCG-GOAL-DRIFT",
        "plan_id": "SCG",
        "goal": "กันงานหลุดเป้า",
        "deliverables": ["ด่าน"],
        "branch": "task/scg",
        "base_sha": "a" * 40,
        "allowed_paths": ["tests/**"],
        "forbidden_paths": [],
        "work_types": ["test"],
        "owner_scope_token": "อนุมัติสเปค SCG-GOAL-DRIFT 7189f34f",
        "status": "active",
        "primary_issues": ["SCG-P8-I1"],
        "support_issues": [],
        "next_prompt": "AUTO_CONTINUE",
        "frozen_at": None,
        "merge_sha": None,
    }
    value["goal_hash"] = goal_contract.goal_hash(value)
    path = root / ".project/active-task.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return value


def write_phase(root: Path, contract: dict, *, goal_hash: str) -> Path:
    value = {
        "schema": "phase-state-v1",
        "active": True,
        "task_id": contract["task_id"],
        "goal_hash": goal_hash,
        "plan_id": "SCG",
        "phase_id": "SCG-P8",
        "approved_scope": {"owner_approval": "อนุมัติสเปค SCG-GOAL-DRIFT 7189f34f", "question_budget": 0},
        "issues": [
            {"issue_id": "SCG-P8-I1", "kind": "primary", "zone": "ZONE_A", "status": "working", "evidence": []}
        ],
    }
    path = root / ".project/phase-state.json"
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def test_phase_must_use_the_same_goal_hash_as_active_task(tmp_path):
    current = write_contract(tmp_path)
    with pytest.raises(ValueError, match="PHASE_GOAL_DRIFT"):
        load_state(write_phase(tmp_path, current, goal_hash="0" * 64))
    assert load_state(write_phase(tmp_path, current, goal_hash=current["goal_hash"]))["task_id"] == current["task_id"]
