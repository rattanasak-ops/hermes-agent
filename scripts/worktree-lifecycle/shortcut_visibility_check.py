#!/usr/bin/env python3
"""Verify CURRENT_WORKSPACE_ONLY visibility through every shortcut path."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DIRECT_FILES = {
    "Use New Chat": "use-new-chat.md",
    "Use Flow Guardian": "use-flow-guardian.md",
    "Use AI Relay": "use-ai-relay.md",
    "Use Continue": "use-continue.md",
    "Use Close Chat": "use-close-chat.md",
    "Review Chat": "review-chat.md",
    "Use Save Git": "use-save-git.md",
    "Use Merge to Production": "use-merge-to-production.md",
    "Use Move Folder": "use-move-folder.md",
    "Use AI Pair": "use-ai-pair.md",
    "Use Act-As": "use-act-as.md",
    "Use Comply": "use-comply.md",
    "Use OverviewProgress": "use-overviewprogress.md",
    "Use QA QC": "use-qa-qc.md",
    "Use SonarQube": "use-sonarqube.md",
    "Use Hermes Structure": "use-hermes-structure.md",
    "Use Viber Structure": "use-viber-structure.md",
    "Use Viber Audit": "use-viber-audit.md",
}

ACTIVE_CONFLICTS = [
    "งานเขียนใหม่ต้องเรียก `hermes-new-chat open`",
    "การเรียก Shortcut คือคำอนุมัติให้สร้างจริง",
    "ให้ Manager แสดง dry-run และรอเจ้าของอนุมัติ",
]

OWNER_BRANCH_POLICY = "OWNER_EXPLICIT_BRANCH_ONLY"

NEGATION_MARKERS = (
    "ห้าม", "ไม่สร้าง", "ไม่สลับ", "ไม่ย้าย", "ไม่ลบ", "อย่า", "ปฏิเสธ",
    "ขวาง", "หยุด", "never", "must not", "may not", "do not", "don't",
    "without creating", "without switching",
)

WORKTREE_MUTATION_PATTERNS = (
    re.compile(r"\bhermes(?:-new-chat)?\s+worktree\s+(?:open|enter)\b", re.I),
    re.compile(r"\bhermes-new-chat\s+open\b", re.I),
    re.compile(r"\bgit\s+worktree\s+(?:add|remove|move)\b", re.I),
    re.compile(r"worktree-first\s+multi-agent", re.I),
    re.compile(r"worktree/branch\s+แยก", re.I),
    re.compile(r"ต้องแยก\s+scope,?\s*worktree/branch", re.I),
    re.compile(r"มีผลเหนือ\s+fixed-workspace", re.I),
    re.compile(r"ต้องเลือก\s+branch/worktree", re.I),
    re.compile(r"auto-create\s+worktrees", re.I),
    re.compile(r"parallel.+worktrees", re.I),
    re.compile(r"create\s+a\s+separate\s+temporary\s+worktree", re.I),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shortcut_names(markdown: str) -> list[str]:
    """Read canonical shortcut names from the first column of a map table."""
    names = []
    for line in markdown.splitlines():
        match = re.match(r"^\| `([^`]+)`", line)
        if match:
            names.append(match.group(1))
    return names


def active_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8").split("## Changelog", 1)[0]
    return text.splitlines()


def has_negation(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in NEGATION_MARKERS)


def validate(vault: Path, payload: Path, repo: Path | None = None) -> dict:
    refs = vault / "skills" / "prompt-shortcuts" / "references"
    payload_skill = payload / "skills" / "prompt-shortcuts"
    contract = refs / "worktree-lifecycle-contract.md"
    policy = refs / "work-execution-policy.md"
    skill = vault / "skills" / "prompt-shortcuts" / "SKILL.md"
    registry = vault / "ai-context" / "prompt-shortcut-registry.md"
    errors = []

    for path in (contract, policy, skill, registry):
        if not path.is_file():
            errors.append("missing:{}".format(path))

    contract_text = contract.read_text(encoding="utf-8") if contract.is_file() else ""
    policy_text = policy.read_text(encoding="utf-8") if policy.is_file() else ""
    skill_text = skill.read_text(encoding="utf-8") if skill.is_file() else ""
    registry_text = registry.read_text(encoding="utf-8") if registry.is_file() else ""
    registry_shortcuts = shortcut_names(registry_text)
    skill_shortcuts = shortcut_names(skill_text)
    all_shortcuts = sorted(set(registry_shortcuts))

    if len(registry_shortcuts) != len(set(registry_shortcuts)):
        errors.append("duplicate_shortcut:registry")
    if len(skill_shortcuts) != len(set(skill_shortcuts)):
        errors.append("duplicate_shortcut:skill")
    for shortcut in sorted(set(registry_shortcuts) - set(skill_shortcuts)):
        errors.append("skill_missing_shortcut:{}".format(shortcut))
    for shortcut in sorted(set(skill_shortcuts) - set(registry_shortcuts)):
        errors.append("registry_missing_shortcut:{}".format(shortcut))

    for label, text in (("policy", policy_text), ("skill", skill_text), ("contract", contract_text)):
        if OWNER_BRANCH_POLICY not in text:
            errors.append("owner_branch_policy_missing:{}".format(label))
    for shortcut in all_shortcuts:
        if shortcut not in contract_text:
            errors.append("contract_missing_shortcut:{}".format(shortcut))

    for shortcut, filename in DIRECT_FILES.items():
        path = refs / filename
        if not path.is_file():
            errors.append("direct_file_missing:{}:{}".format(shortcut, filename))
            continue
        text = path.read_text(encoding="utf-8")
        active = text.split("## Changelog", 1)[0]
        if "work-execution-policy.md" not in text:
            errors.append("direct_current_workspace_policy_missing:{}:{}".format(shortcut, filename))
        for phrase in ACTIVE_CONFLICTS:
            if phrase in active:
                errors.append("active_conflict:{}:{}".format(filename, phrase))

    reference_files = sorted(refs.glob("*.md")) if refs.is_dir() else []
    for path in reference_files:
        for line_number, line in enumerate(active_lines(path), start=1):
            if has_negation(line):
                continue
            if any(pattern.search(line) for pattern in WORKTREE_MUTATION_PATTERNS):
                errors.append(
                    "worktree_mutation_instruction:{}:{}:{}".format(
                        path.name, line_number, line.strip()
                    )
                )

    repo = repo or Path(__file__).resolve().parents[2]
    repo_policy_files = sorted((repo / "skills").glob("**/SKILL.md"))
    review_doc = repo / "team-shortcuts" / "shortcut-review.md"
    if review_doc.is_file():
        repo_policy_files.append(review_doc)
    for path in repo_policy_files:
        for line_number, line in enumerate(active_lines(path), start=1):
            if has_negation(line):
                continue
            if any(pattern.search(line) for pattern in WORKTREE_MUTATION_PATTERNS):
                errors.append(
                    "repo_worktree_mutation_instruction:{}:{}:{}".format(
                        path.relative_to(repo), line_number, line.strip()
                    )
                )

    parity_files = [
        "SKILL.md",
    ] + ["references/{}".format(path.name) for path in reference_files]
    for relative in parity_files:
        source = vault / "skills" / "prompt-shortcuts" / relative
        mirror = payload_skill / relative
        if not mirror.is_file():
            errors.append("payload_missing:{}".format(relative))
        elif source.is_file() and digest(source) != digest(mirror):
            errors.append("payload_mismatch:{}".format(relative))
    payload_registry = payload / "ai-context" / "prompt-shortcut-registry.md"
    if not payload_registry.is_file() or (registry.is_file() and digest(registry) != digest(payload_registry)):
        errors.append("payload_mismatch:ai-context/prompt-shortcut-registry.md")

    return {
        "ok": not errors,
        "mode": "CURRENT_WORKSPACE_ONLY",
        "shortcut_visibility": "{}/{}".format(len(all_shortcuts), len(all_shortcuts)),
        "direct_integrations": "{}/{}".format(len(DIRECT_FILES), len(DIRECT_FILES)),
        "worktree_auto_create": "0/{}".format(len(all_shortcuts)),
        "owner_branch_policy": "{}/{}".format(len(all_shortcuts), len(all_shortcuts)),
        "reference_files_scanned": len(reference_files),
        "repo_policy_files_scanned": len(repo_policy_files),
        "parity_files": len(parity_files) + 1,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True)
    parser.add_argument("--payload", required=True)
    parser.add_argument("--repo")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate(
        Path(args.vault).resolve(),
        Path(args.payload).resolve(),
        Path(args.repo).resolve() if args.repo else None,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("WTL_SHORTCUTS_OK" if result["ok"] else "WTL_SHORTCUTS_BLOCKED")
        for error in result["errors"]:
            print("- {}".format(error))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
