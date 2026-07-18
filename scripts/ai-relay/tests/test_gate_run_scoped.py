import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE_RUN = ROOT / "gate-run.py"


def _prepare_python_repo(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'gate-fixture'\nversion = '0.0.0'\n",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    first = tests_dir / "test_first.py"
    second = tests_dir / "test_second.py"
    first.write_text("def test_first():\n    assert True\n", encoding="utf-8")
    second.write_text("def test_second():\n    assert True\n", encoding="utf-8")

    fake_python = tmp_path / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$@\" > \"$GATE_CAPTURE\"\n"
        "printf 'scoped gate ok\\n'\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    return first.relative_to(tmp_path), second.relative_to(tmp_path)


def _run_gate(tmp_path: Path, *test_paths: str):
    capture = tmp_path / "gate-args.txt"
    env = os.environ.copy()
    env["GATE_CAPTURE"] = str(capture)
    command = [
        sys.executable,
        str(GATE_RUN),
        "--cwd",
        str(tmp_path),
        "--task-id",
        "UAG-P2-P3",
    ]
    for test_path in test_paths:
        command.extend(["--test-path", test_path])
    return subprocess.run(command, capture_output=True, text=True, env=env, check=False)


def test_scoped_pytest_paths_run_and_write_project_evidence(tmp_path):
    first, second = _prepare_python_repo(tmp_path)

    result = _run_gate(tmp_path, str(first), str(second))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())
    assert payload["gate_status"] == "pass"
    assert payload["gate_command"] == (
        "pytest -q tests/test_first.py tests/test_second.py"
    )
    assert (tmp_path / "gate-args.txt").read_text(encoding="utf-8").splitlines() == [
        "-m",
        "pytest",
        "-q",
        "tests/test_first.py",
        "tests/test_second.py",
    ]

    output_ref = Path(payload["output_ref"])
    assert output_ref.parent == tmp_path / ".project" / "gate-output"
    assert output_ref.read_text(encoding="utf-8") == "scoped gate ok\n"
    ledger = tmp_path / ".project" / "ledger" / "nobranch.md"
    assert ledger.is_file()
    assert "UAG-P2-P3" in ledger.read_text(encoding="utf-8")
    assert not (tmp_path / ".hermes").exists()


def test_scoped_pytest_path_cannot_escape_repository(tmp_path):
    _prepare_python_repo(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text("def test_outside():\n    assert True\n", encoding="utf-8")

    result = _run_gate(tmp_path, f"../{outside.name}")

    assert result.returncode == 3
    payload = json.loads(result.stdout.strip())
    assert payload["gate_status"] == "error"
    assert payload["reason"] == "test path อยู่นอก Git root"
    assert payload["ledger_written"] is True
    assert not (tmp_path / "gate-args.txt").exists()
    assert not (tmp_path / ".hermes").exists()
