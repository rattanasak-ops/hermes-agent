#!/usr/bin/env python3
"""Spec interview evidence recorder."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterator


SCHEMA = "hermes-spec-interview-evidence-v1"
PLAN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}$")
CHANNEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,80}$")
DIFF_HASH = re.compile(r"^[a-f0-9]{64}$")


def fail(message: str, code: int = 2) -> int:
    print(json.dumps({"ok": False, "reason_human": message}, ensure_ascii=False))
    return code


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes").expanduser().resolve()


def git_root(path: Path) -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ValueError("repo ต้องอยู่ใต้ Git root")
    return Path(proc.stdout.strip()).resolve()


def clean_plan_id(value: str) -> str:
    if not PLAN_ID.fullmatch(value):
        raise ValueError("plan_id ผิดรูปแบบ")
    return value


def clean_channel(value: str) -> str:
    if not CHANNEL.fullmatch(value):
        raise ValueError("channel ผิดรูปแบบ")
    return value


def repo_key(root: Path) -> str:
    return sha256_text(str(root))


def evidence_dir(repo: Path, plan_id: str) -> Path:
    root = git_root(repo)
    return hermes_home() / "spec-evidence" / repo_key(root) / clean_plan_id(plan_id)


@contextmanager
def locked(directory: Path) -> Iterator[None]:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = directory / ".lock"
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def record_files(directory: Path) -> list[Path]:
    records = directory / "records"
    if not records.exists():
        return []
    return sorted(path for path in records.glob("*.json") if path.is_file())


def clean_diff_hash(value: str) -> str:
    lowered = value.lower()
    if not DIFF_HASH.fullmatch(lowered):
        raise ValueError("diff hash ผิดรูปแบบ")
    return lowered


def read_record(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def record_hash(record: dict) -> str:
    body = dict(record)
    body.pop("record_hash", None)
    return sha256_bytes(canonical(body))


def chain_head(directory: Path) -> tuple[int, str]:
    previous = ""
    count = 0
    for path in record_files(directory):
        record = read_record(path)
        expected = record_hash(record)
        if record.get("record_hash") != expected:
            raise ValueError(f"record hash ไม่ตรง: {path.name}")
        if record.get("prev_hash") != previous:
            raise ValueError(f"hash chain ขาดที่ {path.name}")
        previous = expected
        count += 1
    return count, previous


def load_owner_prompt_from_stdin() -> str:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(f"อ่านข้อความเจ้าของจาก hook ไม่ได้: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("hook payload ต้องเป็น JSON object")
    for key in ("user_message", "prompt", "user_prompt", "last_user_message", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            text = value.get("text") or value.get("content")
            if isinstance(text, str) and text.strip():
                return text.strip()
    raise ValueError("ไม่พบข้อความเจ้าของใน hook payload")


def write_record(repo: Path, plan_id: str, kind: str, channel: str, text: str, extra: dict | None = None) -> dict:
    root = git_root(repo)
    directory = evidence_dir(root, plan_id)
    with locked(directory):
        count, previous = chain_head(directory)
        record = {
            "schema": SCHEMA,
            "repo_realpath": str(root),
            "repo_hash": repo_key(root),
            "plan_id": clean_plan_id(plan_id),
            "kind": kind,
            "channel": clean_channel(channel),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "text": text,
            "text_hash": sha256_text(text),
            "prev_hash": previous,
        }
        if extra:
            record.update(extra)
        digest = record_hash(record)
        record["record_hash"] = digest
        records = directory / "records"
        records.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = records / f"{count + 1:06d}-{digest[:12]}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        path.chmod(0o600)
        return {"path": str(path), "record_hash": digest, "prev_hash": previous, "count": count + 1}


def file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def manifest_payload(
    repo: Path,
    plan_id: str,
    spec: Path,
    criteria: Path | None = None,
    chain_count: int | None = None,
    chain_head_value: str | None = None,
) -> dict:
    root = git_root(repo)
    directory = evidence_dir(root, plan_id)
    count, head = chain_head(directory)
    if chain_count is not None:
        count = chain_count
    if chain_head_value is not None:
        head = chain_head_value
    files = [{"role": "spec", "path": str(spec.resolve()), "sha256": file_hash(spec)}]
    if criteria is not None:
        files.append({"role": "criteria", "path": str(criteria.resolve()), "sha256": file_hash(criteria)})
    payload = {
        "schema": "hermes-spec-interview-manifest-v1",
        "repo_realpath": str(root),
        "repo_hash": repo_key(root),
        "plan_id": clean_plan_id(plan_id),
        "chain_count": count,
        "chain_head": head,
        "files": files,
    }
    payload["manifest_hash"] = sha256_bytes(canonical(payload))
    return payload


def approve(repo: Path, plan_id: str, spec: Path, channel: str, owner_message: str) -> dict:
    manifest = manifest_payload(repo, plan_id, spec)
    result = write_record(
        repo,
        plan_id,
        "approval",
        channel,
        owner_message,
        {"manifest_hash": manifest["manifest_hash"], "approved_by": "owner"},
    )
    return {**result, "manifest_hash": manifest["manifest_hash"]}


def waiver_dir(repo: Path, plan_id: str) -> Path:
    return evidence_dir(repo, plan_id) / "waivers"


def waive(repo: Path, plan_id: str, diff_hash: str, channel: str, owner_message: str) -> dict:
    root = git_root(repo)
    directory = evidence_dir(root, plan_id)
    digest = clean_diff_hash(diff_hash)
    with locked(directory):
        waivers = waiver_dir(root, plan_id)
        waivers.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = waivers / f"{digest}.json"
        if path.exists():
            raise ValueError("waiver นี้ถูกจองไว้แล้ว")
        payload = {
            "schema": "hermes-spec-waiver-v1",
            "repo_realpath": str(root),
            "repo_hash": repo_key(root),
            "plan_id": clean_plan_id(plan_id),
            "diff_hash": digest,
            "channel": clean_channel(channel),
            "reason": owner_message,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "used_at_utc": None,
        }
        payload["waiver_hash"] = sha256_bytes(canonical(payload))
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        path.chmod(0o600)
        return {"path": str(path), "diff_hash": digest, "waiver_hash": payload["waiver_hash"]}


def consume_waiver(repo: Path, plan_id: str, diff_hash: str) -> dict:
    root = git_root(repo)
    directory = evidence_dir(root, plan_id)
    digest = clean_diff_hash(diff_hash)
    with locked(directory):
        path = waiver_dir(root, plan_id) / f"{digest}.json"
        if not path.exists():
            raise ValueError("ไม่พบ waiver สำหรับ diff นี้")
        payload = read_record(path)
        expected = dict(payload)
        stored_hash = expected.pop("waiver_hash", None)
        if stored_hash != sha256_bytes(canonical(expected)):
            raise ValueError("waiver hash ไม่ตรง")
        if payload.get("used_at_utc"):
            raise ValueError("waiver นี้ถูกใช้แล้ว")
        payload["used_at_utc"] = datetime.now(timezone.utc).isoformat()
        new_body = dict(payload)
        new_body.pop("waiver_hash", None)
        payload["waiver_hash"] = sha256_bytes(canonical(new_body))
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return {"path": str(path), "diff_hash": digest, "used": True}


def verify(repo: Path, plan_id: str, spec: Path | None = None) -> dict:
    root = git_root(repo)
    directory = evidence_dir(root, plan_id)
    count, head = chain_head(directory)
    result = {
        "ok": True,
        "repo_realpath": str(root),
        "plan_id": clean_plan_id(plan_id),
        "chain_count": count,
        "chain_head": head,
    }
    if spec is not None:
        current = manifest_payload(root, plan_id, spec)
        approvals = []
        for index, path in enumerate(record_files(directory)):
            record = read_record(path)
            if record.get("kind") == "approval":
                approval_manifest = manifest_payload(
                    root,
                    plan_id,
                    spec,
                    chain_count=index,
                    chain_head_value=record.get("prev_hash") or "",
                )
                approvals.append((record, approval_manifest))
        result["manifest_hash"] = current["manifest_hash"]
        result["approved_manifest_match"] = any(
            record.get("manifest_hash") == approval_manifest["manifest_hash"]
            for record, approval_manifest in approvals
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record and verify spec interview evidence.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("record-question", "record-answer", "approve", "manifest", "verify", "waive", "consume-waiver"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--repo", required=True)
        cmd.add_argument("--plan-id", required=True)
    sub.choices["record-question"].add_argument("--question", required=True)
    sub.choices["record-question"].add_argument("--channel", default="ai-chat")
    sub.choices["record-answer"].add_argument("--from-hook", action="store_true", required=True)
    sub.choices["record-answer"].add_argument("--channel", default="owner-chat")
    sub.choices["approve"].add_argument("--spec", required=True)
    sub.choices["approve"].add_argument("--from-hook", action="store_true", required=True)
    sub.choices["approve"].add_argument("--channel", default="owner-chat")
    sub.choices["manifest"].add_argument("--spec", required=True)
    sub.choices["manifest"].add_argument("--criteria")
    sub.choices["verify"].add_argument("--spec")
    sub.choices["waive"].add_argument("--diff-hash", required=True)
    sub.choices["waive"].add_argument("--from-hook", action="store_true", required=True)
    sub.choices["waive"].add_argument("--channel", default="owner-chat")
    sub.choices["consume-waiver"].add_argument("--diff-hash", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        repo = Path(args.repo).expanduser()
        plan_id = clean_plan_id(args.plan_id)
        if args.command == "record-question":
            result = write_record(repo, plan_id, "question", args.channel, args.question)
        elif args.command == "record-answer":
            result = write_record(repo, plan_id, "answer", args.channel, load_owner_prompt_from_stdin())
        elif args.command == "approve":
            result = approve(repo, plan_id, Path(args.spec).expanduser(), args.channel, load_owner_prompt_from_stdin())
        elif args.command == "manifest":
            result = manifest_payload(
                repo,
                plan_id,
                Path(args.spec).expanduser(),
                Path(args.criteria).expanduser() if args.criteria else None,
            )
        elif args.command == "verify":
            result = verify(repo, plan_id, Path(args.spec).expanduser() if args.spec else None)
        elif args.command == "waive":
            result = waive(repo, plan_id, args.diff_hash, args.channel, load_owner_prompt_from_stdin())
        elif args.command == "consume-waiver":
            result = consume_waiver(repo, plan_id, args.diff_hash)
        else:
            return fail("คำสั่งไม่รองรับ")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return fail(str(exc))
    emit({"ok": True, **result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
