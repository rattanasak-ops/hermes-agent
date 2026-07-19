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
    "enforce-spec-gate.py",
    "record-spec-owner.py",
    "enforce-shortcut-central.py",
    "goal_contract.py",
    "goal_evidence.py",
    "enforce-goal-contract.py",
    "phase_state.py",
    "enforce-phase-autonomy.py",
    "memory_receipt.py",
    "enforce-memory-receipt.py",
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


def install_spec_tool() -> None:
    source = Path(__file__).resolve().parents[1] / "scripts/spec-interview/spec_interview.py"
    if not source.is_file():
        raise SystemExit(f"ไม่พบ spec-interview: {source}")
    target = HOME / ".hermes/spec-tools/spec_interview.py"
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copy2(source, target)
    target.chmod(0o700)


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
            if isinstance(hook, dict) and "enforce-flow-gate.py" in str(hook.get("command", "")):
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


def install_shortcut_guard_entry(settings_path: Path, runner: Path) -> None:
    """Install the central Shortcut write guard without replacing other gates."""
    data = load_json(settings_path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {settings_path}")
    pre_tool_use = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre_tool_use, list):
        raise SystemExit(f"ช่อง hooks.PreToolUse ผิดรูปแบบใน {settings_path}")

    command = str(runner)
    for entry in pre_tool_use:
        if not isinstance(entry, dict):
            continue
        for hook in entry.get("hooks", []):
            if isinstance(hook, dict) and "enforce-shortcut-central.py" in str(hook.get("command", "")):
                entry["matcher"] = "Edit|Write|NotebookEdit|Bash"
                hook.update({"type": "command", "command": command, "timeout": 20})
                break
        else:
            continue
        break
    else:
        pre_tool_use.append(
            {
                "matcher": "Edit|Write|NotebookEdit|Bash",
                "hooks": [{"type": "command", "command": command, "timeout": 20}],
            }
        )

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(settings_path)


def install_goal_contract_entry(settings_path: Path, runner: Path) -> None:
    """Install the active-task write gate without replacing other gates."""
    data = load_json(settings_path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {settings_path}")
    entries = hooks.setdefault("PreToolUse", [])
    if not isinstance(entries, list):
        raise SystemExit(f"ช่อง hooks.PreToolUse ผิดรูปแบบใน {settings_path}")
    command = str(runner)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for hook in entry.get("hooks", []):
            if isinstance(hook, dict) and "enforce-goal-contract.py" in str(hook.get("command", "")):
                entry["matcher"] = "Edit|Write|NotebookEdit|Bash"
                hook.update({"type": "command", "command": command, "timeout": 20})
                break
        else:
            continue
        break
    else:
        entries.append(
            {
                "matcher": "Edit|Write|NotebookEdit|Bash",
                "hooks": [{"type": "command", "command": command, "timeout": 20}],
            }
        )
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(settings_path)


def install_phase_autonomy_entry(settings_path: Path, runner: Path) -> None:
    """Install the phase-state response gate without replacing other Stop hooks."""
    data = load_json(settings_path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {settings_path}")
    stop = hooks.setdefault("Stop", [])
    if not isinstance(stop, list):
        raise SystemExit(f"ช่อง hooks.Stop ผิดรูปแบบใน {settings_path}")

    command = str(runner)
    for entry in stop:
        if not isinstance(entry, dict):
            continue
        for hook in entry.get("hooks", []):
            if isinstance(hook, dict) and "enforce-phase-autonomy.py" in str(hook.get("command", "")):
                hook.update({"type": "command", "command": command, "timeout": 20})
                break
        else:
            continue
        break
    else:
        stop.append({"hooks": [{"type": "command", "command": command, "timeout": 20}]})

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(settings_path)


def install_memory_receipt_entry(settings_path: Path, runner: Path) -> None:
    """Install New Chat receipt inspection without replacing owner hooks."""
    data = load_json(settings_path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {settings_path}")
    entries = hooks.setdefault("UserPromptSubmit", [])
    if not isinstance(entries, list):
        raise SystemExit(f"ช่อง hooks.UserPromptSubmit ผิดรูปแบบใน {settings_path}")
    command = str(runner)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for hook in entry.get("hooks", []):
            if isinstance(hook, dict) and "enforce-memory-receipt.py" in str(hook.get("command", "")):
                hook.update({"type": "command", "command": command, "timeout": 20})
                break
        else:
            continue
        break
    else:
        entries.append({"hooks": [{"type": "command", "command": command, "timeout": 20}]})
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(settings_path)


def install_spec_entries(settings_path: Path, pre_runner: Path, owner_runner: Path) -> None:
    data = load_json(settings_path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"ช่อง hooks ผิดรูปแบบใน {settings_path}")
    pre = hooks.setdefault("PreToolUse", [])
    owner = hooks.setdefault("UserPromptSubmit", [])
    if not isinstance(pre, list) or not isinstance(owner, list):
        raise SystemExit(f"ช่อง Hook SPEC ผิดรูปแบบใน {settings_path}")

    def upsert(entries: list, marker: str, command: Path, matcher: str | None = None) -> None:
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for hook in entry.get("hooks", []):
                if isinstance(hook, dict) and marker in str(hook.get("command", "")):
                    hook.update({"type": "command", "command": str(command), "timeout": 20})
                    if matcher:
                        entry["matcher"] = matcher
                    return
        item = {"hooks": [{"type": "command", "command": str(command), "timeout": 20}]}
        if matcher:
            item["matcher"] = matcher
        entries.append(item)

    upsert(pre, "enforce-spec-gate.py", pre_runner, "Edit|Write|NotebookEdit|Bash|Task|Agent|Delegate")
    upsert(owner, "record-spec-owner.py", owner_runner)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(settings_path)


def main() -> int:
    claude_hooks = HOME / ".claude" / "hooks"
    codex_hooks = HOME / ".codex" / "hooks"
    install_files(claude_hooks)
    install_files(codex_hooks)
    install_spec_tool()
    install_stop_entry(HOME / ".claude" / "settings.json", claude_hooks / "team-stop-gates.py")
    install_pretooluse_entry(
        HOME / ".claude" / "settings.json", claude_hooks / "enforce-flow-gate.py"
    )
    install_shortcut_guard_entry(
        HOME / ".claude" / "settings.json", claude_hooks / "enforce-shortcut-central.py"
    )
    install_goal_contract_entry(
        HOME / ".claude" / "settings.json", claude_hooks / "enforce-goal-contract.py"
    )
    install_phase_autonomy_entry(
        HOME / ".claude" / "settings.json", claude_hooks / "enforce-phase-autonomy.py"
    )
    install_memory_receipt_entry(
        HOME / ".claude" / "settings.json", claude_hooks / "enforce-memory-receipt.py"
    )
    install_spec_entries(
        HOME / ".claude" / "settings.json",
        claude_hooks / "enforce-spec-gate.py",
        claude_hooks / "record-spec-owner.py",
    )
    install_stop_entry(HOME / ".codex" / "hooks.json", codex_hooks / "team-stop-gates.py")
    install_shortcut_guard_entry(
        HOME / ".codex" / "hooks.json", codex_hooks / "enforce-shortcut-central.py"
    )
    install_goal_contract_entry(
        HOME / ".codex" / "hooks.json", codex_hooks / "enforce-goal-contract.py"
    )
    install_phase_autonomy_entry(
        HOME / ".codex" / "hooks.json", codex_hooks / "enforce-phase-autonomy.py"
    )
    install_memory_receipt_entry(
        HOME / ".codex" / "hooks.json", codex_hooks / "enforce-memory-receipt.py"
    )
    install_spec_entries(
        HOME / ".codex" / "hooks.json",
        codex_hooks / "enforce-spec-gate.py",
        codex_hooks / "record-spec-owner.py",
    )
    print("ติดตั้ง Hook ทีมให้ Claude Code และ Codex แล้ว")
    return 0


if __name__ == "__main__":
    sys.exit(main())
