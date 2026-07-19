#!/usr/bin/env python3
"""Run the team response gates from one Stop hook."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parent
GATES = (
    "validate-thai-language.py",
    "enforce-codex-review.py",
    "enforce-prompt-evidence.py",
    "owner-friction-gate.py",
    "enforce-workspace-response.py",
    "enforce-phase-autonomy.py",
)


def main() -> int:
    payload = sys.stdin.read()
    transform_mode = False
    try:
        parsed_payload = json.loads(payload) if payload.strip() else {}
        transform_mode = (
            isinstance(parsed_payload, dict)
            and parsed_payload.get("hook_event_name") == "transform_llm_output"
        )
    except json.JSONDecodeError:
        transform_mode = False
    blockers: list[str] = []
    for name in GATES:
        path = HOOKS_DIR / name
        if not path.is_file():
            blockers.append(f"ไม่พบด่านตรวจ {path}")
            continue
        proc = subprocess.run(
            [sys.executable, str(path)],
            input=payload,
            text=True,
            capture_output=True,
            timeout=10,
        )
        if proc.returncode == 2:
            if transform_mode:
                text = (proc.stderr or proc.stdout or name).strip()
                print(json.dumps({"response_text": text}, ensure_ascii=False))
                return 0
            blockers.append((proc.stderr or proc.stdout or name).strip())
        elif proc.returncode != 0:
            blockers.append(f"ด่าน {name} ทำงานผิดปกติ exit={proc.returncode}")
        elif transform_mode and proc.stdout.strip():
            try:
                transformed = json.loads(proc.stdout)
            except json.JSONDecodeError:
                transformed = {}
            if isinstance(transformed, dict) and isinstance(transformed.get("response_text"), str):
                print(json.dumps({"response_text": transformed["response_text"]}, ensure_ascii=False))
                return 0

    if blockers:
        print("[Hermes Team Stop Gate] ไม่อนุญาตให้ส่งคำตอบรอบนี้", file=sys.stderr)
        for item in blockers:
            print(f"- {item}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
