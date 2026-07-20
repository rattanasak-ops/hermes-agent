from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = Path(
    os.environ.get("SCG_INSTALLER_UNDER_TEST")
    or ROOT / "team-shortcuts/install-team-hooks.py"
)


def load_installer():
    spec = importlib.util.spec_from_file_location("team_hook_installer_phase", INSTALLER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def commands(settings: dict, event: str) -> list[str]:
    return [
        str(hook.get("command", ""))
        for entry in settings.get("hooks", {}).get(event, [])
        if isinstance(entry, dict)
        for hook in entry.get("hooks", [])
        if isinstance(hook, dict)
    ]


def test_installer_registers_phase_gate_for_claude_and_codex(monkeypatch, tmp_path):
    module = load_installer()
    monkeypatch.setattr(module, "HOME", tmp_path)
    source = tmp_path / "source-hooks"
    source.mkdir()
    for name in module.HOOK_NAMES:
        (source / name).write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    monkeypatch.setattr(module, "SOURCE", source)
    monkeypatch.setattr(module, "install_spec_tool", lambda: None)

    assert {"phase_state.py", "enforce-phase-autonomy.py"} <= set(module.HOOK_NAMES)
    assert module.main() == 0

    claude = json.loads((tmp_path / ".claude/settings.json").read_text(encoding="utf-8"))
    codex = json.loads((tmp_path / ".codex/hooks.json").read_text(encoding="utf-8"))
    assert any("enforce-phase-autonomy.py" in item for item in commands(claude, "Stop"))
    assert any("enforce-phase-autonomy.py" in item for item in commands(codex, "Stop"))
    assert (tmp_path / ".claude/hooks/phase_state.py").is_file()
    assert (tmp_path / ".codex/hooks/phase_state.py").is_file()
