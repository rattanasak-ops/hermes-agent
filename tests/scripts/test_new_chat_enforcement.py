from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

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
        "python3 design-system-standard-v2/tools/ds-gate.py --layer all",
        "bash design-system-standard-v2/ds-adopt.sh check .",
        "ruff check .",
        "tsc --noEmit",
    ],
)
def test_normal_development_commands_pass(workspace, command):
    assert GATE.run(payload(workspace, "Bash", {"command": command})) == 0


@pytest.mark.parametrize("branch", ["main", "master", "develop", "development", "production", "prod"])
def test_shared_or_production_branches_block_writes(tmp_path, monkeypatch, capsys, branch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo = make_repo(tmp_path / f"repo-{branch}", branch=branch)
    data = {"repo": repo}
    assert GATE.run(payload(data, "Write", {"file_path": "src/a.py"}, cwd=repo)) == 2
    message = capsys.readouterr().err
    assert "PROTECTED_BRANCH_WRITE_BLOCKED" in message
    assert "hermes-current-workspace-recover" not in message


def test_detached_head_blocks_with_machine_recovery_not_owner_request(workspace, capsys):
    subprocess.run(["git", "checkout", "--detach"], cwd=workspace["repo"], check=True, capture_output=True)
    assert GATE.run(payload(workspace, "Write", {"file_path": "src/a.py"})) == 2
    message = capsys.readouterr().err
    assert "RECOVERY_REQUIRED_REGISTERED_BRANCH" in message
    assert "hermes-current-workspace-recover" in message
    assert "เจ้าของต้อง" not in message
    assert "ให้เจ้าของ" not in message
    assert "เปิดกิ่ง" not in message


def test_registered_detached_workspace_recovers_same_root_and_preserves_dirty_files(workspace):
    repo = workspace["repo"]
    subprocess.run(["git", "checkout", "--detach"], cwd=repo, check=True, capture_output=True)
    dirty_file = repo / "src/in-progress.py"
    dirty_file.parent.mkdir()
    dirty_file.write_text("keep this work\n", encoding="utf-8")
    registry = workspace["home"] / ".hermes/worktrees/registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps(
            {
                "schema_version": "worktree-lifecycle-v1",
                "tasks": {
                    "TEST-1": {
                        "task_id": "TEST-1",
                        "state": "BLOCKED",
                        "branch": "task/nat/TEST-1-recovered",
                        "worktree_path": str(repo),
                        "canonical_repo": str(repo),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    before_count = len(subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("worktree ")) - 1

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/new-chat/hermes_workspace_recover.py"),
            "--cwd",
            str(repo),
            "--json",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["code"] == "RECOVERED_REGISTERED_BRANCH"
    assert subprocess.run(
        ["git", "branch", "--show-current"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip() == "task/nat/TEST-1-recovered"
    assert dirty_file.read_text(encoding="utf-8") == "keep this work\n"
    after_count = len(subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("worktree ")) - 1
    assert after_count == before_count


def test_recovery_refuses_a_different_attached_branch_even_at_same_head(workspace):
    repo = workspace["repo"]
    original_branch = "codex/in-progress"
    subprocess.run(
        ["git", "switch", "-c", original_branch],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    registry = workspace["home"] / ".hermes/worktrees/registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps(
            {
                "tasks": {
                    "TEST-ATTACHED": {
                        "task_id": "TEST-ATTACHED",
                        "state": "ACTIVE",
                        "branch": "task/nat/TEST-ATTACHED-registered",
                        "worktree_path": str(repo),
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/new-chat/hermes_workspace_recover.py"),
            "--cwd",
            str(repo),
            "--json",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    payload_out = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload_out["code"] == "RECOVERY_NOT_DETACHED"
    assert subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == original_branch


def test_recovery_stops_on_diverged_dirty_branch_without_owner_handoff(workspace):
    repo = workspace["repo"]
    branch = "task/nat/TEST-2-existing"
    subprocess.run(["git", "switch", "-c", branch], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("branch moved\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "move branch"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "checkout", "--detach", "HEAD~1"], cwd=repo, check=True, capture_output=True
    )
    dirty_file = repo / "src/in-progress.py"
    dirty_file.parent.mkdir()
    dirty_file.write_text("keep this work\n", encoding="utf-8")
    registry = workspace["home"] / ".hermes/worktrees/registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps(
            {
                "tasks": {
                    "TEST-2": {
                        "task_id": "TEST-2",
                        "state": "ACTIVE",
                        "branch": branch,
                        "worktree_path": str(repo),
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/new-chat/hermes_workspace_recover.py"),
            "--cwd",
            str(repo),
            "--json",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    payload_out = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload_out["code"] == "RECOVERY_CONFLICT"
    assert "เจ้าของ" not in payload_out["message"]
    assert "ผู้ใช้" not in payload_out["message"]
    assert subprocess.run(
        ["git", "branch", "--show-current"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip() == ""
    assert dirty_file.read_text(encoding="utf-8") == "keep this work\n"


def test_recovery_stops_on_diverged_clean_branch_to_preserve_detached_commit(workspace):
    repo = workspace["repo"]
    branch = "task/nat/TEST-3-existing"
    subprocess.run(["git", "switch", "-c", branch], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("registered branch moved\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-am", "move branch"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "checkout", "--detach", "HEAD~1"], cwd=repo, check=True, capture_output=True
    )
    detached_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    registry = workspace["home"] / ".hermes/worktrees/registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps(
            {
                "tasks": {
                    "TEST-3": {
                        "task_id": "TEST-3",
                        "state": "ACTIVE",
                        "branch": branch,
                        "worktree_path": str(repo),
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/new-chat/hermes_workspace_recover.py"),
            "--cwd",
            str(repo),
            "--json",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert json.loads(result.stdout)["code"] == "RECOVERY_CONFLICT"
    assert subprocess.run(
        ["git", "branch", "--show-current"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip() == ""
    assert subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip() == detached_head


def test_recovery_command_is_allowed_by_shell_gate_while_detached(workspace):
    subprocess.run(["git", "checkout", "--detach"], cwd=workspace["repo"], check=True, capture_output=True)

    assert GATE.run(payload(
        workspace,
        "Bash",
        {"command": f"hermes-current-workspace-recover --cwd {workspace['repo']} --json"},
    )) == 0


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
        "git -C . status --short",
        "git -C. log --oneline -3",
        "git --no-pager -C . diff --stat",
        "git -C . -C .. status --short",
    ],
)
def test_git_c_allows_read_only_subcommands(workspace, command):
    assert GATE.run(payload(workspace, "Bash", {"command": command})) == 0


@pytest.mark.parametrize(
    "command",
    [
        "git -C . checkout -- README.md",
        "git -C . reset --hard HEAD",
        "git -C . clean -fd",
        "git -C . stash push",
        "git -C . worktree add /tmp/hidden -b task/nat/hidden",
        "git --no-pager -C . checkout -- README.md",
        "git -C . -C .. reset --hard HEAD",
        "git -C . push --force origin main",
        "git -C . -c alias.erase=reset erase --hard HEAD",
        "git -C",
    ],
)
def test_git_c_cannot_hide_dangerous_subcommands(workspace, command):
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
