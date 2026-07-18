#!/usr/bin/env python3
"""Forward every client hook payload to the current-workspace gate.

ชื่อไฟล์เดิมคงไว้เพื่อให้เครื่องที่ติดตั้งแล้วอัปเดตได้โดยไม่เกิด Hook ซ้ำ
"""

from __future__ import annotations

from pathlib import Path
import os
import json
import subprocess
import sys


def main() -> int:
    gate = Path.home() / ".local" / "bin" / "hermes-prewrite-gate"
    if not gate.is_file():
        print("[Hermes New Chat Gate] BLOCKED: ไม่พบ hermes-prewrite-gate", file=sys.stderr)
        return 2
    payload = sys.stdin.buffer.read()
    proc = subprocess.run(
        [str(gate)], input=payload, env=os.environ.copy(), capture_output=True
    )
    if proc.stderr:
        sys.stderr.buffer.write(proc.stderr)
    if proc.returncode != 0:
        reason = proc.stderr.decode("utf-8", errors="replace").strip() or "Blocked by Hermes Current Workspace Gate"
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
