#!/usr/bin/env python3
"""Install team response gates without replacing existing AI settings."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
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
    """Install the global New Chat/Relay write gate and remove stale variants."""
    data = load_json(settings_path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {settings_path}")
    pre_tool_use = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre_tool_use, list):
        raise SystemExit(f"ช่อง hooks.PreToolUse ผิดรูปแบบใน {settings_path}")

    command = str(runner)
    target_name = runner.name
    stale_names = ("enforce-relay-flow.py", "enforce-new-chat-relay.py") if target_name == "enforce-new-chat-relay.py" else ()
    cleaned = []
    for entry in pre_tool_use:
        if not isinstance(entry, dict):
            cleaned.append(entry)
            continue
        kept = [
            hook for hook in entry.get("hooks", [])
            if not (
                isinstance(hook, dict)
                and any(name in str(hook.get("command", "")) for name in stale_names)
            )
        ]
        if kept:
            updated = dict(entry)
            updated["hooks"] = kept
            cleaned.append(updated)
    hooks["PreToolUse"] = cleaned
    pre_tool_use = cleaned
    found = False
    for entry in pre_tool_use:
        if not isinstance(entry, dict):
            continue
        for hook in entry.get("hooks", []):
            if isinstance(hook, dict) and target_name in str(
                hook.get("command", "")
            ):
                entry["matcher"] = "Edit|Write|MultiEdit|NotebookEdit|ApplyPatch|Bash"
                hook.update({"type": "command", "command": command, "timeout": 20})
                found = True
    if not found:
        pre_tool_use.append(
            {
                "matcher": "Edit|Write|MultiEdit|NotebookEdit|ApplyPatch|Bash",
                "hooks": [{"type": "command", "command": command, "timeout": 20}],
            }
        )

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(settings_path)


def install_cursor_entry(settings_path: Path, runner: Path) -> None:
    """Install Cursor's user-level preToolUse gate without replacing other hooks."""
    data = load_json(settings_path)
    data.setdefault("version", 1)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {settings_path}")
    entries = hooks.setdefault("preToolUse", [])
    if not isinstance(entries, list):
        raise SystemExit(f"ช่อง hooks.preToolUse ผิดรูปแบบใน {settings_path}")
    command = str(runner)
    entries[:] = [
        entry for entry in entries
        if not (
            isinstance(entry, dict)
            and "enforce-new-chat-relay.py" in str(entry.get("command", ""))
        )
    ]
    entries.append({
        "command": command,
        "matcher": "Shell|Bash|Write|Edit|ApplyPatch|apply_patch",
        "timeout": 20,
        "failClosed": True,
    })
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(settings_path)


def install_hermes_entry(config_path: Path, runner: Path) -> None:
    """Install Hermes Agent's user-level pre_tool_call shell hook."""
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("ติดตั้ง Hook ให้ Hermes Agent ไม่ได้: ไม่พบ PyYAML") from exc
    data = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if loaded is not None and not isinstance(loaded, dict):
            raise SystemExit(f"ไฟล์ตั้งค่าต้องเป็น YAML object: {config_path}")
        data = loaded or {}
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {config_path}")
    entries = hooks.setdefault("pre_tool_call", [])
    if not isinstance(entries, list):
        raise SystemExit(f"ช่อง hooks.pre_tool_call ผิดรูปแบบใน {config_path}")
    command = str(runner)
    entries[:] = [
        entry for entry in entries
        if not (
            isinstance(entry, dict)
            and "enforce-new-chat-relay.py" in str(entry.get("command", ""))
        )
    ]
    entries.append({
        "command": command,
        "matcher": "(?i)terminal|bash|shell|write|edit|apply_patch",
        "timeout": 20,
    })
    data["hooks_auto_accept"] = True
    config_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = config_path.with_suffix(config_path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp.replace(config_path)


def main() -> int:
    claude_hooks = HOME / ".claude" / "hooks"
    codex_hooks = HOME / ".codex" / "hooks"
    cursor_hooks = HOME / ".cursor" / "hooks"
    hermes_config = HOME / ".hermes" / "config.yaml"
    if shutil.which("hermes"):
        try:
            resolved = subprocess.run(
                ["hermes", "config", "path"], text=True, capture_output=True, timeout=10
            )
            if resolved.returncode == 0 and resolved.stdout.strip():
                hermes_config = Path(resolved.stdout.strip()).expanduser()
        except (OSError, subprocess.TimeoutExpired):
            pass
    hermes_hooks = hermes_config.parent / "hooks"
    install_files(claude_hooks)
    install_files(codex_hooks)
    install_files(cursor_hooks)
    install_files(hermes_hooks)
    install_stop_entry(HOME / ".claude" / "settings.json", claude_hooks / "team-stop-gates.py")
    install_pretooluse_entry(
        HOME / ".claude" / "settings.json", claude_hooks / "enforce-new-chat-relay.py"
    )
    install_stop_entry(HOME / ".codex" / "hooks.json", codex_hooks / "team-stop-gates.py")
    install_pretooluse_entry(
        HOME / ".codex" / "hooks.json", codex_hooks / "enforce-new-chat-relay.py"
    )
    install_cursor_entry(
        HOME / ".cursor" / "hooks.json", cursor_hooks / "enforce-new-chat-relay.py"
    )
    install_hermes_entry(
        hermes_config, hermes_hooks / "enforce-new-chat-relay.py"
    )
    print("ติดตั้ง Hook ทีมให้ Claude Code, Codex, Cursor และ Hermes Agent แล้ว")
    return 0


if __name__ == "__main__":
    sys.exit(main())
