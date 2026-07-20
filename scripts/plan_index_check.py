#!/usr/bin/env python3
"""Check that the central plan index has one active plan and honest progress."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


ACTIVE = re.compile(r"(?m)^active_plan_id:\s*([A-Za-z0-9_-]+)\s*$")
PLAN_ID = re.compile(r"(?im)^\s*>?[^\n]*?\bplan_id(?:\*\*)?\s*:\s*([A-Za-z0-9_-]+)\b")
PROGRESS = re.compile(r"(\d+)\s*/\s*(\d+)\s*=\s*(\d+(?:\.\d+)?)%")


def table_rows(text: str) -> list[dict[str, str]]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or "plan_id" in line or re.match(r"^\|[-:|]+\|$", line.replace(" ", "")):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            continue
        rows.append(
            {
                "plan_id": cells[0],
                "file": cells[1].strip("`"),
                "lifecycle": cells[2],
                "progress": cells[3],
                "evidence": cells[4],
            }
        )
    return rows


def progress_errors(value: str, label: str) -> list[str]:
    matches = list(PROGRESS.finditer(value))
    if not matches:
        return [f"{label} ไม่มี N/M = เปอร์เซ็นต์"]
    errors = []
    for match in matches:
        done, total, percent = int(match.group(1)), int(match.group(2)), float(match.group(3))
        if total <= 0 or done > total:
            errors.append(f"{label} มี N/M ผิดรูปแบบ: {match.group(0)}")
            continue
        expected = round(done * 100 / total, 1)
        if abs(expected - percent) > 0.11:
            errors.append(f"{label} เปอร์เซ็นต์ไม่ตรงหลักฐาน: {match.group(0)} ควรเป็น {expected}%")
    return errors


def check(root: Path, index_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    index = (index_path or root / ".project/plan-index.md").resolve()
    text = index.read_text(encoding="utf-8")
    active_match = ACTIVE.search(text)
    active_id = active_match.group(1) if active_match else ""
    rows = table_rows(text)
    errors: list[str] = []
    if not active_id:
        errors.append("ดัชนีไม่มี active_plan_id")
    ids = [row["plan_id"] for row in rows]
    files = [row["file"] for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("ดัชนีมี plan_id ซ้ำ")
    if len(files) != len(set(files)):
        errors.append("ดัชนีให้หลาย plan_id ใช้ไฟล์เดียวกัน")
    active_rows = [row for row in rows if row["lifecycle"] == "active"]
    if len(active_rows) != 1:
        errors.append(f"ต้องมีแผน active 1 รายการ แต่พบ {len(active_rows)}")
    elif active_rows[0]["plan_id"] != active_id:
        errors.append("active_plan_id ไม่ตรงกับแถว lifecycle active")

    for row in rows:
        plan = root / row["file"]
        if not plan.is_file():
            errors.append(f"ไม่พบไฟล์แผน {row['file']}")
            continue
        plan_text = plan.read_text(encoding="utf-8")
        top = "\n".join(plan_text.splitlines()[:12])
        found = PLAN_ID.search(top)
        if not found or found.group(1) != row["plan_id"]:
            errors.append(f"plan_id ใน {row['file']} ไม่ตรงกับดัชนี")
        errors.extend(progress_errors(row["progress"], f"ดัชนี {row['plan_id']}"))
        errors.extend(progress_errors(top, f"ไฟล์ {row['plan_id']}"))
        if not row["evidence"].strip():
            errors.append(f"ดัชนี {row['plan_id']} ไม่มีหลักฐาน")
    return {
        "ok": not errors,
        "active_plan_id": active_id,
        "active_count": len(active_rows),
        "plans": len(rows),
        "plans_checked": len(rows) - sum(1 for row in rows if not (root / row["file"]).is_file()),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--index", default="")
    args = parser.parse_args()
    try:
        result = check(Path(args.cwd), Path(args.index) if args.index else None)
    except (OSError, ValueError) as exc:
        result = {"ok": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
