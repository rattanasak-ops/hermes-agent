#!/usr/bin/env python3
"""Forward the client hook payload to the installed central write gate."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys


def main() -> int:
    gate = Path.home() / ".local" / "bin" / "hermes-prewrite-gate"
    if not gate.is_file():
        print("[Hermes New Chat Gate] BLOCKED: ไม่พบ hermes-prewrite-gate", file=sys.stderr)
        return 2
    payload = sys.stdin.buffer.read()
    proc = subprocess.run([str(gate)], input=payload, env=os.environ.copy())
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
