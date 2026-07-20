import json
from pathlib import Path
import re


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
    manifest = json.loads((TEAM / "BUNDLE-MANIFEST.json").read_text(encoding="utf-8"))
    installer = (TEAM / "install-shortcuts.sh").read_text(encoding="utf-8")
    checker = (TEAM / "check-shortcuts.sh").read_text(encoding="utf-8")

    assert re.fullmatch(r"\d{4}\.\d{2}\.\d{2}-\d+", version)
    assert manifest["version"] == version
    assert (TEAM / "BUNDLE-MANIFEST.json").is_file()
    assert (TEAM / "verify-bundle.py").is_file()
    assert "INSTALLED_VERSION" in installer
    assert "BUNDLE-MANIFEST.json" in installer
    assert "verify-package" in installer
    assert "verify-installed" in installer
    assert "HERMES_SHORTCUT_ALLOW_DOWNGRADE" in installer
    assert "ชุดเก่าจะไม่ถูกนำกลับมาทับชุดใหม่" in installer
    assert "ไฟล์ที่ติดตั้งไม่ตรงกับชุดแจก" in installer
    assert "ไม่พบตัวตรวจสุขภาพ Hook" in installer
    assert 'BACKUP_ROOT="${HERMES_SHORTCUT_BACKUP_ROOT:-$HOME/.hermes/backups/shortcuts}"' in installer
    assert installer.count("diff -qr --exclude='.DS_Store'") == 2
    assert 'mv "${backups[$i]}" "$BACKUP_QUARANTINE/$name"' in installer
    assert 'rm -rf -- "${backups[$i]}"' not in installer
    assert "registry_vs_skill" in checker
    assert "manifest_matches_source" in checker
    assert "installed_bundle_hash" in checker
    assert '"29"' not in checker
    assert '"33"' not in checker


def test_distribution_contains_current_workspace_and_agent_center_contracts():
    payload = TEAM / "payload"
    skill = (payload / "skills/prompt-shortcuts/SKILL.md").read_text(encoding="utf-8")
    registry = (payload / "ai-context/prompt-shortcut-registry.md").read_text(
        encoding="utf-8"
    )
    refs = payload / "skills/prompt-shortcuts/references"
    use_agent = (refs / "use-agent.md").read_text(encoding="utf-8")
    work_policy = (refs / "work-execution-policy.md").read_text(encoding="utf-8")
    use_continue = (refs / "use-continue.md").read_text(encoding="utf-8")
    flow_guardian = (refs / "use-flow-guardian.md").read_text(encoding="utf-8")

    assert "| `Use Agent`" in skill
    assert "| `Use Agent`" in registry
    assert "Work Execution Policy v2.3" in registry
    assert "v1.2 · รองรับงานคิด" in registry
    assert "receipt_runtime_valid" in use_agent
    assert "CURRENT_WORKSPACE_ONLY" in work_policy
    assert "งบคำถามสำหรับงาน ZONE_A = 0 ครั้ง" in use_continue
    assert "ห้ามสร้าง ลบ ย้าย หรือสลับ Worktree/กิ่ง" in flow_guardian
    assert "New writable work must go through Worktree Manager" not in skill


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
    assert 'HOOK_DOCTOR_SRC="$SCRIPT_DIR/team-hook-doctor.py"' in installer
    assert (TEAM / "team-hook-doctor.py").is_file()
    assert '".claude" / "settings.json"' in hook_installer
    assert '".codex" / "hooks.json"' in hook_installer
    assert (hook_dir / "validate-thai-language.py").is_file()
    assert (hook_dir / "enforce-codex-review.py").is_file()
    assert (hook_dir / "enforce-prompt-evidence.py").is_file()
    assert (hook_dir / "team-stop-gates.py").is_file()
    assert (hook_dir / "enforce-spec-gate.py").is_file()
    assert (hook_dir / "record-spec-owner.py").is_file()
    assert "UserPromptSubmit" in hook_installer
    assert "spec_interview.py" in hook_installer
