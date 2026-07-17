from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEAM = ROOT / "team-shortcuts"


def test_readme_has_explicit_mac_commands_for_codex_app_and_cursor():
    text = (TEAM / "README.md").read_text(encoding="utf-8")

    assert "## วิธีติดตั้งบน Mac" in text
    assert "คำสั่งต่อไปนี้ติดตั้งให้ Codex App" in text
    assert "install-from-github.sh | bash" in text
    assert "install-from-github.sh | bash -s -- --cursor" in text


def test_readme_has_one_windows_command_for_cursor_and_codex_app():
    text = (TEAM / "README.md").read_text(encoding="utf-8")

    assert "## วิธีติดตั้งบน Windows" in text
    assert "คำสั่งเดียวติดตั้ง Shortcut ให้ทั้ง Cursor และ Codex App" in text
    assert "install-from-github.ps1 | iex" in text


def test_windows_docs_do_not_overclaim_mw_support():
    text = (TEAM / "README.md").read_text(encoding="utf-8")

    assert "ยังไม่มีหลักฐานว่าทำงานบน Windows PowerShell โดยตรง" in text
    assert "WSL หรือ Git Bash" in text


def test_windows_github_loader_downloads_and_runs_the_bundled_installer():
    text = (TEAM / "install-from-github.ps1").read_text(encoding="utf-8")

    assert "Invoke-WebRequest" in text
    assert "Expand-Archive" in text
    assert 'Filter "install-shortcuts.ps1"' in text
    assert "& $Installer.FullName" in text
    assert "Remove-Item -LiteralPath $TempRoot -Recurse -Force" in text


def test_mac_github_loader_prints_commands_for_both_platforms_without_mw_overclaim():
    text = (TEAM / "install-from-github.sh").read_text(encoding="utf-8")

    assert "Mac · Codex App:" in text
    assert "Mac · Cursor + Codex App:" in text
    assert "Windows · Cursor + Codex App:" in text
    assert "install-from-github.ps1 | iex" in text
    assert "MW บน Windows ยังต้องใช้ WSL หรือ Git Bash" in text
    assert "ยังไม่ยืนยันการรองรับผ่าน PowerShell โดยตรง" in text
