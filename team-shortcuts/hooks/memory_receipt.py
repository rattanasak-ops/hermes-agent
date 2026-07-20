#!/usr/bin/env python3
"""Seal and verify one atomic project-memory close operation."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any

from goal_contract import CONTRACT_PATH as GOAL_CONTRACT_PATH, load_contract


SCHEMA = "hermes-memory-receipt-v1"
RECEIPT = Path(".project/memory-receipt.json")
HISTORY = Path(".project/memory-receipts")
TRANSACTION = Path(".project/memory-transaction.json")
LOCK = Path(".project/.memory-close.lock")
PROTECTED = {RECEIPT.as_posix(), TRANSACTION.as_posix(), LOCK.as_posix()}
CLOSE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
GIT_SHA = re.compile(r"^[0-9a-fA-F]{7,64}$")
IMMUTABLE_LOG_DIRS = {"session-logs", "sessions"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"ไฟล์ JSON ต้องเป็น object: {path}")
    return value


def inside(root: Path, value: str, *, source: bool) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"path ต้องอยู่ภายในโปรเจกต์: {value}")
    normalized = path.as_posix()
    prefix = ".project/scratchpad/" if source else ".project/"
    if not normalized.startswith(prefix):
        raise ValueError(f"path อยู่นอกพื้นที่ความจำที่อนุญาต: {value}")
    if not source and (
        normalized in PROTECTED or normalized.startswith(f"{HISTORY.as_posix()}/")
    ):
        raise ValueError(f"ห้ามเขียนไฟล์ควบคุมผ่าน batch: {value}")
    resolved = (root / path).resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"path หลุดจาก Git root: {value}")
    return resolved


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode())


def current_close_id(root: Path) -> str | None:
    path = root / RECEIPT
    if not path.is_file():
        return None
    try:
        return str(read_json(path).get("close_id") or "") or None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def batch_file(root: Path, value: Path) -> Path:
    """Allow prepared close batches only from the project scratchpad."""
    candidate = value.expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    scratchpad = (root / ".project/scratchpad").resolve()
    if scratchpad not in resolved.parents:
        raise ValueError("ไฟล์ batch ต้องอยู่ใน .project/scratchpad/")
    return resolved


def validate_close_id(value: object) -> str:
    close_id = str(value or "").strip()
    if not CLOSE_ID.fullmatch(close_id):
        raise ValueError("close_id ต้องเป็นอักษร ตัวเลข จุด ขีด หรือขีดล่าง ไม่เกิน 128 ตัว")
    return close_id


def prepared_writes(root: Path, batch: dict[str, Any], close_id: str) -> list[tuple[Path, bytes, str]]:
    raw = batch.get("writes")
    if not isinstance(raw, list) or not raw:
        raise ValueError("batch ต้องมี writes อย่างน้อย 1 รายการ")
    result: list[tuple[Path, bytes, str]] = []
    seen: set[Path] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("รายการ writes ผิดรูปแบบ")
        source = inside(root, str(item.get("source") or ""), source=True)
        target_text = str(item.get("target") or "")
        target = inside(root, target_text, source=False)
        if target in seen:
            raise ValueError(f"target ซ้ำ: {target_text}")
        seen.add(target)
        data = source.read_bytes()
        if close_id.encode() not in data:
            raise ValueError(f"ไฟล์ไม่มี close_id รอบนี้: {source}")
        result.append((target, data, target.relative_to(root).as_posix()))
    return result


def apply_batch(root: Path, batch_path: Path) -> dict[str, Any]:
    root = root.resolve()
    batch = read_json(batch_file(root, batch_path))
    close_id = validate_close_id(batch.get("close_id"))
    branch = str(batch.get("branch") or "").strip()
    sha = str(batch.get("sha") or "").strip()
    if not branch:
        raise ValueError("batch ไม่มี branch")
    if not GIT_SHA.fullmatch(sha):
        raise ValueError("batch ไม่มี Git SHA ที่ตรวจสอบได้")
    active_goal = None
    goal_path = root / GOAL_CONTRACT_PATH
    if goal_path.is_file():
        active_goal = load_contract(goal_path)
        if (
            str(batch.get("task_id") or "") != active_goal["task_id"]
            or str(batch.get("goal_hash") or "") != active_goal["goal_hash"]
        ):
            raise ValueError(
                "PROJECT_GOAL_DRIFT: batch ปิดแชทไม่มี task_id และ goal_hash ที่ตรงใบงานปัจจุบัน"
            )
    writes = prepared_writes(root, batch, close_id)
    lock_path = root / LOCK
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        previous = str(batch.get("previous_close_id") or "") or None
        if previous:
            validate_close_id(previous)
        if current_close_id(root) != previous:
            raise ValueError("previous_close_id ไม่ตรงกับใบรับรองล่าสุด")
        history_path = root / HISTORY / f"{close_id}.json"
        if close_id == previous or history_path.exists():
            raise ValueError("close_id ซ้ำกับรอบปิดที่มีอยู่")
        immutable = [
            relative
            for target, _, relative in writes
            if target.exists() and IMMUTABLE_LOG_DIRS.intersection(Path(relative).parts)
        ]
        if immutable:
            raise ValueError(f"session log ต้องเขียนครั้งเดียว ห้ามทับ: {', '.join(immutable)}")
        transaction = {
            "schema": SCHEMA, "close_id": close_id,
            "started_ns": time.time_ns(), "targets": [item[2] for item in writes],
        }
        atomic_json(root / TRANSACTION, transaction)
        backups: list[tuple[Path, bytes | None]] = []
        try:
            for target, data, _ in writes:
                backups.append((target, target.read_bytes() if target.exists() else None))
                atomic_bytes(target, data)
            created_ns = time.time_ns()
            files = [
                {
                    "path": relative,
                    "sha256": digest(target.read_bytes()),
                    "mtime_ns": target.stat().st_mtime_ns,
                }
                for target, _, relative in writes
            ]
            receipt = {
                "schema": SCHEMA,
                "close_id": close_id,
                "previous_close_id": previous,
                "git_root": str(root),
                "branch": branch,
                "sha": sha,
                "writer": str(batch.get("writer") or "unknown"),
                "started_at": str(batch.get("started_at") or ""),
                "closed_at": str(batch.get("closed_at") or ""),
                "created_ns": created_ns,
                "files": files,
            }
            if active_goal:
                receipt.update(
                    {
                        "task_id": active_goal["task_id"],
                        "plan_id": active_goal["plan_id"],
                        "goal_hash": active_goal["goal_hash"],
                    }
                )
            atomic_json(history_path, receipt)
            atomic_json(root / RECEIPT, receipt)
            (root / TRANSACTION).unlink(missing_ok=True)
            return {"ok": True, "close_id": close_id, "files": len(files), "receipt": str(root / RECEIPT)}
        except Exception:
            for target, previous_data in reversed(backups):
                if previous_data is None:
                    target.unlink(missing_ok=True)
                else:
                    atomic_bytes(target, previous_data)
            history_path.unlink(missing_ok=True)
            (root / TRANSACTION).unlink(missing_ok=True)
            raise


def verify_receipt(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if (root / TRANSACTION).exists():
        return {"ok": False, "code": "PROJECT_MEMORY_DRIFT", "reason": "พบการเขียนความจำที่ยังไม่ปิดรอบ", "files": [TRANSACTION.as_posix()]}
    receipt_path = root / RECEIPT
    if not receipt_path.is_file():
        return {"ok": False, "code": "PROJECT_MEMORY_RECEIPT_MISSING", "reason": "ยังไม่มีใบรับรองรอบปิด", "files": []}
    try:
        receipt = read_json(receipt_path)
        close_id = validate_close_id(receipt.get("close_id"))
        if receipt.get("schema") != SCHEMA:
            raise ValueError("รูปแบบใบรับรองไม่ตรง")
        if Path(str(receipt.get("git_root") or "")).resolve() != root:
            raise ValueError("Git root ในใบรับรองไม่ตรงกับพื้นที่ปัจจุบัน")
        goal_path = root / GOAL_CONTRACT_PATH
        if goal_path.is_file():
            active_goal = load_contract(goal_path)
            if (
                receipt.get("task_id") != active_goal["task_id"]
                or receipt.get("plan_id") != active_goal["plan_id"]
                or receipt.get("goal_hash") != active_goal["goal_hash"]
            ):
                return {
                    "ok": False,
                    "code": "PROJECT_GOAL_DRIFT",
                    "reason": "task_id, plan_id หรือ goal_hash ในใบรับรองไม่ตรงใบงานปัจจุบัน",
                    "files": [],
                }
        if not str(receipt.get("branch") or "").strip() or not GIT_SHA.fullmatch(
            str(receipt.get("sha") or "").strip()
        ):
            raise ValueError("branch หรือ Git SHA ในใบรับรองไม่ครบ")
        history_current = root / HISTORY / f"{close_id}.json"
        if not history_current.is_file() or read_json(history_current) != receipt:
            raise ValueError("ใบรับรองล่าสุดไม่ตรงกับประวัติรอบปิด")
        changed: list[str] = []
        created_ns = int(receipt.get("created_ns") or 0)
        files = receipt.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("ใบรับรองไม่มีรายการไฟล์")
        for item in files:
            if not isinstance(item, dict):
                raise ValueError("รายการไฟล์ในใบรับรองผิดรูปแบบ")
            relative = str(item.get("path") or "")
            target = inside(root, relative, source=False)
            if not target.is_file() or digest(target.read_bytes()) != item.get("sha256"):
                changed.append(relative)
            elif target.stat().st_mtime_ns > created_ns:
                changed.append(relative)
        seen: set[str] = set()
        cursor: dict[str, Any] | None = receipt
        while cursor:
            cursor_close_id = validate_close_id(cursor.get("close_id"))
            if cursor.get("schema") != SCHEMA:
                raise ValueError("schema ในสายใบรับรองไม่ตรง")
            if cursor_close_id in seen:
                raise ValueError("สาย previous_close_id วนกลับ")
            seen.add(cursor_close_id)
            previous = str(cursor.get("previous_close_id") or "")
            if not previous:
                break
            validate_close_id(previous)
            previous_path = root / HISTORY / f"{previous}.json"
            if not previous_path.is_file():
                raise ValueError(f"ไม่พบใบรับรองก่อนหน้า: {previous}")
            cursor = read_json(previous_path)
            if str(cursor.get("close_id") or "") != previous:
                raise ValueError(f"รหัสใบรับรองก่อนหน้าไม่ตรงชื่อไฟล์: {previous}")
        if changed:
            return {"ok": False, "code": "PROJECT_MEMORY_DRIFT", "reason": "ไฟล์ไม่ตรงใบรับรอง", "files": sorted(set(changed))}
        return {"ok": True, "code": "MEMORY_RECEIPT_OK", "close_id": receipt["close_id"], "files": len(files)}
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        return {"ok": False, "code": "PROJECT_MEMORY_DRIFT", "reason": str(exc), "files": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=".")
    commands = parser.add_subparsers(dest="command", required=True)
    apply_cmd = commands.add_parser("apply-batch")
    apply_cmd.add_argument("--batch", required=True)
    commands.add_parser("verify")
    args = parser.parse_args(argv)
    root = Path(args.cwd).expanduser().resolve()
    try:
        result = apply_batch(root, Path(args.batch)) if args.command == "apply-batch" else verify_receipt(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"ok": False, "code": "PROJECT_MEMORY_WRITE_BLOCKED", "reason": str(exc), "files": []}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
