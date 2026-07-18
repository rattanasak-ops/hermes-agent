from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEAM = ROOT / "team-shortcuts"
INSTALLER = TEAM / "install-shortcuts.ps1"


def _installer_text() -> str:
    return INSTALLER.read_text(encoding="utf-8")


def test_windows_powershell_installer_is_shipped_with_the_payload():
    text = _installer_text()

    assert 'Join-Path $ScriptRoot "payload"' in text
    assert 'Copy-Item -LiteralPath $RegistrySource' in text
    assert 'Copy-Item -LiteralPath $SkillSource' in text
    assert 'Copy-Item -LiteralPath $VersionFile' in text
    assert 'Join-Path $PayloadRoot "skills\\agent-center"' in text
    assert 'Join-Path $ScriptRoot "..\\plugins\\agent_center"' in text


def test_windows_installer_connects_codex_app_and_cursor_with_windows_pointers():
    text = _installer_text()

    assert 'Join-Path $HOME ".codex\\skills\\prompt-shortcuts"' in text
    assert "New-Item -ItemType Junction" in text
    assert 'Join-Path $HOME ".cursor\\rules\\hermes-prompt-shortcuts.mdc"' in text
    assert "alwaysApply: true" in text
    assert "$RegistryDestination" in text
    assert "$SkillDestination\\SKILL.md" in text
    assert 'Join-Path $HOME ".codex\\skills\\agent-center"' in text
    assert 'plugins enable agent-center' in text


def test_windows_installer_checks_all_migrate_phases_and_shared_contract_after_copy():
    text = _installer_text()

    assert "foreach ($phase in 0..13)" in text
    assert '"use-migrate-$phase.md"' in text
    assert '"use-migrate-phase-contract.md"' in text
    assert "$migrateCount -ne 14" in text
    assert "$registryCount -ne $skillCount" in text
    assert "$registryCount -ne $indexCount" in text
    assert 'Write-Host "RESULT: PASS"' in text


def test_windows_installer_states_mw_shell_requirement_truthfully():
    text = _installer_text()

    assert "WSL" in text
    assert "Git Bash" in text
    assert "ไม่ได้อ้างว่ารองรับ MW โดยตรง" in text
    assert "mw-setup.sh" not in text
