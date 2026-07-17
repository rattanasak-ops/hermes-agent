import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
TEAM = ROOT / "team-shortcuts"


def _table_rows(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("| `"))


def _skill_rows(path: Path) -> int:
    active = False
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "## Shortcut Map":
            active = True
            continue
        if active and line.startswith("## "):
            break
        if active and line.startswith("| `"):
            count += 1
    return count


def test_distribution_counts_are_consistent_without_hardcoded_old_totals():
    payload = TEAM / "payload"
    registry = payload / "ai-context/prompt-shortcut-registry.md"
    skill = payload / "skills/prompt-shortcuts/SKILL.md"
    index = payload / "skills/prompt-shortcuts/Prompt Shortcuts.md"
    refs = payload / "skills/prompt-shortcuts/references"

    registry_count = _table_rows(registry)
    assert registry_count == _skill_rows(skill)
    assert registry_count == _table_rows(index)
    assert len(list(refs.glob("*.md"))) >= registry_count


def test_distribution_has_traceable_version_and_required_runtime_tools():
    version = (TEAM / "VERSION").read_text(encoding="utf-8").strip()
    installer = (TEAM / "install-shortcuts.sh").read_text(encoding="utf-8")
    checker = (TEAM / "check-shortcuts.sh").read_text(encoding="utf-8")

    assert version == "2026.07.17-1"
    assert "INSTALLED_VERSION" in installer
    assert "ไม่พบตัวตรวจสุขภาพ Hook" in installer
    assert "registry_vs_skill" in checker
    assert '"29"' not in checker
    assert '"33"' not in checker


def _installed_shortcut_home(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    home = tmp_path / "home"
    root = home / "ObsidianVault/HermesAgent"
    shutil.copytree(TEAM / "payload", root)
    (root / ".shortcut-version").write_text("2026.07.17-1\n", encoding="utf-8")

    # แยกการทดสอบไฟล์ Migrate ออกจากจำนวนรายการ Shortcut อื่นใน payload
    (root / "ai-context/prompt-shortcut-registry.md").write_text("| `fixture` |\n", encoding="utf-8")
    (root / "skills/prompt-shortcuts/Prompt Shortcuts.md").write_text(
        "| `fixture` |\n", encoding="utf-8"
    )
    (root / "skills/prompt-shortcuts/SKILL.md").write_text(
        "## Shortcut Map\n| `fixture` |\n## End\n", encoding="utf-8"
    )

    codex_skill = home / ".codex/skills/prompt-shortcuts"
    codex_skill.parent.mkdir(parents=True)
    codex_skill.symlink_to(root / "skills/prompt-shortcuts")

    claude = home / ".claude/CLAUDE.md"
    claude.parent.mkdir(parents=True)
    claude.write_text("HERMES_SHORTCUTS_START\n", encoding="utf-8")

    local_bin = home / ".local/bin"
    local_bin.mkdir(parents=True)
    hook_doctor = local_bin / "hermes-hook-doctor"
    hook_doctor.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    hook_doctor.chmod(0o755)
    (local_bin / "hermes-write-permit").touch()

    env = os.environ.copy()
    env["HOME"] = str(home)
    env["HERMES_SHORTCUT_EXPECTED_VERSION"] = "2026.07.17-1"
    return root, env


def _run_shortcut_check(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(TEAM / "check-shortcuts.sh")],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_checker_accepts_all_14_migrate_phases_and_shared_contract(tmp_path):
    _, env = _installed_shortcut_home(tmp_path)

    result = _run_shortcut_check(env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "use_migrate_phase_coverage   14" in result.stdout
    assert "RESULT: PASS" in result.stdout


@pytest.mark.parametrize(
    "missing_name",
    [*(f"use-migrate-{phase}.md" for phase in range(14)), "use-migrate-phase-contract.md"],
)
def test_checker_fails_when_any_migrate_phase_or_contract_is_missing(tmp_path, missing_name):
    root, env = _installed_shortcut_home(tmp_path)
    (root / "skills/prompt-shortcuts/references" / missing_name).unlink()

    result = _run_shortcut_check(env)

    assert result.returncode != 0
    assert "RESULT: FAIL" in result.stdout
    assert missing_name in result.stdout


def test_github_installer_sets_up_shortcuts_relay_and_shell_path():
    installer = (TEAM / "install-from-github.sh").read_text(encoding="utf-8")

    assert 'RELAY_SRC="$ARCHIVE_ROOT/scripts/ai-relay"' in installer
    assert 'bash "$RELAY_DIR/scripts/ai-relay/install-local.sh"' in installer
    assert 'ensure_local_bin_path "$HOME/.zshrc"' in installer
    assert 'ensure_local_bin_path "$HOME/.bashrc"' in installer
    assert "AI Portal" in installer
    assert "codex login" not in installer
    assert "grok login" not in installer
    assert "relay-status --probe" in installer


def test_team_installer_includes_real_stop_hooks_for_fresh_notebooks():
    installer = (TEAM / "install-shortcuts.sh").read_text(encoding="utf-8")
    hook_installer = (TEAM / "install-team-hooks.py").read_text(encoding="utf-8")
    hook_dir = TEAM / "hooks"

    assert 'python3 "$TEAM_HOOK_INSTALLER"' in installer
    assert '".claude" / "settings.json"' in hook_installer
    assert '".codex" / "hooks.json"' in hook_installer
    assert (hook_dir / "validate-thai-language.py").is_file()
    assert (hook_dir / "enforce-codex-review.py").is_file()
    assert (hook_dir / "enforce-prompt-evidence.py").is_file()
    assert (hook_dir / "team-stop-gates.py").is_file()
