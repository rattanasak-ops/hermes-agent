#!/usr/bin/env python3
"""Run the three team response gates from one Stop hook."""

from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path


HOOKS_DIR = Path(__file__).resolve().parent
GATES = (
    "validate-thai-language.py",
    "enforce-codex-review.py",
    "enforce-prompt-evidence.py",
    "owner-friction-gate.py",
)


def main() -> int:
    payload = sys.stdin.read()
    transform_mode = False
    try:
        transform_mode = json.loads(payload).get("hook_event_name") == "transform_llm_output"
    except Exception:
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
            blockers.append((proc.stderr or proc.stdout or name).strip())
        elif proc.returncode != 0:
            blockers.append(f"ด่าน {name} ทำงานผิดปกติ exit={proc.returncode}")

    if blockers:
        if transform_mode:
            replacement = (
                "BLOCK · คำตอบสุดท้ายถูกด่าน Hermes Team Stop Gate กันไว้\n"
                + "\n".join(f"- {item}" for item in blockers)
                + "\nแก้: กลับไปทำต่อใน Git root ปัจจุบันหรือรายงาน blocker ที่พิสูจน์จากเครื่อง"
            )
            print(json.dumps({"response_text": replacement}, ensure_ascii=False))
            return 0
        print("[Hermes Team Stop Gate] ไม่อนุญาตให้ส่งคำตอบรอบนี้", file=sys.stderr)
        for item in blockers:
            print(f"- {item}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
