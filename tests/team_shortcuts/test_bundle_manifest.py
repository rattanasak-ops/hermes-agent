from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "team-shortcuts" / "verify-bundle.py"


def load_module():
    spec = importlib.util.spec_from_file_location("shortcut_bundle", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_team(tmp_path: Path) -> Path:
    target = tmp_path / "team-shortcuts"
    shutil.copytree(ROOT / "team-shortcuts", target)
    return target


def install_fixture(module, team: Path, tmp_path: Path):
    manifest = module.build_manifest(team)
    root = tmp_path / "installed"
    hooks = tmp_path / "hooks"
    for entry in manifest["files"]:
        source = team / entry["path"]
        if entry["kind"] == "payload":
            target = root / entry["path"].removeprefix("payload/")
        elif entry["kind"] == "hook":
            target = hooks / Path(entry["path"]).name
        else:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (root / ".shortcut-version").write_text(manifest["version"] + "\n", encoding="utf-8")
    return manifest, root, hooks


def test_manifest_matches_current_package():
    module = load_module()
    manifest = module.load_manifest(ROOT / "team-shortcuts" / "BUNDLE-MANIFEST.json")
    result = module.verify_package(ROOT / "team-shortcuts", manifest)
    assert result["ok"] is True
    assert result["checked"] == manifest["file_count"]


def test_host_metadata_does_not_change_bundle_identity(tmp_path):
    module = load_module()
    team = copy_team(tmp_path)
    before = module.build_manifest(team)
    (team / "payload/.DS_Store").write_bytes(b"metadata")
    (team / "hooks/._team-stop-gates.py").write_bytes(b"metadata")
    after = module.build_manifest(team)
    assert after == before


def test_changed_payload_is_rejected(tmp_path):
    module = load_module()
    team = copy_team(tmp_path)
    manifest = module.build_manifest(team)
    target = team / "payload/skills/prompt-shortcuts/SKILL.md"
    target.write_text(target.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
    result = module.verify_package(team, manifest)
    assert result["ok"] is False
    assert any(item.startswith("size:payload/") or item.startswith("hash:payload/") for item in result["problems"])


def test_changed_installed_hook_is_rejected(tmp_path):
    module = load_module()
    team = copy_team(tmp_path)
    manifest, root, hooks = install_fixture(module, team, tmp_path)
    assert module.verify_installed(root, [hooks], manifest)["ok"] is True
    hook = next(hooks.glob("*.py"))
    hook.write_text("changed\n", encoding="utf-8")
    result = module.verify_installed(root, [hooks], manifest)
    assert result["ok"] is False
    assert any("hash:hooks/" in item or "size:hooks/" in item for item in result["problems"])


def test_manifest_aggregate_tampering_is_rejected(tmp_path):
    module = load_module()
    team = copy_team(tmp_path)
    path = tmp_path / "manifest.json"
    value = module.build_manifest(team)
    value["aggregate_sha256"] = "0" * 64
    path.write_text(json.dumps(value), encoding="utf-8")
    try:
        module.load_manifest(path)
    except ValueError as exc:
        assert "แฮชรวม" in str(exc)
    else:
        raise AssertionError("tampered aggregate was accepted")
