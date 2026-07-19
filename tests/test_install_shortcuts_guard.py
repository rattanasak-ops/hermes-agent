import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="bash installer test")


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "team-shortcuts" / "install-shortcuts.sh"


def build_fake_installer(
    tmp_path: Path,
    registry: str = "registry v1\n",
    ref: str = "ref v1\n",
    mw_setup_exit: int = 0,
    hook_doctor_script: str = "#!/usr/bin/env python3\nraise SystemExit(0)\n",
):
    team_dir = tmp_path / "team-shortcuts"
    scripts_dir = tmp_path / "scripts"
    mw_dir = scripts_dir / "mw"
    payload = team_dir / "payload"
    registry_path = payload / "ai-context" / "prompt-shortcut-registry.md"
    ref_path = payload / "skills" / "prompt-shortcuts" / "references" / "a.md"
    agent_skill = payload / "skills" / "agent-center" / "SKILL.md"
    agent_metadata = payload / "skills" / "agent-center" / "agents" / "openai.yaml"
    agent_plugin = tmp_path / "plugins" / "agent_center" / "plugin.yaml"

    team_dir.mkdir()
    mw_dir.mkdir(parents=True)
    shutil.copy2(SCRIPT, team_dir / "install-shortcuts.sh")
    (team_dir / "install-new-chat-tools.sh").write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "mkdir -p \"$HOME/.local/bin\"\n"
        "for name in hermes-new-chat hermes-worktree; do\n"
        "  printf '#!/usr/bin/env bash\\nexit 0\\n' > \"$HOME/.local/bin/$name\"\n"
        "  chmod 0755 \"$HOME/.local/bin/$name\"\n"
        "done\n"
        "printf '#!/usr/bin/env bash\\nexit 2\\n' > \"$HOME/.local/bin/hermes-prewrite-gate\"\n"
        "chmod 0755 \"$HOME/.local/bin/hermes-prewrite-gate\"\n"
    )
    (team_dir / "VERSION").write_text("test-version\n")
    (team_dir / "install-team-hooks.py").write_text("#!/usr/bin/env python3\n")
    (scripts_dir / "hermes_write_permit.py").write_text("#!/usr/bin/env bash\nexit 0\n")
    (scripts_dir / "hermes_hook_doctor.py").write_text(hook_doctor_script)
    save_git = tmp_path / "skills/devops/save-git/scripts/save_git_gate.py"
    save_git.parent.mkdir(parents=True)
    save_git.write_text("#!/usr/bin/env python3\nraise SystemExit(0)\n")
    gate = scripts_dir / "new-chat/hermes_prewrite_gate.py"
    gate.parent.mkdir(parents=True)
    gate.write_text("#!/usr/bin/env python3\nraise SystemExit(2)\n")
    (gate.parent / "hermes_owner_intent.py").write_text(
        "#!/usr/bin/env python3\nraise SystemExit(0)\n"
    )
    (gate.parent / "hermes_workspace_recover.py").write_text(
        "#!/usr/bin/env python3\nraise SystemExit(0)\n"
    )
    lifecycle = tmp_path / "hermes_cli/worktree_lifecycle.py"
    lifecycle.parent.mkdir(parents=True)
    lifecycle.write_text("def register_worktree_subparser(subparsers):\n    pass\n")
    (mw_dir / "mw-setup.sh").write_text(f"#!/usr/bin/env bash\nexit {mw_setup_exit}\n")
    registry_path.parent.mkdir(parents=True)
    ref_path.parent.mkdir(parents=True)
    agent_skill.parent.mkdir(parents=True)
    agent_metadata.parent.mkdir(parents=True)
    agent_plugin.parent.mkdir(parents=True)
    registry_path.write_text(registry)
    ref_path.write_text(ref)
    agent_skill.write_text("---\nname: agent-center\n---\n")
    agent_metadata.write_text("interface:\n  display_name: Agent Center\n")
    agent_plugin.write_text("name: agent-center\nversion: 0.1.0\n")

    fake_bin = tmp_path / "home" / ".local" / "bin"
    fake_bin.mkdir(parents=True)
    fake_hermes = fake_bin / "hermes"
    fake_hermes.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"${1:-}\" = dump ]; then\n"
        "  printf 'hermes_home:      ~/.hermes-active\\n'\n"
        "elif [ \"${1:-}\" = plugins ] && [ \"${2:-}\" = enable ] "
        "&& [ \"${3:-}\" = agent-center ]; then\n"
        "  test -f \"$HOME/.hermes-active/plugins/agent-center/plugin.yaml\" || exit 3\n"
        "  test -f \"$HOME/.hermes-active/skills/agent-center/SKILL.md\" || exit 5\n"
        "  mkdir -p \"$HOME/.hermes-active\"\n"
        "  printf 'plugins:\\n  enabled:\\n    - agent-center\\n' "
        "> \"$HOME/.hermes-active/config.yaml\"\n"
        "  printf 'enabled\\n' > \"$HOME/.hermes-active/agent-center-enabled\"\n"
        "else\n"
        "  exit 4\n"
        "fi\n"
    )
    fake_hermes.chmod(0o755)
    return team_dir


def run_installer(team_dir: Path, tmp_path: Path, *args: str):
    env = os.environ.copy()
    env.pop("HERMES_HOME", None)
    env["HOME"] = str(tmp_path / "home")
    env["HERMES_SHORTCUTS_DEST"] = str(tmp_path / "vault")
    env["PATH"] = f"{tmp_path / 'home/.local/bin'}{os.pathsep}{env.get('PATH', '')}"
    hook_doctor = tmp_path / "home/.local/bin/hermes-hook-doctor"
    if hook_doctor.is_symlink() or hook_doctor.exists():
        hook_doctor.unlink()
    return subprocess.run(
        ["bash", str(team_dir / "install-shortcuts.sh"), *args],
        cwd=team_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def vault_file(tmp_path: Path, relative: str) -> Path:
    return tmp_path / "vault" / relative


def backup_dirs(tmp_path: Path):
    return sorted((tmp_path / "vault").glob(".backup-shortcuts-*"))


def test_fresh_install_copies_payload_to_destination(tmp_path: Path):
    team_dir = build_fake_installer(tmp_path)

    result = run_installer(team_dir, tmp_path)

    assert result.returncode == 0, result.stderr + result.stdout
    assert vault_file(tmp_path, "ai-context/prompt-shortcut-registry.md").read_text() == "registry v1\n"
    assert vault_file(tmp_path, "skills/prompt-shortcuts/references/a.md").read_text() == "ref v1\n"
    assert vault_file(tmp_path, "skills/agent-center/SKILL.md").is_file()
    assert (tmp_path / "home/.codex/skills/agent-center/SKILL.md").is_file()
    assert (tmp_path / "home/.hermes-active/skills/agent-center/SKILL.md").is_file()
    assert (tmp_path / "home/.hermes-active/plugins/agent-center/plugin.yaml").is_file()
    assert (tmp_path / "home/.hermes-active/agent-center-enabled").read_text() == "enabled\n"
    local_bin = tmp_path / "home/.local/bin"
    for name in ("hermes-prewrite-gate", "hermes-new-chat", "hermes-worktree", "save-git"):
        assert (local_bin / name).is_file()
    gate = subprocess.run(
        [str(local_bin / "hermes-prewrite-gate")],
        input="{not-json",
        env={**os.environ, "HOME": str(tmp_path / "home")},
        text=True,
        capture_output=True,
        check=False,
    )
    assert gate.returncode == 2


def test_existing_codex_agent_directory_requires_force_before_stale_delete(tmp_path: Path):
    team_dir = build_fake_installer(tmp_path)
    codex_agent = tmp_path / "home/.codex/skills/agent-center"
    codex_agent.mkdir(parents=True)
    (codex_agent / "stale.txt").write_text("remove me\n")

    blocked = run_installer(team_dir, tmp_path)

    assert blocked.returncode == 2, blocked.stderr + blocked.stdout
    assert (codex_agent / "stale.txt").exists()
    assert "stale.txt (มีเฉพาะปลายทาง)" in blocked.stdout

    result = run_installer(team_dir, tmp_path, "--force")

    assert result.returncode == 0, result.stderr + result.stdout
    assert (codex_agent / "SKILL.md").is_file()
    assert not (codex_agent / "stale.txt").exists()


def test_newer_different_destination_blocks_without_force(tmp_path: Path):
    team_dir = build_fake_installer(tmp_path)
    assert run_installer(team_dir, tmp_path).returncode == 0

    dest = vault_file(tmp_path, "skills/prompt-shortcuts/references/a.md")
    dest.write_text("owner newer work\n")
    future = time.time() + 60
    os.utime(dest, (future, future))

    result = run_installer(team_dir, tmp_path)

    assert result.returncode == 2
    assert dest.read_text() == "owner newer work\n"
    assert "ไฟล์ปลายทางใหม่กว่าชุดติดตั้ง" in result.stdout
    assert "skills/prompt-shortcuts/references/a.md" in result.stdout


def test_force_overwrites_newer_destination_and_creates_backup(tmp_path: Path):
    team_dir = build_fake_installer(tmp_path)

    dest = vault_file(tmp_path, "skills/prompt-shortcuts/references/a.md")
    dest.parent.mkdir(parents=True)
    dest.write_text("owner newer work\n")
    future = time.time() + 60
    os.utime(dest, (future, future))

    result = run_installer(team_dir, tmp_path, "--force")

    assert result.returncode == 0, result.stderr + result.stdout
    assert dest.read_text() == "ref v1\n"
    backups = backup_dirs(tmp_path)
    assert len(backups) == 1
    assert (backups[0] / "skills/prompt-shortcuts/references/a.md").read_text() == "owner newer work\n"


def test_newer_codex_agent_skill_blocks_and_force_backs_it_up(tmp_path: Path):
    team_dir = build_fake_installer(tmp_path)

    codex_link = tmp_path / "home/.codex/skills/agent-center"
    codex_link.mkdir(parents=True)
    codex_skill = codex_link / "SKILL.md"
    codex_skill.write_text("owner newer Codex skill\n")
    future = time.time() + 60
    os.utime(codex_skill, (future, future))

    blocked = run_installer(team_dir, tmp_path)
    assert blocked.returncode == 2
    assert codex_skill.read_text() == "owner newer Codex skill\n"
    assert "Codex skill/agent-center/SKILL.md" in blocked.stdout

    forced = run_installer(team_dir, tmp_path, "--force")
    assert forced.returncode == 0, forced.stderr + forced.stdout
    assert codex_skill.read_text() == "---\nname: agent-center\n---\n"
    assert any(
        (backup / "codex-skills/agent-center/SKILL.md").is_file()
        and (backup / "codex-skills/agent-center/SKILL.md").read_text()
        == "owner newer Codex skill\n"
        for backup in backup_dirs(tmp_path)
    )


def test_destination_only_codex_file_requires_force_before_delete(tmp_path: Path):
    team_dir = build_fake_installer(tmp_path)

    codex_link = tmp_path / "home/.codex/skills/agent-center"
    codex_link.mkdir(parents=True)
    owner_note = codex_link / "owner-local-note.md"
    owner_note.write_text("keep my local note\n")

    blocked = run_installer(team_dir, tmp_path)
    assert blocked.returncode == 2
    assert owner_note.read_text() == "keep my local note\n"
    assert "owner-local-note.md (มีเฉพาะปลายทาง)" in blocked.stdout

    forced = run_installer(team_dir, tmp_path, "--force")
    assert forced.returncode == 0, forced.stderr + forced.stdout
    assert not owner_note.exists()
    assert any(
        (backup / "codex-skills/agent-center/owner-local-note.md").is_file()
        for backup in backup_dirs(tmp_path)
    )


@pytest.mark.parametrize("broken", [False, True])
def test_destination_only_codex_symlink_blocks_without_force(tmp_path: Path, broken: bool):
    team_dir = build_fake_installer(tmp_path)
    codex_link = tmp_path / "home/.codex/skills/agent-center"
    codex_link.mkdir(parents=True)
    owner_target = tmp_path / "owner-note.md"
    if not broken:
        owner_target.write_text("owner note\n")
    owner_link = codex_link / "owner-link.md"
    owner_link.symlink_to(owner_target)

    blocked = run_installer(team_dir, tmp_path)

    assert blocked.returncode == 2
    assert owner_link.is_symlink()
    assert "owner-link.md (มีเฉพาะปลายทาง)" in blocked.stdout


def test_rerun_unchanged_payload_does_not_create_second_backup(tmp_path: Path):
    team_dir = build_fake_installer(tmp_path)

    dest = vault_file(tmp_path, "skills/prompt-shortcuts/references/a.md")
    dest.parent.mkdir(parents=True)
    dest.write_text("changed but older\n")
    past = time.time() - 60
    os.utime(dest, (past, past))
    assert run_installer(team_dir, tmp_path).returncode == 0
    assert len(backup_dirs(tmp_path)) == 1

    result = run_installer(team_dir, tmp_path)

    assert result.returncode == 0, result.stderr + result.stdout
    assert len(backup_dirs(tmp_path)) == 1


def test_missing_mw_setup_fails_installation(tmp_path: Path):
    team_dir = build_fake_installer(tmp_path)
    (tmp_path / "scripts/mw/mw-setup.sh").unlink()

    result = run_installer(team_dir, tmp_path)

    assert result.returncode != 0
    assert "ไม่พบตัวติดตั้งเครื่องมือ Use Migrate Web" in result.stdout


def test_failed_mw_setup_fails_installation(tmp_path: Path):
    team_dir = build_fake_installer(tmp_path, mw_setup_exit=23)

    result = run_installer(team_dir, tmp_path)

    assert result.returncode != 0
    assert "ติดตั้งเครื่องมือ Use Migrate Web (MW) ไม่สำเร็จ" in result.stdout


def test_installer_retries_hook_doctor_once(tmp_path: Path):
    marker = tmp_path / "hook-doctor-attempted"
    doctor = (
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        f"marker = Path({str(marker)!r})\n"
        "if not marker.exists():\n"
        "    marker.write_text('first', encoding='utf-8')\n"
        "    raise SystemExit(137)\n"
        "raise SystemExit(0)\n"
    )
    team_dir = build_fake_installer(tmp_path, hook_doctor_script=doctor)

    result = run_installer(team_dir, tmp_path)

    assert result.returncode == 0, result.stderr + result.stdout
    assert "ลองตรวจ Hook ซ้ำอีก 1 ครั้ง" in result.stdout


def test_save_git_scope_uses_merged_head_and_effective_target_diff(tmp_path: Path, monkeypatch):
    gate_path = ROOT / "skills/devops/save-git/scripts/save_git_gate.py"
    spec = importlib.util.spec_from_file_location("repo_save_git_gate", gate_path)
    assert spec and spec.loader
    gate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gate
    spec.loader.exec_module(gate)

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-b", "feature/test")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test User")
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "base")
    base = git("rev-parse", "HEAD")
    (tmp_path / "old.txt").write_text("already merged\n", encoding="utf-8")
    git("add", "old.txt")
    git("commit", "-m", "old feature")
    merged_head = git("rev-parse", "HEAD")

    git("switch", "-c", "main", base)
    (tmp_path / "old.txt").write_text("already merged\n", encoding="utf-8")
    git("add", "old.txt")
    git("commit", "-m", "squash old feature")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("switch", "feature/test")
    (tmp_path / "new.txt").write_text("new work\n", encoding="utf-8")
    git("add", "new.txt")
    git("commit", "-m", "new feature")
    git("merge", "--no-edit", "main")

    monkeypatch.setattr(
        gate,
        "merged_head_checkpoint",
        lambda root, branch, target: (merged_head, "github"),
    )

    assert gate.effective_scope(tmp_path, "origin/main", "feature/test", "main") == (
        1,
        1,
        "github",
    )
