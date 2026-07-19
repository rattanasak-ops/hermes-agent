#!/usr/bin/env python3
"""Self-test response gates and real current-workspace wiring."""

from __future__ import annotations

import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tempfile


HOME = Path.home()
CLAUDE_HOOKS = HOME / ".claude" / "hooks"
CODEX_HOOKS = HOME / ".codex" / "hooks"
CURSOR_HOOKS = HOME / ".cursor" / "hooks"


def active_hermes_home() -> Path:
    explicit = os.environ.get("HERMES_HOME", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    default = HOME / ".hermes"
    try:
        account_home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    except (KeyError, OSError):
        return default
    if HOME.resolve() != account_home or shutil.which("hermes") is None:
        return default
    try:
        result = subprocess.run(
            ["hermes", "config", "path"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return default
    candidate = Path(result.stdout.strip()).expanduser()
    return candidate.resolve().parent if result.returncode == 0 and candidate.name == "config.yaml" else default


HERMES_HOME = active_hermes_home()
HERMES_HOOKS = HERMES_HOME / "hooks"


def call(path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(path)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
    )


def executable_call(path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(path)],
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


def gate_call(
    gate: Path,
    cwd: Path,
    tool: str,
    tool_input: dict,
    **extra: object,
) -> subprocess.CompletedProcess[str]:
    payload = {"tool_name": tool, "cwd": str(cwd), "tool_input": tool_input}
    payload.update(extra)
    return subprocess.run(
        [str(gate)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
    )


def wiring_checks(cwd: Path) -> dict[str, bool]:
    paths = {
        "claude": CLAUDE_HOOKS / "enforce-new-chat-relay.py",
        "codex": CODEX_HOOKS / "enforce-new-chat-relay.py",
        "cursor": CURSOR_HOOKS / "enforce-new-chat-relay.py",
        "hermes": HOME / ".local" / "bin" / "hermes-current-workspace-hook",
    }
    checks = {name: path.is_file() for name, path in paths.items()}
    settings = {
        "claude": HOME / ".claude" / "settings.json",
        "codex": HOME / ".codex" / "hooks.json",
        "cursor": HOME / ".cursor" / "hooks.json",
        "hermes": HERMES_HOME / "config.yaml",
    }
    for name, path in settings.items():
        try:
            text = path.read_text(encoding="utf-8")
            runner_name = "hermes-current-workspace-hook" if name == "hermes" else "enforce-new-chat-relay.py"
            checks[name] = checks[name] and runner_name in text and "hermes-owner-intent" in text
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
    branch_name = "task/doctor/owner-approved"
    branch_payload = {
        "tool_name": "Bash",
        "cwd": str(cwd),
        "tool_input": {"command": f"git switch -c {branch_name}"},
    }
    worktree_payload = {
        "tool_name": "Bash",
        "cwd": str(cwd),
        "tool_input": {"command": "hermes-new-chat open --task-id DOCTOR"},
    }
    for name, path in paths.items():
        if checks[name]:
            owner_intent = executable_call(
                HOME / ".local" / "bin" / "hermes-owner-intent",
                {"cwd": str(cwd), "user_message": f"สร้าง new branch = {branch_name}"},
            )
            checks[name] = (
                owner_intent.returncode == 0
                and call(path, allow_payload).returncode == 0
                and call(path, block_payload).returncode == 2
                and call(path, branch_payload).returncode == 0
                and call(path, {**branch_payload, "tool_input": {"command": "git switch -c task/doctor/another"}}).returncode == 2
                and call(path, worktree_payload).returncode == 2
            )
    return checks


def workspace_response_checks() -> dict[str, bool]:
    paths = {
        "claude": CLAUDE_HOOKS / "enforce-workspace-response.py",
        "codex": CODEX_HOOKS / "enforce-workspace-response.py",
        "cursor": CURSOR_HOOKS / "enforce-workspace-response.py",
        "hermes": HERMES_HOOKS / "enforce-workspace-response.py",
    }
    settings = {
        "claude": HOME / ".claude" / "settings.json",
        "codex": HOME / ".codex" / "hooks.json",
        "cursor": HOME / ".cursor" / "hooks.json",
        "hermes": HERMES_HOME / "config.yaml",
    }
    bad_answer = (
        "การกระทำเดียวที่ต้องให้เจ้าของทำ: "
        "เปิดหรือสร้างกิ่งงาน S1 ให้ workspace นี้ก่อน"
    )
    checks: dict[str, bool] = {}
    for name, path in paths.items():
        try:
            settings_text = settings[name].read_text(encoding="utf-8")
        except OSError:
            checks[name] = False
            continue
        if name == "hermes":
            result = call(
                path,
                {
                    "hook_event_name": "transform_llm_output",
                    "extra": {"response_text": bad_answer},
                },
            )
            behavior_ok = (
                result.returncode == 0
                and "WORKSPACE_OWNER_HANDOFF_BLOCKED" in result.stdout
            )
            wiring_ok = "transform_llm_output" in settings_text
        else:
            result = call(path, {"last_assistant_message": bad_answer})
            behavior_ok = (
                result.returncode == 2
                and "WORKSPACE_OWNER_HANDOFF_BLOCKED" in result.stderr
            )
            wiring_ok = (
                "team-stop-gates.py" in settings_text
                or "enforce-workspace-response.py" in settings_text
            )
            if name == "cursor":
                wiring_ok = wiring_ok and "afterAgentResponse" in settings_text and '"stop"' in settings_text
        checks[name] = path.is_file() and wiring_ok and behavior_ok
    return checks


def phase_autonomy_checks() -> dict[str, bool]:
    paths = {
        "claude": CLAUDE_HOOKS / "enforce-phase-autonomy.py",
        "codex": CODEX_HOOKS / "enforce-phase-autonomy.py",
        "cursor": CURSOR_HOOKS / "enforce-phase-autonomy.py",
        "hermes": HERMES_HOOKS / "enforce-phase-autonomy.py",
    }
    settings = {
        "claude": HOME / ".claude" / "settings.json",
        "codex": HOME / ".codex" / "hooks.json",
        "cursor": HOME / ".cursor" / "hooks.json",
        "hermes": HERMES_HOME / "config.yaml",
    }
    bad_answer = (
        "SPEC-P6-I1 ผ่านแล้ว แต่ I2-I4 ยังไม่ทำ "
        "อนุมัติให้ผมทำ I2-I4 ต่อไหมครับ"
    )
    allowed_answer = (
        "OWNER_INPUT_REQUIRED: LOGIN_REQUIRED\n"
        "หลักฐาน: ระบบตอบ 401 หลังเรียกบัญชีจริง 3/3 รอบ\n"
        "กรุณาเข้าสู่ระบบหนึ่งครั้ง แล้วผมจะทำเฟสเดิมต่อ"
    )
    checks: dict[str, bool] = {}
    for name, path in paths.items():
        try:
            settings_text = settings[name].read_text(encoding="utf-8")
        except OSError:
            checks[name] = False
            continue
        if name == "hermes":
            blocked = call(
                path,
                {
                    "hook_event_name": "transform_llm_output",
                    "extra": {"response_text": bad_answer},
                },
            )
            behavior_ok = (
                blocked.returncode == 0
                and "PHASE_CONTINUATION_REQUIRED" in blocked.stdout
                and call(
                    path,
                    {
                        "hook_event_name": "transform_llm_output",
                        "extra": {"response_text": allowed_answer},
                    },
                ).stdout == ""
            )
            wiring_ok = (
                "transform_llm_output" in settings_text
                and "enforce-phase-autonomy.py" in settings_text
            )
        else:
            blocked = call(path, {"last_assistant_message": bad_answer})
            allowed = call(path, {"last_assistant_message": allowed_answer})
            behavior_ok = (
                blocked.returncode == 2
                and "PHASE_CONTINUATION_REQUIRED" in blocked.stderr
                and allowed.returncode == 0
            )
            wiring_ok = (
                "team-stop-gates.py" in settings_text
                or "enforce-phase-autonomy.py" in settings_text
            )
            if name == "cursor":
                wiring_ok = (
                    wiring_ok
                    and "afterAgentResponse" in settings_text
                    and '"stop"' in settings_text
                )
        checks[name] = path.is_file() and wiring_ok and behavior_ok
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

    response_wiring = workspace_response_checks()
    results.append({
        "gate": "workspace_response",
        "ok": all(response_wiring.values()) and len(response_wiring) == 4,
        "wiring": response_wiring,
        "checks": f"{sum(response_wiring.values())}/{len(response_wiring)}",
    })

    phase_wiring = phase_autonomy_checks()
    results.append({
        "gate": "phase_autonomy",
        "ok": all(phase_wiring.values()) and len(phase_wiring) == 4,
        "wiring": phase_wiring,
        "checks": f"{sum(phase_wiring.values())}/{len(phase_wiring)}",
    })

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
                "worktree_manager_block": gate_call(gate, feature, "Bash", {"command": "hermes-new-chat open --task-id DOCTOR"}).returncode == 2,
                "worktree_git_c_block": gate_call(gate, feature, "Bash", {"command": "git -C . worktree add /tmp/doctor-hidden -b task/doctor/hidden"}).returncode == 2,
                "worktree_env_block": gate_call(gate, feature, "Bash", {"command": "env hermes-new-chat open --task-id DOCTOR-HIDDEN"}).returncode == 2,
                "worktree_nested_shell_block": gate_call(gate, feature, "Bash", {"command": "bash -lc 'git worktree add /tmp/doctor-hidden -b task/doctor/hidden'"}).returncode == 2,
                "owner_branch_create": gate_call(
                    gate,
                    feature,
                    "Bash",
                    {"command": "git switch -c task/doctor/owner-approved"},
                    user_prompt="สร้าง new branch = task/doctor/owner-approved",
                ).returncode == 0,
                "owner_branch_mismatch_block": gate_call(
                    gate,
                    feature,
                    "Bash",
                    {"command": "git switch -c task/doctor/ai-invented"},
                    user_prompt="สร้าง new branch = task/doctor/owner-approved",
                ).returncode == 2,
            }
            wiring = wiring_checks(feature)
            registry = base / "registry.json"
            recovery_branch = "task/doctor/registered-recovery"
            registry.write_text(
                json.dumps(
                    {
                        "tasks": {
                            "DOCTOR-RECOVERY": {
                                "task_id": "DOCTOR-RECOVERY",
                                "state": "ACTIVE",
                                "branch": recovery_branch,
                                "worktree_path": str(feature),
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            recovery_env = os.environ.copy()
            recovery_env["HERMES_WORKTREE_REGISTRY"] = str(registry)
            attached_recovery = subprocess.run(
                [
                    str(HOME / ".local/bin/hermes-current-workspace-recover"),
                    "--cwd",
                    str(feature),
                    "--json",
                ],
                env=recovery_env,
                capture_output=True,
                text=True,
            )
            attached_payload = json.loads(attached_recovery.stdout or "{}")
            attached_branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=feature,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            scenarios["attached_branch_refusal"] = (
                attached_recovery.returncode == 2
                and attached_payload.get("code") == "RECOVERY_NOT_DETACHED"
                and attached_branch == "task/doctor/current-workspace"
            )
            subprocess.run(
                ["git", "checkout", "--detach"], cwd=feature, check=True, capture_output=True
            )
            detached_gate = gate_call(gate, feature, "Write", {"file_path": "src/a.py"})
            dirty_file = feature / "src/in-progress.py"
            dirty_file.parent.mkdir(parents=True, exist_ok=True)
            dirty_file.write_text("keep doctor work\n", encoding="utf-8")
            before_worktrees = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=feature,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.count("worktree ")
            recovery = subprocess.run(
                [
                    str(HOME / ".local/bin/hermes-current-workspace-recover"),
                    "--cwd",
                    str(feature),
                    "--json",
                ],
                env=recovery_env,
                capture_output=True,
                text=True,
            )
            after_worktrees = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=feature,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.count("worktree ")
            recovered_branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=feature,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            scenarios.update(
                {
                    "detached_machine_recovery_message": (
                        detached_gate.returncode == 2
                        and "RECOVERY_REQUIRED_REGISTERED_BRANCH" in detached_gate.stderr
                        and "เจ้าของต้อง" not in detached_gate.stderr
                    ),
                    "registered_branch_recovery": (
                        recovery.returncode == 0
                        and recovered_branch == recovery_branch
                    ),
                    "recovery_preserves_dirty": dirty_file.read_text(encoding="utf-8") == "keep doctor work\n",
                    "recovery_does_not_add_worktree": before_worktrees == after_worktrees,
                }
            )
    results.append({
        "gate": "current_workspace_prewrite",
        "ok": bool(scenarios) and all(scenarios.values()) and all(wiring.values()),
        "scenarios": scenarios,
        "wiring": wiring,
        "checks": f"{sum(scenarios.values()) + sum(wiring.values())}/{len(scenarios) + len(wiring)}" if scenarios else "0/18",
    })

    ok = all(row["ok"] for row in results)
    print(json.dumps({"ok": ok, "gates": results}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
