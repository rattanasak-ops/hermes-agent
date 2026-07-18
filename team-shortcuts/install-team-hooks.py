#!/usr/bin/env python3
"""Install team response gates without replacing existing AI settings."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys


HOME = Path.home()
SOURCE = Path(__file__).resolve().parent / "hooks"
HOOK_NAMES = (
    "validate-thai-language.py",
    "enforce-codex-review.py",
    "enforce-prompt-evidence.py",
    "team-stop-gates.py",
    "enforce-flow-gate.py",
    "enforce-new-chat-relay.py",
)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ไฟล์ตั้งค่า JSON เสียที่ {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"ไฟล์ตั้งค่าต้องเป็น JSON object: {path}")
    return value


def install_files(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name in HOOK_NAMES:
        src = SOURCE / name
        if not src.is_file():
            raise SystemExit(f"ไม่พบไฟล์ Hook ในชุดติดตั้ง: {src}")
        dst = target / name
        if not dst.exists() or src.read_bytes() != dst.read_bytes():
            shutil.copy2(src, dst)
        dst.chmod(0o755)


def install_stop_entry(settings_path: Path, runner: Path) -> None:
    data = load_json(settings_path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {settings_path}")
    stop = hooks.setdefault("Stop", [])
    if not isinstance(stop, list):
        raise SystemExit(f"ช่อง hooks.Stop ผิดรูปแบบใน {settings_path}")

    existing_commands = [
        str(hook.get("command", ""))
        for entry in stop
        if isinstance(entry, dict)
        for hook in entry.get("hooks", [])
        if isinstance(hook, dict)
    ]
    has_native_bundle = (
        any("validate-all-stop.py" in command for command in existing_commands)
        and any("enforce-codex-review.py" in command for command in existing_commands)
    )

    if has_native_bundle:
        cleaned = []
        for entry in stop:
            if not isinstance(entry, dict):
                cleaned.append(entry)
                continue
            hooks_in_entry = entry.get("hooks", [])
            kept = [
                hook for hook in hooks_in_entry
                if not (isinstance(hook, dict) and "team-stop-gates.py" in str(hook.get("command", "")))
            ]
            if kept:
                updated = dict(entry)
                updated["hooks"] = kept
                cleaned.append(updated)
        hooks["Stop"] = cleaned
        stop = cleaned

    command = str(runner)
    found = False
    for entry in stop:
        if not isinstance(entry, dict):
            continue
        for hook in entry.get("hooks", []):
            if isinstance(hook, dict) and "team-stop-gates.py" in str(hook.get("command", "")):
                hook.update({"type": "command", "command": command, "timeout": 12})
                found = True
    if not found and not has_native_bundle:
        stop.append({"hooks": [{"type": "command", "command": command, "timeout": 12}]})

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(settings_path)


def install_pretooluse_entry(settings_path: Path, runner: Path) -> None:
    """Install the MW write gate without disturbing other PreToolUse hooks."""
    data = load_json(settings_path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {settings_path}")
    pre_tool_use = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre_tool_use, list):
        raise SystemExit(f"ช่อง hooks.PreToolUse ผิดรูปแบบใน {settings_path}")

    command = str(runner)
    found = False
    for entry in pre_tool_use:
        if not isinstance(entry, dict):
            continue
        for hook in entry.get("hooks", []):
            if isinstance(hook, dict) and "enforce-flow-gate.py" in str(
                hook.get("command", "")
            ):
                entry["matcher"] = "Edit|Write|NotebookEdit|Bash"
                hook.update({"type": "command", "command": command, "timeout": 20})
                found = True
    if not found:
        pre_tool_use.append(
            {
                "matcher": "Edit|Write|NotebookEdit|Bash",
                "hooks": [{"type": "command", "command": command, "timeout": 20}],
            }
        )

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(settings_path)


def install_new_chat_entry(settings_path: Path, runner: Path) -> None:
    """Install the current-workspace gate while preserving the old filename."""
    data = load_json(settings_path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {settings_path}")
    pre_tool_use = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre_tool_use, list):
        raise SystemExit(f"ช่อง hooks.PreToolUse ผิดรูปแบบใน {settings_path}")

    matcher = "Edit|Write|MultiEdit|NotebookEdit|ApplyPatch|Bash"
    command = str(runner)
    found = False
    for entry in pre_tool_use:
        if not isinstance(entry, dict):
            continue
        for hook in entry.get("hooks", []):
            if isinstance(hook, dict) and "enforce-new-chat-relay.py" in str(
                hook.get("command", "")
            ):
                entry["matcher"] = matcher
                hook.update({"type": "command", "command": command, "timeout": 20})
                found = True
    if not found:
        pre_tool_use.append(
            {
                "matcher": matcher,
                "hooks": [{"type": "command", "command": command, "timeout": 20}],
            }
        )

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(settings_path)


def install_cursor_entry(settings_path: Path, runner: Path) -> None:
    data = load_json(settings_path)
    data.setdefault("version", 1)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {settings_path}")
    entries = hooks.setdefault("preToolUse", [])
    if not isinstance(entries, list):
        raise SystemExit(f"ช่อง hooks.preToolUse ผิดรูปแบบใน {settings_path}")
    command = str(runner)
    found = False
    for entry in entries:
        if isinstance(entry, dict) and "enforce-new-chat-relay.py" in str(entry.get("command", "")):
            entry.update(
                {
                    "command": command,
                    "matcher": "Shell|Bash|Write|Edit|ApplyPatch|apply_patch",
                    "timeout": 20,
                    "failClosed": True,
                }
            )
            found = True
    if not found:
        entries.append(
            {
                "command": command,
                "matcher": "Shell|Bash|Write|Edit|ApplyPatch|apply_patch",
                "timeout": 20,
                "failClosed": True,
            }
        )
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(settings_path)


def install_hermes_config_entry(config_path: Path, runner: Path) -> None:
    """Append one Hermes pre_tool_call hook without rewriting existing YAML."""
    command = str(runner)
    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    if "enforce-new-chat-relay.py" in text:
        return
    block = (
        "\nhooks:\n"
        "  pre_tool_call:\n"
        f"    - command: {command}\n"
        "      timeout: 20\n"
    )
    if not text.strip():
        updated = block.lstrip("\n")
    elif "\nhooks:\n" not in "\n" + text:
        updated = text.rstrip() + block
    else:
        lines = text.splitlines()
        hooks_index = next(i for i, line in enumerate(lines) if line.strip() == "hooks:" and not line.startswith(" "))
        section_end = len(lines)
        for i in range(hooks_index + 1, len(lines)):
            if lines[i] and not lines[i].startswith((" ", "#")):
                section_end = i
                break
        pre_index = next(
            (i for i in range(hooks_index + 1, section_end) if lines[i].strip() == "pre_tool_call:"),
            None,
        )
        if pre_index is None:
            insert = ["  pre_tool_call:", f"    - command: {command}", "      timeout: 20"]
            lines[section_end:section_end] = insert
        else:
            insert_at = section_end
            for i in range(pre_index + 1, section_end):
                if lines[i].startswith("  ") and not lines[i].startswith("    ") and lines[i].strip():
                    insert_at = i
                    break
            lines[insert_at:insert_at] = [f"    - command: {command}", "      timeout: 20"]
        updated = "\n".join(lines) + "\n"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = config_path.with_suffix(config_path.suffix + ".tmp")
    tmp.write_text(updated, encoding="utf-8")
    tmp.replace(config_path)


def install_hermes_allowlist(path: Path, runner: Path) -> None:
    data = load_json(path)
    approvals = data.setdefault("approvals", [])
    if not isinstance(approvals, list):
        raise SystemExit(f"ช่อง approvals ผิดรูปแบบใน {path}")
    command = str(runner)
    if not any(
        isinstance(row, dict)
        and row.get("event") == "pre_tool_call"
        and row.get("command") == command
        for row in approvals
    ):
        approvals.append({"event": "pre_tool_call", "command": command})
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    claude_hooks = HOME / ".claude" / "hooks"
    codex_hooks = HOME / ".codex" / "hooks"
    cursor_hooks = HOME / ".cursor" / "hooks"
    hermes_hooks = HOME / ".hermes" / "hooks"
    install_files(claude_hooks)
    install_files(codex_hooks)
    install_files(cursor_hooks)
    install_files(hermes_hooks)
    install_stop_entry(HOME / ".claude" / "settings.json", claude_hooks / "team-stop-gates.py")
    install_pretooluse_entry(
        HOME / ".claude" / "settings.json", claude_hooks / "enforce-flow-gate.py"
    )
    install_new_chat_entry(
        HOME / ".claude" / "settings.json", claude_hooks / "enforce-new-chat-relay.py"
    )
    install_stop_entry(HOME / ".codex" / "hooks.json", codex_hooks / "team-stop-gates.py")
    install_new_chat_entry(
        HOME / ".codex" / "hooks.json", codex_hooks / "enforce-new-chat-relay.py"
    )
    install_cursor_entry(
        HOME / ".cursor" / "hooks.json", cursor_hooks / "enforce-new-chat-relay.py"
    )
    install_hermes_config_entry(
        HOME / ".hermes" / "config.yaml", hermes_hooks / "enforce-new-chat-relay.py"
    )
    install_hermes_allowlist(
        HOME / ".hermes" / "shell-hooks-allowlist.json",
        hermes_hooks / "enforce-new-chat-relay.py",
    )
    print("ติดตั้ง Hook พื้นที่ปัจจุบันให้ Claude Code, Codex, Cursor และ Hermes Agent แล้ว")
    return 0


if __name__ == "__main__":
    sys.exit(main())
