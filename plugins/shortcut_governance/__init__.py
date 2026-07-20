"""Hermes Shortcut governance plugin."""

from __future__ import annotations

import json

from .cli import from_slash, register_cli, shortcut_incident_command
from .store import ShortcutIncidentStore


def _record_handler(args: dict, **_kwargs) -> str:
    try:
        result = ShortcutIncidentStore(args.get("store_path") or None).record(args)
        return json.dumps({"ok": True, **result}, ensure_ascii=False)
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


def _status_handler(args: dict, **_kwargs) -> str:
    store = ShortcutIncidentStore(args.get("store_path") or None)
    rows = store.list(args.get("status") or None)
    return json.dumps({"ok": True, "count": len(rows), "incidents": rows}, ensure_ascii=False)


def register(ctx) -> None:
    ctx.register_cli_command(
        name="shortcut-incident",
        help="บันทึกและติดตามปัญหา Shortcut โดยแก้ที่ Hermes Agent เท่านั้น",
        setup_fn=register_cli,
        handler_fn=shortcut_incident_command,
        description="นับปัญหาเดิมข้ามโปรเจกต์และสร้าง Prompt ซ่อมกลางเมื่อเกิดครั้งที่ 4",
    )
    ctx.register_command(
        "shortcut-incidents",
        from_slash,
        description="สรุปเหตุ Shortcut ที่รอการแก้กลาง",
    )
    ctx.register_tool(
        name="shortcut_incident_record",
        toolset="shortcut_governance",
        schema={
            "name": "shortcut_incident_record",
            "description": "บันทึกปัญหา Shortcut โดยไม่แก้ Shortcut ในโปรเจกต์ผู้แจ้ง",
            "parameters": {
                "type": "object",
                "properties": {
                    "shortcut": {"type": "string"},
                    "stage": {"type": "string"},
                    "symptom": {"type": "string"},
                    "expected": {"type": "string"},
                    "actual": {"type": "string"},
                    "project": {"type": "string"},
                    "machine": {"type": "string"},
                    "git_root": {"type": "string"},
                    "branch": {"type": "string"},
                    "git_sha": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "source": {"type": "string"},
                },
                "required": [
                    "shortcut", "stage", "symptom", "expected", "actual", "project", "machine"
                ],
            },
        },
        handler=_record_handler,
        description="Shortcut incident recorder",
        emoji="🧭",
    )
    ctx.register_tool(
        name="shortcut_incident_status",
        toolset="shortcut_governance",
        schema={
            "name": "shortcut_incident_status",
            "description": "ดูเหตุ Shortcut และจำนวนครั้งสะสม",
            "parameters": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
            },
        },
        handler=_status_handler,
        description="Shortcut incident status",
        emoji="📋",
    )
