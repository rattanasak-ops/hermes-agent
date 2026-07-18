from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_new_chat():
    path = ROOT / "scripts/new-chat/hermes_new_chat.py"
    spec = importlib.util.spec_from_file_location("hermes_new_chat", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


NEW_CHAT = load_new_chat()


def test_status_blocks_expired_permit_even_when_worktree_is_ready(
    tmp_path: Path, monkeypatch,
) -> None:
    state_file = tmp_path / "session.json"
    state_file.write_text(
        json.dumps(
            {
                "task_id": "TASK-1",
                "status": "NEW_CHAT_READY",
                "wtl": "WTL_READY",
                "registry": "",
                "permit_expires_at": (
                    dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
                ).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(NEW_CHAT, "state_path", lambda task_id: state_file)
    monkeypatch.setattr(NEW_CHAT, "find_tool", lambda name: name)
    monkeypatch.setattr(
        NEW_CHAT,
        "run_json",
        lambda command, env: {"ok": True, "decision": "WTL_READY"},
    )

    result = NEW_CHAT.status_task(argparse.Namespace(task_id="TASK-1"))

    assert result["wtl"] == "WTL_READY"
    assert result["status"] == "NEW_CHAT_BLOCKED"
