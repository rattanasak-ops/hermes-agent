from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "hermes-standard" / "bin" / "hermes_std.py"


def load_hermes_std():
    spec = importlib.util.spec_from_file_location("hermes_std", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_init_places_project_only_under_dot_project(tmp_path):
    mod = load_hermes_std()

    created, synced, kept, legacy_found = mod.cmd_init(str(tmp_path))

    for rel in mod.PROJECT_ONLY:
        assert (tmp_path / ".project" / rel).is_file(), f"expected .project/{rel}"
        assert not (tmp_path / rel).exists() or rel in legacy_found

    for rel in ("CLAUDE.md", "AGENTS.md"):
        assert (tmp_path / rel).is_file(), f"expected root {rel}"
        assert not (tmp_path / ".project" / rel).exists()

    assert "plan.md" in created
    assert "decisions.md" in created
    assert legacy_found == []


def test_init_migration_skips_duplicate_when_legacy_at_root(tmp_path):
    mod = load_hermes_std()
    legacy = tmp_path / "OverviewProgress.md"
    legacy.write_text("# legacy overview\n", encoding="utf-8")

    created, _synced, kept, legacy_found = mod.cmd_init(str(tmp_path))

    assert legacy.is_file()
    assert not (tmp_path / ".project" / "OverviewProgress.md").exists()
    assert "OverviewProgress.md" in legacy_found
    assert "OverviewProgress.md" not in created
    assert all("OverviewProgress.md" not in item for item in kept)
