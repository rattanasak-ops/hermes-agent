#!/usr/bin/env python3
"""Self-test response gates and real current-workspace wiring."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


HOME = Path.home()
CLAUDE_HOOKS = HOME / ".claude" / "hooks"
CODEX_HOOKS = HOME / ".codex" / "hooks"
CURSOR_HOOKS = HOME / ".cursor" / "hooks"
HERMES_HOOKS = HOME / ".hermes" / "hooks"


def call(path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(path)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
    )


def transcript(path: Path, tool_name: str, final: str, command: str = "") -> None:
    rows = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "- แก้ระบบ\n- เพิ่ม test"}]}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": tool_name, "input": {"file_path": "/tmp/app.py", "command": command}}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": final}]}},
    ]
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def make_repo(path: Path, branch: str) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", branch], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "doctor@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Hermes Doctor"], cwd=path, check=True)
    (path / "README.md").write_text("doctor\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "doctor"], cwd=path, check=True, capture_output=True)
    return path.resolve()


def gate_call(gate: Path, cwd: Path, tool: str, tool_input: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(gate)],
        input=json.dumps({"tool_name": tool, "cwd": str(cwd), "tool_input": tool_input}),
        text=True,
        capture_output=True,
    )


def wiring_checks(cwd: Path) -> dict[str, bool]:
    paths = {
        "claude": CLAUDE_HOOKS / "enforce-new-chat-relay.py",
        "codex": CODEX_HOOKS / "enforce-new-chat-relay.py",
        "cursor": CURSOR_HOOKS / "enforce-new-chat-relay.py",
        "hermes": HERMES_HOOKS / "enforce-new-chat-relay.py",
    }
    checks = {name: path.is_file() for name, path in paths.items()}
    settings = {
        "claude": HOME / ".claude" / "settings.json",
        "codex": HOME / ".codex" / "hooks.json",
        "cursor": HOME / ".cursor" / "hooks.json",
        "hermes": HOME / ".hermes" / "config.yaml",
    }
    for name, path in settings.items():
        try:
            checks[name] = checks[name] and "enforce-new-chat-relay.py" in path.read_text(encoding="utf-8")
        except OSError:
            checks[name] = False
    allow_payload = {
        "tool_name": "Bash",
        "cwd": str(cwd),
        "tool_input": {"command": "pnpm dev"},
    }
    block_payload = {
        "tool_name": "Write",
        "cwd": str(cwd),
        "tool_input": {"file_path": ".env"},
    }
    for name, path in paths.items():
        if checks[name]:
            checks[name] = (
                call(path, allow_payload).returncode == 0
                and call(path, block_payload).returncode == 2
            )
    return checks


def main() -> int:
    results = []
    thai = call(CLAUDE_HOOKS / "validate-thai-language.py", {"last_assistant_message": "leverage utilize synergy seamless robust scalable optimize"})
    results.append({"gate": "plain_language", "ok": thai.returncode == 2, "exit": thai.returncode})

    with tempfile.TemporaryDirectory() as tmp:
        review_file = Path(tmp) / "review.jsonl"
        transcript(review_file, "apply_patch", "เสร็จแล้วครับ")
        review = call(CODEX_HOOKS / "enforce-codex-review.py", {"transcript_path": str(review_file), "last_assistant_message": "เสร็จแล้วครับ"})
        results.append({"gate": "independent_review", "ok": review.returncode == 2, "exit": review.returncode})

        evidence_file = Path(tmp) / "evidence.jsonl"
        transcript(evidence_file, "apply_patch", "เสร็จครบ 100% แล้วครับ")
        evidence = call(CLAUDE_HOOKS / "enforce-prompt-evidence.py", {"transcript_path": str(evidence_file), "last_assistant_message": "เสร็จครบ 100% แล้วครับ"})
        results.append({"gate": "prompt_evidence", "ok": evidence.returncode == 2, "exit": evidence.returncode})

    gate = HOME / ".local" / "bin" / "hermes-prewrite-gate"
    scenarios = {}
    wiring = {}
    if gate.is_file():
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            feature = make_repo(base / "feature", "task/doctor/current-workspace")
            shared = make_repo(base / "shared", "main")
            other = make_repo(base / "other", "task/doctor/other")
            scenarios = {
                "direct_write": gate_call(gate, feature, "Write", {"file_path": "src/a.py"}).returncode == 0,
                "pnpm_dev": gate_call(gate, feature, "Bash", {"command": "pnpm dev"}).returncode == 0,
                "shared_branch_block": gate_call(gate, shared, "Write", {"file_path": "src/a.py"}).returncode == 2,
                "cross_root_block": gate_call(gate, feature, "Write", {"file_path": str(other / "src/a.py")}).returncode == 2,
                "env_block": gate_call(gate, feature, "Write", {"file_path": ".env"}).returncode == 2,
                "hermes_dir_block": gate_call(gate, feature, "Write", {"file_path": ".hermes/state.json"}).returncode == 2,
                "dangerous_block": gate_call(gate, feature, "Bash", {"command": "git reset --hard HEAD~1"}).returncode == 2,
                "branch_switch_block": gate_call(gate, feature, "Bash", {"command": "git switch -c task/doctor/new"}).returncode == 2,
                "new_chat_open_block": gate_call(
                    gate,
                    feature,
                    "Bash",
                    {
                        "command": (
                            "hermes-new-chat open --project hermes-agent --staff-id nat "
                            "--task-id T --slug t --repo /tmp --approval ok"
                        )
                    },
                ).returncode == 2,
            }
            wiring = wiring_checks(feature)
    results.append({
        "gate": "current_workspace_prewrite",
        "ok": bool(scenarios) and all(scenarios.values()) and all(wiring.values()),
        "scenarios": scenarios,
        "wiring": wiring,
        "checks": f"{sum(scenarios.values()) + sum(wiring.values())}/{len(scenarios) + len(wiring)}" if scenarios else "0/12",
    })

    ok = all(row["ok"] for row in results)
    print(json.dumps({"ok": ok, "gates": results}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
