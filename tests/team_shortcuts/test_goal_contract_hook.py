from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "team-shortcuts/hooks/enforce-goal-contract.py"
MODULE = ROOT / "team-shortcuts/hooks/goal_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("goal_contract_hook_fixture", MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def make_repo(
    tmp_path: Path, *, status: str = "active", base_sha_override: str = ""
) -> Path:
    module = load_module()
    root = tmp_path / "repo"
    (root / ".project").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "task/scg"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=root, check=True)
    base_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    value = {
        "schema": module.SCHEMA,
        "task_id": "SCG-GOAL-DRIFT",
        "plan_id": "SCG",
        "goal": "กันงานหลุดเป้า",
        "deliverables": ["ด่าน"],
        "branch": "task/scg",
        "base_sha": base_sha_override or base_sha,
        "allowed_paths": [".project/active-task.json", "src/**", "tests/**"],
        "forbidden_paths": ["src/secret/**"],
        "work_types": ["code", "test", "release"],
        "owner_scope_token": "อนุมัติสเปค SCG-GOAL-DRIFT 7189f34f",
        "status": status,
        "primary_issues": ["SCG-P6-I1"],
        "support_issues": [],
        "next_prompt": "AUTO_CONTINUE",
        "frozen_at": "2026-07-19T10:00:00Z" if status == "frozen" else None,
        "merge_sha": "b" * 40 if status == "frozen" else None,
    }
    value["goal_hash"] = module.goal_hash(value)
    (root / ".project/active-task.json").write_text(
        json.dumps(value, ensure_ascii=False), encoding="utf-8"
    )
    return root


def run_hook(root: Path, file_path: str, work_type: str = "code"):
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(
            {
                "cwd": str(root),
                "tool_name": "Write",
                "tool_input": {"file_path": str(root / file_path)},
                "work_type": work_type,
                "branch": "task/scg",
            },
            ensure_ascii=False,
        ),
        text=True,
        capture_output=True,
    )


def run_shell_hook(root: Path, command: str):
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(
            {
                "cwd": str(root),
                "tool_name": "Bash",
                "tool_input": {"command": command},
                "work_type": "release",
                "branch": "task/scg",
            },
            ensure_ascii=False,
        ),
        text=True,
        capture_output=True,
    )


def test_hook_blocks_path_outside_active_task(tmp_path):
    result = run_hook(make_repo(tmp_path), "README.md")
    assert result.returncode == 2
    assert "GOAL_PATH_OUTSIDE_SCOPE" in result.stderr


def test_hook_allows_path_in_active_task(tmp_path):
    result = run_hook(make_repo(tmp_path), "src/app.py")
    assert result.returncode == 0, result.stderr


def test_hook_blocks_direct_contract_edits_after_creation(tmp_path):
    root = make_repo(tmp_path)
    result = run_hook(root, ".project/active-task.json", "docs")
    assert result.returncode == 2
    assert "GOAL_CONTRACT_DIRECT_WRITE_BLOCKED" in result.stderr


def test_hook_blocks_write_when_head_is_not_descended_from_contract_base(tmp_path):
    root = make_repo(tmp_path, base_sha_override="b" * 40)
    result = run_hook(root, "src/app.py")
    assert result.returncode == 2
    assert "GOAL_HISTORY_MISMATCH" in result.stderr


def test_hook_rejects_frozen_task(tmp_path):
    result = run_hook(make_repo(tmp_path, status="frozen"), "src/app.py")
    assert result.returncode == 2
    assert "BRANCH_FROZEN" in result.stderr


def test_hook_skips_legacy_project_without_contract(tmp_path):
    root = tmp_path / "legacy"
    root.mkdir()
    result = run_hook(root, "README.md")
    assert result.returncode == 0


def test_pre_commit_and_pre_push_gate_scan_all_changed_paths(tmp_path):
    root = make_repo(tmp_path)
    (root / "src").mkdir()
    (root / "src/app.py").write_text("ok\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", ".project/active-task.json", "src/app.py"],
        cwd=root,
        check=True,
    )
    allowed = run_shell_hook(root, "git commit -m scoped")
    assert allowed.returncode == 0, allowed.stderr
    subprocess.run(["git", "commit", "-q", "-m", "scoped"], cwd=root, check=True)

    allowed_push = run_shell_hook(root, "git push origin task/scg")
    assert allowed_push.returncode == 0, allowed_push.stderr

    (root / "README.md").write_text("outside\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "outside"], cwd=root, check=True)
    blocked = run_shell_hook(root, "git push origin task/scg")
    assert blocked.returncode == 2
    assert "GOAL_PATH_OUTSIDE_SCOPE" in blocked.stderr
    assert "README.md" in blocked.stderr
