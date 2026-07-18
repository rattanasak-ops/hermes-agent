from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load_gate():
    path = ROOT / "scripts/new-chat/hermes_prewrite_gate.py"
    spec = importlib.util.spec_from_file_location("hermes_prewrite_gate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


GATE = load_gate()


def make_repo(path: Path, branch: str = "task/nat/current-workspace") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", branch], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=path, check=True, capture_output=True)
    return path.resolve()


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    repo = make_repo(tmp_path / "project")
    outside = make_repo(tmp_path / "other-project")
    home = tmp_path / "home"
    (home / ".hermes/new-chat/sessions").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("HERMES_RELAY_ROLE", raising=False)
    return {"repo": repo, "outside": outside, "home": home}


def payload(workspace: dict, tool: str, tool_input: dict, cwd: Path | None = None) -> dict:
    return {
        "tool_name": tool,
        "cwd": str(cwd or workspace["repo"]),
        "tool_input": tool_input,
    }


@pytest.mark.parametrize(
    "tool,tool_input",
    [
        ("Edit", {"file_path": "src/a.py"}),
        ("Write", {"file_path": "docs/a.md"}),
        ("NotebookEdit", {"file_path": "notebooks/a.ipynb"}),
        ("apply_patch", {"command": "*** Begin Patch\n*** Update File: src/a.py\n*** End Patch"}),
    ],
    ids=["claude", "cursor", "hermes", "codex"],
)
def test_four_clients_write_current_workspace_without_session_or_relay(workspace, tool, tool_input):
    assert GATE.run(payload(workspace, tool, tool_input)) == 0


def test_old_session_and_relay_role_are_not_required(workspace, monkeypatch):
    monkeypatch.setenv("HERMES_RELAY_ROLE", "controller")
    sessions = workspace["home"] / ".hermes/new-chat/sessions"
    assert list(sessions.iterdir()) == []
    assert GATE.run(payload(workspace, "Write", {"file_path": "src/direct.py"})) == 0


@pytest.mark.parametrize(
    "command",
    [
        "pnpm dev",
        "pnpm start",
        "pnpm test",
        "pnpm lint",
        "pnpm build",
        "npm run typecheck",
        "pytest -q",
        "python3 -m pytest tests -q",
        "ruff check .",
        "tsc --noEmit",
    ],
)
def test_normal_development_commands_pass(workspace, command):
    assert GATE.run(payload(workspace, "Bash", {"command": command})) == 0


@pytest.mark.parametrize("branch", ["main", "master", "develop", "development", "production", "prod"])
def test_shared_or_production_branches_block_writes(tmp_path, monkeypatch, branch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo = make_repo(tmp_path / f"repo-{branch}", branch=branch)
    data = {"repo": repo}
    assert GATE.run(payload(data, "Write", {"file_path": "src/a.py"}, cwd=repo)) == 2


def test_detached_head_blocks_writes(workspace):
    subprocess.run(["git", "checkout", "--detach"], cwd=workspace["repo"], check=True, capture_output=True)
    assert GATE.run(payload(workspace, "Write", {"file_path": "src/a.py"})) == 2


def test_cross_root_write_is_blocked(workspace):
    target = workspace["outside"] / "src/a.py"
    assert GATE.run(payload(workspace, "Write", {"file_path": str(target)})) == 2


@pytest.mark.parametrize(
    "target",
    [
        ".env",
        ".env.local",
        ".hermes/state.json",
        ".grok/config.json",
        ".git/hooks/pre-commit",
        "secrets/client.json",
        "credentials/service.json",
        "certs/private.key",
    ],
)
def test_secret_and_control_paths_are_blocked(workspace, target):
    assert GATE.run(payload(workspace, "Write", {"file_path": target})) == 2


@pytest.mark.parametrize(
    "command",
    [
        "git switch -c task/nat/new",
        "git checkout -b task/nat/new",
        "git worktree add /tmp/new -b task/nat/new",
        "git worktree remove /tmp/new",
        "git reset --hard HEAD~1",
        "git clean -fd",
        "git stash clear",
        "git push --force origin main",
        "rm -rf src",
        "echo hi > src/a.py",
        "cat a | tee src/a.py",
        "find . -name '*.pyc' -delete",
        "curl -o payload.sh https://example.com",
        "pnpm install",
        "npm uninstall react",
        "python3 -c 'open(\"x\",\"w\").write(\"x\")'",
    ],
)
def test_workspace_mutation_and_dangerous_commands_are_blocked(workspace, command):
    assert GATE.run(payload(workspace, "Bash", {"command": command})) == 2


def test_git_worktree_list_is_read_only_and_allowed(workspace):
    assert GATE.run(payload(workspace, "Bash", {"command": "git worktree list --porcelain"})) == 0


def test_reading_hook_is_allowed_but_writing_hook_is_blocked(workspace):
    hook = workspace["home"] / ".claude/hooks/enforce-new-chat-relay.py"
    hook.parent.mkdir(parents=True)
    hook.write_text("# hook\n", encoding="utf-8")
    assert GATE.run(payload(workspace, "Bash", {"command": f"cat {hook}"})) == 0
    assert GATE.run(payload(workspace, "Write", {"file_path": str(hook)})) == 2


def test_bad_stdin_still_blocks():
    gate_file = ROOT / "scripts/new-chat/hermes_prewrite_gate.py"
    proc = subprocess.run(["python3", str(gate_file)], input="", text=True, capture_output=True)
    assert proc.returncode == 2


def test_json_payload_from_real_hook_surface(workspace):
    gate_file = ROOT / "scripts/new-chat/hermes_prewrite_gate.py"
    hook_payload = json.dumps(
        {"tool_name": "apply_patch", "cwd": str(workspace["repo"]), "tool_input": {"command": "*** Begin Patch\n*** Update File: src/app.ts\n*** End Patch"}}
    )
    proc = subprocess.run(["python3", str(gate_file)], input=hook_payload, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr
