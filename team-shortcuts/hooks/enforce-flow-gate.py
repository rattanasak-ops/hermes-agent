#!/usr/bin/env python3
"""Block Claude Code writes that skip the Migrate Web flow."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}
MW_MARKER = Path(".work/profile.yaml")
SHELL_WRITE_RE = re.compile(r"(?:^|\s)(?:tee|cp|mv|sed\s+-[^\n]*i)|(?<!\d)>{1,2}")
REDIRECT_RE = re.compile(
    r"(?<!\d)>{1,2}\s*(?P<path>\"[^\"]+\"|'[^']+'|[^\s|;&]+)"
)

# ── Flow Station Gate: บังคับ owner ยืนยันในแชทจริง ก่อน AI โยนงานสร้างหน้า ──
# ปฐมเหตุ 2026-07-15: AI ข้าม M0/M2/M3.5 (คุยกับ owner) แล้วสั่ง codex/relay สร้างทั้งหน้า
# ด่านเดิมพึ่งไฟล์ .flow-state ที่ AI เขียนเอง → AI พิมพ์ owner_ok ปลอมได้
# เปลี่ยนมาจับ "owner ยืนยันจริง" จากบันทึกแชท (transcript) ที่ AI เขียนทับไม่ได้
AI_DELEGATE_RE = re.compile(
    r"(?:^|[\s;&|(])(?:"
    r"codex\s+e(?:xec)?\b"              # codex exec / codex e
    r"|relay[-_]call"                   # relay-call.py
    r"|grok\b[^\n]*?(?:\bexec\b|--?p(?:rompt)?\b)"    # grok เขียนโค้ด
    r"|gemini\b[^\n]*?(?:--?p(?:rompt)?\b)"           # gemini เขียนโค้ด
    r")",
    re.IGNORECASE,
)
REQUIRED_STATIONS = ("M0", "M2", "M3.5")
# owner ยืนยันราย station = ข้อความสั้น + คำอนุมัติ "ติดกับ" ชื่อ station
# (กัน false positive: owner paste เนื้อหายาวที่บังเอิญมี station + คำ "ผ่าน/ok" กระจายอยู่)
_APPROVE_WORD = r"(?:\bok\b|โอเค|ผ่าน|อนุมัติ|ยืนยัน|เอาเลย|\bใช่\b|approve)"
_STATION_TOKEN = r"(M0|M2|M3[._ ]?5)"
_STATION_APPROVE_RE = re.compile(
    rf"(?i){_APPROVE_WORD}\s*[:：\-]?\s*{_STATION_TOKEN}\b"
    rf"|{_STATION_TOKEN}\s*[:：\-]?\s*{_APPROVE_WORD}",
    re.IGNORECASE,
)
_MAX_APPROVAL_LEN = 200  # การยืนยันราย station สั้น · ข้อความยาวกว่านี้ = paste ไม่นับ


def _absolute(path: Path, cwd: Path) -> Path:
    expanded = path.expanduser()
    return Path(os.path.abspath(str(expanded if expanded.is_absolute() else cwd / expanded)))


def find_project_root(path: Path) -> Optional[Path]:
    """Find the nearest MW root at or above a path."""
    resolved = Path(os.path.abspath(str(path.expanduser())))
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if (candidate / MW_MARKER).is_file():
            return candidate
    return None


def _unquote(value: str) -> str:
    try:
        parts = shlex.split(value)
    except ValueError:
        return value.strip("\"'")
    return parts[0] if len(parts) == 1 else value.strip("\"'")


def _shell_tokens(command: str) -> List[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return []


def _command_destinations(tokens: Sequence[str]) -> List[str]:
    destinations: List[str] = []
    for index, token in enumerate(tokens):
        name = Path(token).name
        if name not in {"cp", "mv", "tee", "sed"}:
            continue
        tail = list(tokens[index + 1 :])
        if name in {"cp", "mv"}:
            values = [value for value in tail if not value.startswith("-")]
            if len(values) >= 2:
                destinations.append(values[-1])
        elif name == "tee":
            values = [value for value in tail if not value.startswith("-")]
            if values:
                destinations.extend(values)
        elif name == "sed" and any(
            value == "-i" or (value.startswith("-") and "i" in value[1:])
            for value in tail
        ):
            values = [value for value in tail if not value.startswith("-")]
            if len(values) >= 2:
                destinations.append(values[-1])
    return destinations


def extract_bash_targets(command: str) -> Tuple[List[str], bool, bool]:
    """Return best-effort write targets, whether it writes, and complexity."""
    redirect_targets = [_unquote(match.group("path")) for match in REDIRECT_RE.finditer(command)]
    tokens = _shell_tokens(command)
    command_targets = _command_destinations(tokens) if tokens else []
    targets = list(dict.fromkeys(redirect_targets + command_targets))
    has_write = bool(SHELL_WRITE_RE.search(command))
    separators = len(re.findall(r"&&|;", command))
    complex_write = has_write and (
        (separators > 0 and (len(redirect_targets) > 0 or len(command_targets) > 0))
        or (len(redirect_targets) > 1)
        or (not tokens and not targets)
    )
    return targets, has_write, complex_write


def find_flow_gate(project_root: Path) -> Optional[Path]:
    candidates = (
        project_root / "scripts/mw/flow_gate.py",
        Path(__file__).resolve().parent.parent / "payload/scripts/mw/flow_gate.py",
        Path.home() / ".hermes/mw/flow_gate.py",
    )
    return next((path for path in candidates if path.is_file()), None)


def _mw_registry_files() -> List[Path]:
    """ไฟล์ทะเบียนพื้นที่โปรเจกต์ Migrate Web (portable · ตามลำดับความสำคัญ)."""
    files: List[Path] = []
    env = os.environ.get("MW_RELAY_REQUIRED_LIST")
    if env:
        files.append(Path(env).expanduser())
    files.append(Path.home() / ".hermes/mw/relay-required-projects.txt")
    files.append(Path.home() / ".claude/relay-required-projects.txt")
    return files


def _mw_registry_roots() -> List[str]:
    roots: List[str] = []
    for path in _mw_registry_files():
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                roots.append(os.path.realpath(os.path.expanduser(line)))
    return roots


def _cwd_in_mw_registry(cwd: Path) -> bool:
    resolved = os.path.realpath(str(cwd))
    for root in _mw_registry_roots():
        if resolved == root or resolved.startswith(root + os.sep):
            return True
    return False


def _normalize_station(token: str) -> Optional[str]:
    compact = re.sub(r"[._ ]", "", token).upper()
    if compact in {"M35"}:
        return "M3.5"
    if compact == "M2":
        return "M2"
    if compact == "M0":
        return "M0"
    return None


def _is_owner_human(record: Dict[str, object]) -> bool:
    """True เฉพาะข้อความที่ owner พิมพ์เองจริง (ไม่ใช่ hook/system แทรก)."""
    if record.get("type") != "user":
        return False
    message = record.get("message")
    if not isinstance(message, dict) or message.get("role") != "user":
        return False
    if not isinstance(message.get("content"), str):
        return False
    origin = record.get("origin")
    return isinstance(origin, dict) and origin.get("kind") == "human"


def owner_approved_stations(transcript_path: str) -> set:
    """อ่านบันทึกแชท คืน set ของ station ที่ owner พิมพ์ยืนยันจริง (AI ปลอมไม่ได้)."""
    approved: set = set()
    with open(transcript_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict) or not _is_owner_human(record):
                continue
            content = record["message"]["content"]
            # การยืนยันราย station เป็นข้อความสั้น เจตนาชัด · paste ยาว = ไม่นับ
            if len(content) > _MAX_APPROVAL_LEN:
                continue
            for match in _STATION_APPROVE_RE.finditer(content):
                token = match.group(1) or match.group(2)
                station = _normalize_station(token) if token else None
                if station:
                    approved.add(station)
    return approved


def _guard_delegation(
    command: str, cwd: Path, transcript_path: Optional[str]
) -> Optional[str]:
    """บล็อกการสั่ง AI สร้างหน้า ถ้า owner ยังไม่ยืนยันครบทุก station ในแชทจริง."""
    if os.environ.get("RELAY_CODE_OVERRIDE") == "1":
        return None
    if not AI_DELEGATE_RE.search(command):
        return None
    if not _cwd_in_mw_registry(cwd):
        return None
    if not transcript_path:
        return (
            "โปรเจกต์ Migrate Web: สั่ง AI สร้างหน้าไม่ได้ — อ่านบันทึกแชทไม่ได้ "
            "(payload ไม่มี transcript_path) จึงยืนยันการอนุมัติของเจ้าของไม่ได้"
        )
    try:
        approved = owner_approved_stations(transcript_path)
    except OSError:
        return (
            "โปรเจกต์ Migrate Web: อ่านบันทึกแชทไม่ได้ จึงยังยืนยันไม่ได้ว่าเจ้าของอนุมัติ "
            "— บล็อกไว้ก่อนเพื่อความปลอดภัย"
        )
    missing = [station for station in REQUIRED_STATIONS if station not in approved]
    if not missing:
        return None
    return (
        "โปรเจกต์ Migrate Web: ยังสั่ง AI สร้างหน้าไม่ได้ — "
        f"ต้องให้เจ้าของพิมพ์ยืนยันในแชทก่อน ขาดสถานี: {', '.join(missing)} "
        "(ให้เจ้าของพิมพ์ยืนยันราย station เช่น 'OK M0')"
    )


def _advice(stderr: str) -> str:
    match = re.search(r"(?:^|\n)-?\s*(M(?:\d+(?:\.\d+)?)|S):", stderr)
    if match:
        return f"ทำ {match.group(1)} ให้จบก่อน แล้วสร้างหลักฐานตาม path ที่แจ้ง"
    return "ทำขั้นที่ขาดให้จบและสร้างไฟล์หลักฐานตามข้อความข้างต้นก่อนลองใหม่"


def _block(message: str) -> int:
    print(f"[Hermes Flow Gate] {message}", file=sys.stderr)
    return 2


def _guard_target(target: Path, cwd: Path) -> Optional[str]:
    absolute = _absolute(target, cwd)
    root = find_project_root(absolute)
    if root is None:
        return None
    gate = find_flow_gate(root)
    if gate is None:
        return (
            "ไม่พบ scripts/mw/flow_gate.py สำหรับโปรเจกต์ MW; "
            "ติดตั้งชุด MW flow gate ที่ project/scripts/mw หรือ ~/.hermes/mw ก่อนเขียนไฟล์"
        )
    try:
        proc = subprocess.run(
            [sys.executable, str(gate), "guard-write", str(absolute)],
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return "flow_gate.py ใช้เวลาเกิน 15 วินาที จึงบล็อกการเขียนเพื่อความปลอดภัย"
    except OSError as exc:
        return f"เรียก flow_gate.py ไม่สำเร็จ จึงบล็อกการเขียน: {exc}"
    if proc.returncode == 0:
        if proc.stderr.strip():
            print(proc.stderr.strip(), file=sys.stderr)
        return None
    detail = (proc.stderr or proc.stdout or f"guard-write exit={proc.returncode}").strip()
    return f"{detail}\n{_advice(detail)}"


def run(payload: Dict[str, object]) -> int:
    tool_name = payload.get("tool_name")
    if tool_name not in WRITE_TOOLS | {"Bash"}:
        return 0
    raw_input = payload.get("tool_input")
    tool_input = raw_input if isinstance(raw_input, dict) else {}
    raw_cwd = payload.get("cwd")
    cwd = _absolute(Path(str(raw_cwd)) if raw_cwd else Path.cwd(), Path.cwd())
    cwd_root = find_project_root(cwd)

    # Flow Station Gate: จับตอน AI โยนงานสร้างหน้าให้ AI ตัวอื่น (นอกเหนือ guard-write)
    if tool_name == "Bash":
        command_value = tool_input.get("command")
        if isinstance(command_value, str) and command_value.strip():
            raw_transcript = payload.get("transcript_path")
            transcript_path = raw_transcript if isinstance(raw_transcript, str) else None
            delegation_block = _guard_delegation(command_value, cwd, transcript_path)
            if delegation_block:
                return _block(delegation_block)

    targets: Iterable[Path]
    if tool_name in WRITE_TOOLS:
        file_path = tool_input.get("file_path")
        if not isinstance(file_path, str) or not file_path.strip():
            if cwd_root is not None:
                return _block("คำสั่งเขียนไฟล์ไม่มี tool_input.file_path จึงตรวจลำดับงานไม่ได้")
            return 0
        targets = (Path(file_path),)
    else:
        command = tool_input.get("command")
        if not isinstance(command, str) or not command.strip():
            return 0
        extracted, has_write, complex_write = extract_bash_targets(command)
        if not has_write:
            return 0
        if cwd_root is not None and (complex_write or not extracted):
            return _block(
                "คำสั่ง shell เขียนไฟล์ในโปรเจกต์ MW ต้องแตกเป็นคำสั่งเดียวชัดๆ"
            )
        targets = (Path(value) for value in extracted)

    blockers = []
    for target in targets:
        blocker = _guard_target(target, cwd)
        if blocker:
            blockers.append(blocker)
    if blockers:
        return _block("\n".join(blockers))
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError) as exc:
        return _block(f"อ่านข้อมูล PreToolUse ไม่ได้: {exc}")
    if not isinstance(payload, dict):
        return _block("ข้อมูล PreToolUse ต้องเป็น JSON object")
    return run(payload)


if __name__ == "__main__":
    raise SystemExit(main())
