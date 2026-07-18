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
    shutil.copy2(ROOT / "team-shortcuts/install-new-chat-tools.sh", team_dir)
    shutil.copytree(ROOT / "team-shortcuts/new-chat-tools", team_dir / "new-chat-tools")
    (team_dir / "VERSION").write_text("test-version\n")
    (team_dir / "install-team-hooks.py").write_text("#!/usr/bin/env python3\n")
    (scripts_dir / "hermes_write_permit.py").write_text("#!/usr/bin/env bash\nexit 0\n")
    (scripts_dir / "hermes_hook_doctor.py").write_text(
        "#!/usr/bin/env python3\nraise SystemExit(0)\n"
    )
    gate = scripts_dir / "new-chat/hermes_prewrite_gate.py"
    gate.parent.mkdir(parents=True)
    gate.write_text("#!/usr/bin/env python3\nraise SystemExit(2)\n")
    (scripts_dir / "new-chat/hermes_owner_intent.py").write_text(
        "#!/usr/bin/env python3\n"
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
    assert (tmp_path / "home/.hermes-active/plugins/agent-center/plugin.yaml").is_file()
    assert (tmp_path / "home/.hermes-active/agent-center-enabled").read_text() == "enabled\n"
    local_bin = tmp_path / "home/.local/bin"
    for name in ("hermes-prewrite-gate", "hermes-new-chat", "hermes-worktree"):
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
    assert run_installer(team_dir, tmp_path).returncode == 0

    dest = vault_file(tmp_path, "skills/prompt-shortcuts/references/a.md")
    dest.write_text("owner newer work\n")
    future = time.time() + 60
    os.utime(dest, (future, future))

    result = run_installer(team_dir, tmp_path, "--force")

    assert result.returncode == 0, result.stderr + result.stdout
    assert dest.read_text() == "ref v1\n"
    backups = backup_dirs(tmp_path)
    assert len(backups) == 1
    assert (backups[0] / "skills/prompt-shortcuts/references/a.md").read_text() == "owner newer work\n"


def test_rerun_unchanged_payload_does_not_create_second_backup(tmp_path: Path):
    team_dir = build_fake_installer(tmp_path)
    assert run_installer(team_dir, tmp_path).returncode == 0

    dest = vault_file(tmp_path, "skills/prompt-shortcuts/references/a.md")
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
