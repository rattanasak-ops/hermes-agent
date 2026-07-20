#!/usr/bin/env python3
"""Block direct Shortcut edits outside the Hermes Agent source project."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable


EDIT_TOOLS = {"edit", "write", "multiedit", "notebookedit", "applypatch", "apply_patch"}
RUNTIME_MARKERS = (
    ".codex/skills/prompt-shortcuts/",
    ".claude/skills/prompt-shortcuts/",
    ".cursor/skills/prompt-shortcuts/",
    ".hermes/skills/prompt-shortcuts/",
)
SOURCE_MARKERS = (
    "skills/prompt-shortcuts/",
    "ai-context/prompt-shortcut-registry.md",
    "team-shortcuts/",
)
SHELL_WRITE_RE = re.compile(
    r"(?:^|\s)(?:cp|mv|install|tee|truncate|touch|chmod|chown|sed\s+-i|perl\s+-i|python\S*\s+-c)\b|>>?|\bapply_patch\b",
    re.I,
)


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _git_root(cwd: Path) -> Path:
    try:
        text = subprocess.check_output(
            ["git", "-c", f"safe.directory={cwd}", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(text).resolve()
    except (OSError, subprocess.CalledProcessError):
        return cwd.resolve()


def _is_central(root: Path) -> bool:
    return (
        (root / "team-shortcuts/VERSION").is_file()
        and (root / "team-shortcuts/payload/skills/prompt-shortcuts/SKILL.md").is_file()
    )


def _normalized(text: str, cwd: Path) -> str:
    expanded = os.path.expandvars(os.path.expanduser(text)).replace("\\", "/")
    if expanded.startswith("./"):
        expanded = str((cwd / expanded).resolve())
    return "/" + expanded.lstrip("/")


def _write_intent(tool_name: str, payload: dict[str, Any]) -> bool:
    clean_name = tool_name.lower().replace("-", "").replace("_", "")
    if clean_name in {name.replace("_", "") for name in EDIT_TOOLS}:
        return True
    command = str(payload.get("command") or payload.get("cmd") or "")
    return bool(command and SHELL_WRITE_RE.search(command))


def decide(payload: dict[str, Any]) -> tuple[bool, str]:
    tool_name = str(payload.get("tool_name") or payload.get("name") or "")
    tool_input = payload.get("tool_input") or payload.get("input") or payload
    if not isinstance(tool_input, dict) or not _write_intent(tool_name, tool_input):
        return True, "read_only"
    cwd = Path(str(payload.get("cwd") or tool_input.get("cwd") or os.getcwd())).expanduser().resolve()
    root = _git_root(cwd)
    values = [_normalized(item, cwd) for item in _strings(tool_input)]

    if any(marker in value for value in values for marker in RUNTIME_MARKERS):
        return False, "RUNTIME_SHORTCUT_EDIT_BLOCKED"
    touches_source = any(marker in value for value in values for marker in SOURCE_MARKERS)
    if touches_source and not _is_central(root):
        return False, "SHORTCUT_CENTRAL_EDIT_BLOCKED"
    return True, "central_or_unrelated"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    allowed, reason = decide(payload)
    if allowed:
        return 0
    print(
        f"{reason}: ห้ามแก้ Shortcut จากโปรเจกต์ผู้แจ้ง · SHORTCUT_REPORT_ONLY\n"
        "ให้บันทึกชื่อ Shortcut ขั้นที่เสีย สิ่งที่ควรเกิด สิ่งที่เกิดจริง และหลักฐาน "
        "ผ่าน `hermes shortcut-incident record` แล้วนำ Prompt ที่สร้างเมื่อเกิดครั้งที่ 4 "
        "มาแก้ในโปรเจกต์ Hermes Agent เท่านั้น",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
