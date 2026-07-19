#!/usr/bin/env python3
"""Self-test the three response gates installed on a team machine."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


HOME = Path.home()
CLAUDE_HOOKS = HOME / ".claude" / "hooks"
CODEX_HOOKS = HOME / ".codex" / "hooks"


def call(path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    if not path.is_file():
        return subprocess.CompletedProcess(
            args=[str(path)], returncode=127, stdout="", stderr="missing"
        )
    return subprocess.run(
        [sys.executable, str(path)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )


def transcript(path: Path, final: str) -> None:
    rows = [
        {
            "type": "user",
            "message": {"content": [{"type": "text", "text": "- แก้ระบบ\n- เพิ่ม test"}]},
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "apply_patch",
                        "input": {"file_path": "/tmp/app.py"},
                    }
                ]
            },
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": final}]},
        },
    ]
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    results: list[dict[str, object]] = []
    plain = call(
        CLAUDE_HOOKS / "validate-thai-language.py",
        {"last_assistant_message": "leverage utilize synergy seamless robust scalable optimize"},
    )
    results.append(
        {"gate": "plain_language", "ok": plain.returncode == 2, "exit": plain.returncode}
    )

    with tempfile.TemporaryDirectory() as tmp:
        review_file = Path(tmp) / "review.jsonl"
        transcript(review_file, "เสร็จแล้วครับ")
        review = call(
            CODEX_HOOKS / "enforce-codex-review.py",
            {
                "transcript_path": str(review_file),
                "last_assistant_message": "เสร็จแล้วครับ",
            },
        )
        results.append(
            {
                "gate": "independent_review",
                "ok": review.returncode == 2,
                "exit": review.returncode,
            }
        )

        evidence_file = Path(tmp) / "evidence.jsonl"
        transcript(evidence_file, "เสร็จครบ 100% แล้วครับ")
        evidence = call(
            CLAUDE_HOOKS / "enforce-prompt-evidence.py",
            {
                "transcript_path": str(evidence_file),
                "last_assistant_message": "เสร็จครบ 100% แล้วครับ",
            },
        )
        results.append(
            {
                "gate": "prompt_evidence",
                "ok": evidence.returncode == 2,
                "exit": evidence.returncode,
            }
        )

    ok = all(bool(row["ok"]) for row in results)
    print(json.dumps({"ok": ok, "gates": results}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
