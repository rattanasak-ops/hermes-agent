#!/usr/bin/env python3
"""Build and verify the versioned Team Shortcut content manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any


SCHEMA = "hermes-shortcut-bundle-v1"
MANIFEST_NAME = "BUNDLE-MANIFEST.json"
PACKAGE_FILES = (
    "VERSION",
    "check-shortcuts.sh",
    "install-from-github.sh",
    "install-shortcuts.sh",
    "install-team-hooks.py",
    "sync-from-vault.sh",
    "team-hook-doctor.py",
    "verify-bundle.py",
)
IGNORED_NAMES = {".DS_Store"}


def is_ignored(path: Path) -> bool:
    """Return True for host metadata that must not affect bundle identity."""
    return any(part in IGNORED_NAMES or part.startswith("._") for part in path.parts)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate(entries: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda item: item["path"]):
        digest.update(
            f"{entry['path']}\0{entry['sha256']}\0{entry['size']}\n".encode("utf-8")
        )
    return digest.hexdigest()


def package_paths(team_root: Path) -> list[tuple[Path, str]]:
    paths: list[tuple[Path, str]] = []
    for parent, kind, pattern in (
        (team_root / "payload", "payload", "*"),
        (team_root / "hooks", "hook", "*.py"),
    ):
        if not parent.is_dir():
            continue
        for path in sorted(parent.rglob(pattern)):
            if path.is_file() and not is_ignored(path.relative_to(team_root)):
                paths.append((path, kind))
    for relative in PACKAGE_FILES:
        path = team_root / relative
        if path.is_file():
            paths.append((path, "package"))
    return paths


def build_manifest(team_root: Path) -> dict[str, Any]:
    version_path = team_root / "VERSION"
    if not version_path.is_file():
        raise ValueError("ไม่พบ VERSION ในชุดแจก")
    entries = [
        {
            "path": path.relative_to(team_root).as_posix(),
            "kind": kind,
            "size": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path, kind in package_paths(team_root)
    ]
    if not entries:
        raise ValueError("ชุดแจกไม่มีไฟล์ให้สร้างรายการแฮช")
    return {
        "schema": SCHEMA,
        "version": version_path.read_text(encoding="utf-8").strip(),
        "aggregate_sha256": aggregate(entries),
        "file_count": len(entries),
        "files": sorted(entries, key=lambda item: item["path"]),
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
    temporary.replace(path)


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ValueError("รูปแบบใบรายการแฮชไม่ถูกต้อง")
    files = value.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("ใบรายการแฮชไม่มีรายการไฟล์")
    if value.get("file_count") != len(files):
        raise ValueError("จำนวนไฟล์ในใบรายการแฮชไม่ตรง")
    if value.get("aggregate_sha256") != aggregate(files):
        raise ValueError("แฮชรวมในใบรายการถูกแก้หรือคำนวณไม่ตรง")
    return value


def verify_file(path: Path, entry: dict[str, Any]) -> str | None:
    if not path.is_file():
        return f"missing:{entry['path']}"
    if path.stat().st_size != entry.get("size"):
        return f"size:{entry['path']}"
    if sha256(path) != entry.get("sha256"):
        return f"hash:{entry['path']}"
    return None


def verify_package(team_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    problems: list[str] = []
    version = (team_root / "VERSION").read_text(encoding="utf-8").strip()
    if version != manifest.get("version"):
        problems.append(f"version:{version}!={manifest.get('version')}")
    for entry in manifest["files"]:
        problem = verify_file(team_root / entry["path"], entry)
        if problem:
            problems.append(problem)

    expected_dynamic = {
        entry["path"]
        for entry in manifest["files"]
        if entry.get("kind") in {"payload", "hook"}
    }
    actual_dynamic = {
        path.relative_to(team_root).as_posix()
        for path, kind in package_paths(team_root)
        if kind in {"payload", "hook"}
    }
    for extra in sorted(actual_dynamic - expected_dynamic):
        problems.append(f"extra:{extra}")
    return {
        "ok": not problems,
        "version": version,
        "aggregate_sha256": manifest["aggregate_sha256"],
        "checked": len(manifest["files"]),
        "problems": problems,
    }


def installed_target(entry: dict[str, Any], root: Path, hook_root: Path) -> Path | None:
    relative = entry["path"]
    if entry.get("kind") == "payload":
        return root / relative.removeprefix("payload/")
    if entry.get("kind") == "hook":
        return hook_root / Path(relative).name
    return None


def verify_installed(
    root: Path,
    hook_roots: list[Path],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    problems: list[str] = []
    installed_version = root / ".shortcut-version"
    version = installed_version.read_text(encoding="utf-8").strip() if installed_version.is_file() else ""
    if version != manifest.get("version"):
        problems.append(f"version:{version or 'MISSING'}!={manifest.get('version')}")

    checked = 0
    for entry in manifest["files"]:
        if entry.get("kind") == "payload":
            target = installed_target(entry, root, hook_roots[0] if hook_roots else Path())
            assert target is not None
            problem = verify_file(target, entry)
            checked += 1
            if problem:
                problems.append(problem)
        elif entry.get("kind") == "hook":
            for hook_root in hook_roots:
                target = installed_target(entry, root, hook_root)
                assert target is not None
                problem = verify_file(target, entry)
                checked += 1
                if problem:
                    problems.append(f"{hook_root}:{problem}")

    return {
        "ok": not problems,
        "version": version,
        "aggregate_sha256": manifest["aggregate_sha256"],
        "checked": checked,
        "hook_roots": [str(path) for path in hook_roots],
        "problems": problems,
    }


def emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload.get("ok") else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--team-root", type=Path, default=Path(__file__).resolve().parent)
    build.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / MANIFEST_NAME)
    package = commands.add_parser("verify-package")
    package.add_argument("--team-root", type=Path, default=Path(__file__).resolve().parent)
    package.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parent / MANIFEST_NAME)
    installed = commands.add_parser("verify-installed")
    installed.add_argument("--root", type=Path, required=True)
    installed.add_argument("--hook-root", type=Path, action="append", default=[])
    installed.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            manifest = build_manifest(args.team_root.resolve())
            write_manifest(args.output.resolve(), manifest)
            return emit({"ok": True, "manifest": str(args.output.resolve()), **manifest})
        manifest = load_manifest(args.manifest.resolve())
        if args.command == "verify-package":
            return emit(verify_package(args.team_root.resolve(), manifest))
        return emit(
            verify_installed(
                args.root.expanduser().resolve(),
                [path.expanduser().resolve() for path in args.hook_root],
                manifest,
            )
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return emit({"ok": False, "problems": [str(exc)]})


if __name__ == "__main__":
    raise SystemExit(main())
