import json
import subprocess
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
GATE = TOOLS_DIR / "ds-gate.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_gate(*args):
    return subprocess.run(
        [sys.executable, str(GATE), *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_complete_design_system_passes_all_layers():
    result = run_gate("--file", FIXTURES / "designsystem-pass.md", "--layer", "all", "--json")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["errors"] == []


def test_incomplete_h_layer_reports_h2_and_h5():
    result = run_gate("--file", FIXTURES / "designsystem-fail-h.md", "--layer", "H")

    assert result.returncode == 1
    assert "[H2]" in result.stdout
    assert "[H5]" in result.stdout


def test_incomplete_f_layer_reports_f5_and_f7():
    result = run_gate("--file", FIXTURES / "designsystem-fail-f.md", "--layer", "F")

    assert result.returncode == 1
    assert "[F5]" in result.stdout
    assert "[F7]" in result.stdout


def test_init_creates_todo_template_that_fails_gate_and_never_overwrites(tmp_path):
    design_system = tmp_path / ".project" / "DesignSystem.md"

    created = run_gate("--file", design_system, "--init")
    assert created.returncode == 0
    original = design_system.read_text(encoding="utf-8")
    assert "TODO" in original

    checked = run_gate("--file", design_system, "--layer", "all")
    assert checked.returncode == 1
    assert "ยังมี TODO" in checked.stdout

    repeated = run_gate("--file", design_system, "--init")
    assert repeated.returncode == 1
    assert "มีไฟล์อยู่แล้ว" in repeated.stdout
    assert design_system.read_text(encoding="utf-8") == original


def test_missing_file_exits_two_and_recommends_init(tmp_path):
    missing = tmp_path / "missing.md"

    result = run_gate("--file", missing)

    assert result.returncode == 2
    assert "ไม่พบไฟล์" in result.stdout
    assert "--init" in result.stdout
