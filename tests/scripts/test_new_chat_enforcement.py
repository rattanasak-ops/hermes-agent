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


@pytest.mark.parametrize(
    "command",
    [
        "sort -o src/app.py /etc/hosts",
        "sort -osrc/app.py /etc/hosts",
        "sort --output=src/app.py /etc/hosts",
        "curl --output=src/app.py https://example.com",
        "curl -osrc/app.py https://example.com",
        "curl -OJ https://example.com/file",
        "find . -fprint0 src/app.py",
        "diff --output=src/app.py a b",
        "ruff check --fix .",
        "ruff check --fix-only .",
        "ruff check --add-noqa .",
        "ruff check --unsafe-fixes .",
        "tsc --build",
        "gh pr merge 1",
    ],
)
def test_read_only_allowlist_blocks_write_or_mutating_flags(workspace, command):
    assert GATE.run(payload(workspace, "Bash", {"command": command})) == 2


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
        "hermes-new-chat open --project hermes-agent --staff-id nat --task-id T --slug t --repo /tmp --approval ok",
        "hermes-worktree open --project-id hermes-agent --staff-id nat --task-id T --slug t --repo /tmp --apply",
        "hermes worktree open --project-id hermes-agent --staff-id nat --task-id T --slug t --repo /tmp --apply",
        "hermes-worktree close --task-id T --merged --merge-sha abc123 --json",
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


@pytest.mark.parametrize(
    "command",
    [
        "hermes-new-chat open --project demo --task-id DEMO-1 --title demo --staff-id nat",
        "hermes-worktree open --project demo --task-id DEMO-1",
        "hermes worktree open --project demo --task-id DEMO-1",
        "hermes worktree enter --task-id DEMO-1",
    ],
)
def test_shortcut_cannot_create_or_enter_worktree_through_manager_commands(workspace, command):
    assert GATE.run(payload(workspace, "Bash", {"command": command})) == 2


@pytest.mark.parametrize(
    "command",
    [
        "git -C . worktree add /tmp/hidden -b task/nat/hidden",
        "git --git-dir=.git worktree add /tmp/hidden -b task/nat/hidden",
        "env git worktree add /tmp/hidden -b task/nat/hidden",
        "env HERMES_TEST=1 hermes-new-chat open --task-id HIDDEN",
        "bash -lc 'git worktree add /tmp/hidden -b task/nat/hidden'",
        "zsh -c 'hermes-new-chat open --task-id HIDDEN'",
    ],
)
def test_worktree_mutation_cannot_hide_behind_wrappers(workspace, command):
    assert GATE.run(payload(workspace, "Bash", {"command": command})) == 2


@pytest.mark.parametrize(
    "command",
    [
        "git switch -c badword_tracking",
        "git checkout -b badword_tracking",
        "git branch badword_tracking",
    ],
)
def test_owner_explicit_named_branch_request_is_allowed(workspace, command):
    data = payload(workspace, "Bash", {"command": command})
    data["user_prompt"] = "สร้าง new branch = badword_tracking"
    assert GATE.run(data) == 0


def test_owner_branch_request_can_be_read_from_transcript(workspace, tmp_path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "สร้าง branch ชื่อ feature/owner-approved"}],
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    data = payload(
        workspace,
        "Bash",
        {"command": "git switch -c feature/owner-approved"},
    )
    data["transcript_path"] = str(transcript)
    assert GATE.run(data) == 0


def test_owner_prompt_hook_grants_short_lived_branch_intent(workspace):
    recorder = ROOT / "scripts/new-chat/hermes_owner_intent.py"
    proc = subprocess.run(
        ["python3", str(recorder)],
        input=json.dumps(
            {
                "cwd": str(workspace["repo"]),
                "user_message": "สร้าง new branch = feature/from-owner-hook",
            },
            ensure_ascii=False,
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = payload(
        workspace,
        "Bash",
        {"command": "git switch -c feature/from-owner-hook"},
    )
    assert GATE.run(data) == 0


def test_pasted_example_prompt_hook_does_not_grant_branch_intent(workspace):
    recorder = ROOT / "scripts/new-chat/hermes_owner_intent.py"
    proc = subprocess.run(
        ["python3", str(recorder)],
        input=json.dumps(
            {
                "cwd": str(workspace["repo"]),
                "user_message": "นี่คือตัวอย่างจากแชทเก่า: สร้าง new branch = badword_tracking",
            },
            ensure_ascii=False,
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = payload(workspace, "Bash", {"command": "git switch -c badword_tracking"})
    assert GATE.run(data) == 2


def test_ai_cannot_invoke_owner_intent_recorder(workspace):
    command = "hermes-owner-intent"
    assert GATE.run(payload(workspace, "Bash", {"command": command})) == 2


def test_branch_name_must_match_owner_request(workspace):
    data = payload(
        workspace,
        "Bash",
        {"command": "git switch -c feature/ai-invented"},
    )
    data["user_prompt"] = "สร้าง branch ชื่อ feature/owner-approved"
    assert GATE.run(data) == 2


def test_long_pasted_example_is_not_branch_approval(workspace):
    data = payload(
        workspace,
        "Bash",
        {"command": "git switch -c badword_tracking"},
    )
    data["user_prompt"] = (
        "ช่วยตรวจปัญหา Shortcut ทุกตัวว่าทำไม AI สร้าง Worktree มั่ว "
        "นี่คือตัวอย่างจากแชทเก่า: สร้าง new branch = badword_tracking "
        "แต่รอบนี้ให้ตรวจและแก้ระบบกลางเท่านั้น " + ("รายละเอียด " * 40)
    )
    assert GATE.run(data) == 2


def test_owner_cannot_authorize_protected_branch_name(workspace):
    data = payload(workspace, "Bash", {"command": "git switch -c main"})
    data["user_prompt"] = "สร้าง new branch = main"
    assert GATE.run(data) == 2


def test_git_worktree_list_is_read_only_and_allowed(workspace):
    assert GATE.run(payload(workspace, "Bash", {"command": "git worktree list --porcelain"})) == 0


def test_read_only_hermes_workspace_status_commands_are_allowed(workspace):
    assert GATE.run(payload(workspace, "Bash", {"command": "hermes-new-chat status --task-id T"})) == 0
    assert GATE.run(payload(workspace, "Bash", {"command": "hermes-worktree status --task-id T --json"})) == 0


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
