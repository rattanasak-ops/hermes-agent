from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SPEC_TOOL = ROOT / "scripts/spec-interview/spec_interview.py"
GATE_PATH = ROOT / "scripts/new-chat/hermes_prewrite_gate.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("hermes_prewrite_gate", GATE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "task/nat/spec"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("base\n", encoding="utf-8")
    (path / ".project/spec").mkdir(parents=True)
    (path / ".project/spec/SPEC.md").write_text("status: draft\n\n# SPEC\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=path, check=True, capture_output=True)
    return path.resolve()


def set_plan(repo: Path, plan_id: str = "SPEC") -> Path:
    plan = repo / ".project/plan.md"
    plan.write_text(f"> plan_id: {plan_id}\n\n# Plan\n", encoding="utf-8")
    spec = repo / ".project/spec" / f"{plan_id}.md"
    spec.write_text("status: draft\n\n# SPEC\n", encoding="utf-8")
    return spec


def run_tool(repo: Path, home: Path, *args: str, input_payload: dict | None = None) -> subprocess.CompletedProcess:
    env = {"HOME": str(home), "HERMES_HOME": str(home / ".hermes")}
    return subprocess.run(
        [sys.executable, str(SPEC_TOOL), *args],
        input=json.dumps(input_payload, ensure_ascii=False) if input_payload is not None else None,
        text=True,
        capture_output=True,
        env=env,
        cwd=repo,
        check=False,
    )


def parse(proc: subprocess.CompletedProcess) -> dict:
    assert proc.stdout, proc.stderr
    return json.loads(proc.stdout)


def test_question_record_creates_hash_chain_outside_repo(tmp_path):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    proc = run_tool(
        repo,
        home,
        "record-question",
        "--repo",
        str(repo),
        "--plan-id",
        "SPEC",
        "--question",
        "เป้าหมายคืออะไร",
    )
    data = parse(proc)
    assert proc.returncode == 0, proc.stderr
    assert data["ok"] is True
    assert str(home / ".hermes/spec-evidence") in data["path"]
    assert not (repo / ".hermes").exists()


def test_owner_answer_requires_hook_payload(tmp_path):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    proc = run_tool(
        repo,
        home,
        "record-answer",
        "--repo",
        str(repo),
        "--plan-id",
        "SPEC",
        "--from-hook",
    )
    assert proc.returncode == 2
    assert parse(proc)["ok"] is False


def test_owner_answer_from_hook_extends_chain_and_verify_passes(tmp_path):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    first = run_tool(
        repo,
        home,
        "record-question",
        "--repo",
        str(repo),
        "--plan-id",
        "SPEC",
        "--question",
        "นิยามผ่านคืออะไร",
    )
    assert first.returncode == 0, first.stderr
    second = run_tool(
        repo,
        home,
        "record-answer",
        "--repo",
        str(repo),
        "--plan-id",
        "SPEC",
        "--from-hook",
        input_payload={"user_message": "ผ่านเมื่อ pytest เขียวและ hook block เคสปลอม"},
    )
    assert second.returncode == 0, second.stderr
    verify = run_tool(repo, home, "verify", "--repo", str(repo), "--plan-id", "SPEC")
    data = parse(verify)
    assert verify.returncode == 0, verify.stderr
    assert data["ok"] is True
    assert data["chain_count"] == 2


def test_tampering_breaks_hash_chain(tmp_path):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    proc = run_tool(
        repo,
        home,
        "record-answer",
        "--repo",
        str(repo),
        "--plan-id",
        "SPEC",
        "--from-hook",
        input_payload={"user_message": "คำตอบจริง"},
    )
    data = parse(proc)
    path = Path(data["path"])
    record = json.loads(path.read_text(encoding="utf-8"))
    record["text"] = "คำตอบปลอม"
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    verify = run_tool(repo, home, "verify", "--repo", str(repo), "--plan-id", "SPEC")
    assert verify.returncode == 2
    assert parse(verify)["ok"] is False


def test_manifest_changes_when_spec_changes(tmp_path):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    spec_path = repo / ".project/spec/SPEC.md"
    first = run_tool(repo, home, "manifest", "--repo", str(repo), "--plan-id", "SPEC", "--spec", str(spec_path))
    spec_path.write_text("status: draft\n\n# SPEC\nchanged\n", encoding="utf-8")
    second = run_tool(repo, home, "manifest", "--repo", str(repo), "--plan-id", "SPEC", "--spec", str(spec_path))
    assert parse(first)["manifest_hash"] != parse(second)["manifest_hash"]


def test_prewrite_gate_blocks_ai_from_recording_owner_answer(tmp_path):
    repo = make_repo(tmp_path / "repo")
    gate = load_gate()
    payload = {
        "tool_name": "Bash",
        "cwd": str(repo),
        "tool_input": {
            "command": f"spec-interview record-answer --repo {repo} --plan-id SPEC --from-hook"
        },
    }
    assert gate.run(payload) == 2


def test_prewrite_gate_allows_read_only_spec_verify(tmp_path):
    repo = make_repo(tmp_path / "repo")
    gate = load_gate()
    payload = {
        "tool_name": "Bash",
        "cwd": str(repo),
        "tool_input": {"command": f"spec-interview verify --repo {repo} --plan-id SPEC"},
    }
    assert gate.run(payload) == 0


def test_spec_draft_blocks_runtime_write_but_allows_spec_edit(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(home / ".hermes"))
    set_plan(repo)
    gate = load_gate()

    blocked = {
        "tool_name": "Write",
        "cwd": str(repo),
        "tool_input": {"file_path": "src/app.py"},
    }
    allowed = {
        "tool_name": "Write",
        "cwd": str(repo),
        "tool_input": {"file_path": ".project/spec/SPEC.md"},
    }

    assert gate.run(blocked) == 2
    assert gate.run(allowed) == 0


def test_approved_spec_allows_runtime_write(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(home / ".hermes"))
    spec_path = set_plan(repo)
    approval = run_tool(
        repo,
        home,
        "approve",
        "--repo",
        str(repo),
        "--plan-id",
        "SPEC",
        "--spec",
        str(spec_path),
        "--from-hook",
        input_payload={"user_message": "อนุมัติสเปคนี้"},
    )
    assert approval.returncode == 0, approval.stderr
    gate = load_gate()
    payload = {
        "tool_name": "Write",
        "cwd": str(repo),
        "tool_input": {"file_path": "src/app.py"},
    }
    assert gate.run(payload) == 0


def test_spec_change_after_approval_blocks_runtime_write(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(home / ".hermes"))
    spec_path = set_plan(repo)
    approval = run_tool(
        repo,
        home,
        "approve",
        "--repo",
        str(repo),
        "--plan-id",
        "SPEC",
        "--spec",
        str(spec_path),
        "--from-hook",
        input_payload={"user_message": "อนุมัติสเปคนี้"},
    )
    assert approval.returncode == 0, approval.stderr
    spec_path.write_text("status: draft\n\n# SPEC\nchanged after approve\n", encoding="utf-8")
    gate = load_gate()
    payload = {
        "tool_name": "Write",
        "cwd": str(repo),
        "tool_input": {"file_path": "src/app.py"},
    }
    assert gate.run(payload) == 2


def test_ai_direct_write_to_spec_evidence_is_blocked(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(home / ".hermes"))
    gate = load_gate()
    payload = {
        "tool_name": "Write",
        "cwd": str(repo),
        "tool_input": {"file_path": str(home / ".hermes/spec-evidence/fake.json")},
    }
    assert gate.run(payload) == 2


def test_reused_approval_from_other_plan_does_not_unlock_write(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(home / ".hermes"))
    spec_path = set_plan(repo, "SPEC")
    approval = run_tool(
        repo,
        home,
        "approve",
        "--repo",
        str(repo),
        "--plan-id",
        "SPEC",
        "--spec",
        str(spec_path),
        "--from-hook",
        input_payload={"user_message": "อนุมัติสเปคเก่า"},
    )
    assert approval.returncode == 0, approval.stderr
    set_plan(repo, "OTHER")
    gate = load_gate()
    payload = {
        "tool_name": "Write",
        "cwd": str(repo),
        "tool_input": {"file_path": "src/app.py"},
    }
    assert gate.run(payload) == 2


def test_spec_symlink_write_escape_is_blocked(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "repo")
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    (repo / ".project/spec/link.md").symlink_to(outside)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(home / ".hermes"))
    gate = load_gate()
    payload = {
        "tool_name": "Write",
        "cwd": str(repo),
        "tool_input": {"file_path": ".project/spec/link.md"},
    }
    assert gate.run(payload) == 2


def test_hidden_code_in_markdown_is_blocked_before_spec_approval(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(home / ".hermes"))
    set_plan(repo)
    gate = load_gate()
    payload = {
        "tool_name": "Write",
        "cwd": str(repo),
        "tool_input": {"file_path": "docs/runbook.md", "content": "```python\nprint('runs')\n```"},
    }
    assert gate.run(payload) == 2


def test_missing_spec_tool_fails_closed_for_runtime_write(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(home / ".hermes"))
    set_plan(repo)
    gate = load_gate()
    monkeypatch.setattr(gate, "SPEC_INTERVIEW_TOOL", tmp_path / "missing.py")
    payload = {
        "tool_name": "Write",
        "cwd": str(repo),
        "tool_input": {"file_path": "src/app.py"},
    }
    assert gate.run(payload) == 2


def test_waiver_can_be_consumed_once_with_lock(tmp_path):
    repo = make_repo(tmp_path / "repo")
    home = tmp_path / "home"
    digest = hashlib.sha256(b"one small docs typo").hexdigest()
    create = run_tool(
        repo,
        home,
        "waive",
        "--repo",
        str(repo),
        "--plan-id",
        "SPEC",
        "--diff-hash",
        digest,
        "--from-hook",
        input_payload={"user_message": "อนุญาตข้ามเฉพาะ typo นี้"},
    )
    assert create.returncode == 0, create.stderr
    first = run_tool(repo, home, "consume-waiver", "--repo", str(repo), "--plan-id", "SPEC", "--diff-hash", digest)
    second = run_tool(repo, home, "consume-waiver", "--repo", str(repo), "--plan-id", "SPEC", "--diff-hash", digest)
    assert first.returncode == 0, first.stderr
    assert second.returncode == 2
