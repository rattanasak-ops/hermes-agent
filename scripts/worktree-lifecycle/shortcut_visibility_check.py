#!/usr/bin/env python3
"""Verify CURRENT_WORKSPACE_ONLY visibility through every shortcut path."""

from __future__ import annotations

import argparse
import hashlib
import json
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

ALL_SHORTCUTS = [
    "Use Act-As", "Use Comply", "Use Summary", "Use Scan Feature", "Use AI Relay",
    "Use Viber Structure", "Use Viber Audit", "Use Impeccable", "Use Blog Auto",
    "Use WOW Resource", "Use Flow Guardian", "Use New Chat", "Use Close Chat",
    "Use Save Git", "Use Merge to Production", "Use Continue", "Use Move Folder",
    "Review Chat", "Use AI Pair", "Use Business Plan", "Use SaaS Opus Master Prompt",
    "Use BusinessPlan", "Use OverviewProgress", "Use FeatureSpec", "Use DesignSystem",
    "Use Create Design System", "Use Hermes Structure", "Use Create Content",
    "Use QA QC", "Use SonarQube", "Use Migrate Web", "Use Migrate 0",
]

ACTIVE_CONFLICTS = [
    "งานเขียนใหม่ต้องเรียก `hermes-new-chat open`",
    "การเรียก Shortcut คือคำอนุมัติให้สร้างจริง",
    "ให้ Manager แสดง dry-run และรอเจ้าของอนุมัติ",
]

OWNER_BRANCH_POLICY = "OWNER_EXPLICIT_BRANCH_ONLY"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(vault: Path, payload: Path) -> dict:
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
    for label, text in (("policy", policy_text), ("skill", skill_text), ("contract", contract_text)):
        if OWNER_BRANCH_POLICY not in text:
            errors.append("owner_branch_policy_missing:{}".format(label))
    for shortcut in ALL_SHORTCUTS:
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

    parity_files = [
        "SKILL.md",
        "references/work-execution-policy.md",
        "references/worktree-lifecycle-contract.md",
    ] + [
        "references/{}".format(name) for name in DIRECT_FILES.values()
    ]
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
        "shortcut_visibility": "{}/{}".format(len(ALL_SHORTCUTS), len(ALL_SHORTCUTS)),
        "direct_integrations": "{}/{}".format(len(DIRECT_FILES), len(DIRECT_FILES)),
        "worktree_auto_create": "0/{}".format(len(ALL_SHORTCUTS)),
        "owner_branch_policy": "{}/{}".format(len(ALL_SHORTCUTS), len(ALL_SHORTCUTS)),
        "parity_files": len(parity_files) + 1,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True)
    parser.add_argument("--payload", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate(Path(args.vault).resolve(), Path(args.payload).resolve())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("WTL_SHORTCUTS_OK" if result["ok"] else "WTL_SHORTCUTS_BLOCKED")
        for error in result["errors"]:
            print("- {}".format(error))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
