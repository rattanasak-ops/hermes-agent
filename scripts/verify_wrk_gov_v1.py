#!/usr/bin/env python3
"""ตรวจสัญญา WRK-GOV-V1 และ Pilot Hermes Agent แบบอ่านอย่างเดียว."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
from typing import Any


REFERENCE_ROOT = Path(
    "team-shortcuts/payload/skills/prompt-shortcuts/references"
)
CORE_FILES = (
    "work-execution-policy.md",
    "project-worktree-adapter.schema.json",
    "worktree-registry-v2.schema.json",
    "recovery-cleanup-gate.md",
    "shortcut-worktree-contract.md",
)
SUPPORT_FILES = (
    "wrk-gov-v1.md",
    "worktree-lifecycle-contract.md",
    "old-chat-recovery-packet.md",
    "hermes-agent.worktree-adapter.example.json",
)


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def add_check(checks: list[dict[str, Any]], name: str, ok: bool, detail: Any) -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} ต้องเป็น JSON object")
    return value


def validate_adapter(adapter: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if adapter.get("schema_version") != "wrk-gov-project-adapter-v1":
        errors.append("schema_version ไม่ตรง")
    if adapter.get("standard_version") != "WRK-GOV-V1":
        errors.append("standard_version ไม่ตรง")
    repository = adapter.get("repository") or {}
    if not repository.get("owner_urls"):
        errors.append("ขาด repository.owner_urls")
    machines = adapter.get("machines") or []
    machine_ids = [item.get("machine_id") for item in machines if isinstance(item, dict)]
    if not machines or len(machine_ids) != len(set(machine_ids)):
        errors.append("machine_id ขาดหรือซ้ำ")
    if adapter.get("default_writer_machine_id") not in machine_ids:
        errors.append("default_writer_machine_id ไม่อยู่ใน machines")
    if adapter.get("runtime_machine_id") not in machine_ids:
        errors.append("runtime_machine_id ไม่อยู่ใน machines")
    for machine in machines:
        if not isinstance(machine, dict):
            errors.append("machine ต้องเป็น object")
            continue
        for field in ("canonical_repo", "worktree_roots", "remote_alias"):
            if not machine.get(field):
                errors.append(f"{machine.get('machine_id', 'unknown')} ขาด {field}")
    cleanup = adapter.get("cleanup") or {}
    if cleanup.get("manager_only") is not True:
        errors.append("cleanup.manager_only ต้องเป็น true")
    if cleanup.get("gate_count") != 6:
        errors.append("cleanup.gate_count ต้องเป็น 6")
    if int(cleanup.get("quarantine_hours") or 0) < 72:
        errors.append("cleanup.quarantine_hours ต้องไม่น้อยกว่า 72")
    return errors


def mapped_prompt_files(skill_text: str) -> tuple[list[str], list[str]]:
    rows = [
        line for line in skill_text.splitlines()
        if line.startswith("| `Use ") or line.startswith("| `Review Chat`")
    ]
    mapped = re.findall(r"`references/([^`]+\.md)`", skill_text)
    expanded: list[str] = []
    for item in mapped:
        if "<เลข>" in item:
            expanded.extend(f"use-migrate-{index}.md" for index in range(14))
        else:
            expanded.append(item)
    return rows, sorted(set(expanded))


def inspect_pilot(repo: Path) -> dict[str, Any]:
    root = Path(run_git(repo, "rev-parse", "--show-toplevel"))
    branch = run_git(repo, "branch", "--show-current") or "DETACHED"
    sha = run_git(repo, "rev-parse", "HEAD")
    dirty_lines = run_git(repo, "status", "--short").splitlines()
    worktree_text = run_git(repo, "worktree", "list", "--porcelain")
    worktree_count = sum(1 for line in worktree_text.splitlines() if line.startswith("worktree "))
    remotes = run_git(repo, "remote", "-v").splitlines()
    return {
        "git_root": str(root),
        "branch": branch,
        "sha": sha,
        "dirty_entries": len(dirty_lines),
        "worktree_count": worktree_count,
        "remotes": remotes,
        "mutation_count": 0,
    }


def verify(repo_root: Path, pilot_repo: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    reference_root = repo_root / REFERENCE_ROOT

    missing_core = [name for name in CORE_FILES if not (reference_root / name).is_file()]
    add_check(checks, "core_files_5_of_5", not missing_core, {"missing": missing_core})

    missing_support = [name for name in SUPPORT_FILES if not (reference_root / name).is_file()]
    add_check(checks, "support_files", not missing_support, {"missing": missing_support})

    schema_errors: list[str] = []
    for name in ("project-worktree-adapter.schema.json", "worktree-registry-v2.schema.json"):
        try:
            schema = load_json(reference_root / name)
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                schema_errors.append(f"{name}: $schema ไม่ตรง")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            schema_errors.append(f"{name}: {exc}")
    add_check(checks, "json_schemas_parse", not schema_errors, schema_errors)

    adapter_errors: list[str] = []
    adapter: dict[str, Any] = {}
    try:
        adapter = load_json(reference_root / "hermes-agent.worktree-adapter.example.json")
        adapter_errors = validate_adapter(adapter)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        adapter_errors = [str(exc)]
    add_check(checks, "pilot_adapter", not adapter_errors, adapter_errors)

    skill_path = repo_root / "team-shortcuts/payload/skills/prompt-shortcuts/SKILL.md"
    skill_text = skill_path.read_text(encoding="utf-8")
    rows, prompt_files = mapped_prompt_files(skill_text)
    missing_prompts = [name for name in prompt_files if not (reference_root / name).is_file()]
    add_check(
        checks,
        "shortcut_families_33_of_33",
        len(rows) == 33,
        {"count": len(rows)},
    )
    add_check(
        checks,
        "mapped_prompt_files_exist",
        not missing_prompts,
        {"mapped": len(prompt_files), "missing": missing_prompts},
    )
    central_markers = (
        "references/work-execution-policy.md",
        "references/wrk-gov-v1.md",
        "references/recovery-cleanup-gate.md",
        "references/shortcut-worktree-contract.md",
    )
    missing_markers = [marker for marker in central_markers if marker not in skill_text]
    add_check(checks, "skill_inherits_wrk_gov", not missing_markers, {"missing": missing_markers})

    pilot: dict[str, Any]
    try:
        pilot = inspect_pilot(pilot_repo)
        notebook = next(
            machine
            for machine in adapter.get("machines", [])
            if machine.get("machine_id") == "notebook-nat"
        )
        pilot_ok = pilot["git_root"] == notebook.get("canonical_repo")
        add_check(checks, "hermes_agent_read_only_pilot", pilot_ok, pilot)
    except (OSError, subprocess.CalledProcessError, StopIteration) as exc:
        pilot = {"error": str(exc), "mutation_count": 0}
        add_check(checks, "hermes_agent_read_only_pilot", False, pilot)

    ok = all(check["ok"] for check in checks)
    return {
        "ok": ok,
        "decision": "WRK_GOV_V1_CONTRACT_PASS" if ok else "WRK_GOV_V1_CONTRACT_FAIL",
        "standard_version": "WRK-GOV-V1",
        "checks_passed": sum(1 for check in checks if check["ok"]),
        "checks_total": len(checks),
        "checks": checks,
        "pilot": pilot,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--pilot-repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = verify(args.repo_root.resolve(), args.pilot_repo.resolve())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["decision"])
        print(f"ด่านผ่าน {result['checks_passed']}/{result['checks_total']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
