"""Command-line surface for Shortcut incident reporting."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

from .store import ShortcutIncidentStore


def _git(cwd: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-c", f"safe.directory={cwd}", *args],
            cwd=cwd,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def register_cli(parser: argparse.ArgumentParser) -> None:
    subs = parser.add_subparsers(dest="shortcut_incident_action")

    record = subs.add_parser("record", help="บันทึกปัญหา Shortcut โดยไม่แก้ไฟล์กลาง")
    record.add_argument("--shortcut", required=True)
    record.add_argument("--stage", required=True)
    record.add_argument("--symptom", required=True)
    record.add_argument("--expected", required=True)
    record.add_argument("--actual", required=True)
    record.add_argument("--project", default="")
    record.add_argument("--machine", default="")
    record.add_argument("--cwd", default=".")
    record.add_argument("--evidence", action="append", default=[])
    record.add_argument("--source", default="cli")
    record.add_argument("--store-path", default="")
    record.add_argument("--json", action="store_true")

    listing = subs.add_parser("list", help="แสดงเหตุ Shortcut")
    listing.add_argument("--status", default="")
    listing.add_argument("--store-path", default="")
    listing.add_argument("--json", action="store_true")

    show = subs.add_parser("show", help="แสดงเหตุหนึ่งรายการ")
    show.add_argument("incident_id")
    show.add_argument("--store-path", default="")
    show.add_argument("--json", action="store_true")

    close = subs.add_parser("close", help="ปิดเหตุหลังรุ่นใหม่กระจายครบ")
    close.add_argument("incident_id")
    close.add_argument("--version", required=True)
    close.add_argument("--evidence", action="append", default=[])
    close.add_argument("--store-path", default="")
    close.add_argument("--json", action="store_true")

    parser.set_defaults(func=shortcut_incident_command)


def _store(args: argparse.Namespace) -> ShortcutIncidentStore:
    return ShortcutIncidentStore(getattr(args, "store_path", "") or None)


def _print(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, list):
        for row in payload:
            print(
                f"{row['incident_id']} · {row['shortcut']} · "
                f"{row['occurrence_count']} ครั้ง · {row['status']}"
            )
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def shortcut_incident_command(args: argparse.Namespace) -> int:
    action = getattr(args, "shortcut_incident_action", None)
    if not action:
        print("ใช้: hermes shortcut-incident {record|list|show|close}")
        return 2
    try:
        store = _store(args)
        if action == "record":
            cwd = Path(args.cwd).expanduser().resolve()
            root_text = _git(cwd, "rev-parse", "--show-toplevel")
            root = Path(root_text) if root_text else cwd
            payload = store.record(
                {
                    "shortcut": args.shortcut,
                    "stage": args.stage,
                    "symptom": args.symptom,
                    "expected": args.expected,
                    "actual": args.actual,
                    "project": args.project or root.name,
                    "machine": args.machine or platform.node() or "unknown",
                    "git_root": str(root),
                    "branch": _git(root, "branch", "--show-current"),
                    "git_sha": _git(root, "rev-parse", "HEAD"),
                    "evidence": args.evidence,
                    "source": args.source,
                }
            )
        elif action == "list":
            payload = store.list(args.status or None)
        elif action == "show":
            payload = store.get(args.incident_id)
        else:
            payload = store.close(args.incident_id, args.version, args.evidence)
        _print(payload, getattr(args, "json", False))
        return 0
    except (KeyError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


def from_slash(raw_args: str) -> str:
    rows = ShortcutIncidentStore().list()
    escalated = [row for row in rows if row["status"] == "escalate_to_hermes"]
    return (
        f"เหตุ Shortcut ทั้งหมด {len(rows)} รายการ · "
        f"รอแก้ที่ Hermes Agent {len(escalated)} รายการ"
    )
