"""Shortcut incident tracking for Hermes Agent.

The store groups the same failure across projects and machines by a stable
fingerprint.  The fourth occurrence creates a repair prompt for the owner to
bring into the Hermes Agent project.  Project agents only report incidents;
they never edit the central Shortcut sources.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ESCALATION_THRESHOLD = 3
SCHEMA_VERSION = 1

REGISTRY_ROW = re.compile(
    r"^\|\s*(?P<name_cell>.*?)\s*\|\s*(?P<aliases>.*?)\s*\|\s*"
    r"(?P<link>\[\[.*?\]\]|`[^`]+`|[^|]+)\s*\|"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()


def default_store_path() -> Path:
    return hermes_home() / "shortcut-incidents" / "shortcut-incidents.db"


def normalize(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def redact(value: str) -> str:
    """Remove common credentials before incident data reaches durable storage."""
    text = str(value or "")
    text = re.sub(r"(https?://)[^/@\s:]+:[^/@\s]+@", r"\1***:***@", text)
    text = re.sub(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+", "Bearer ***", text)
    text = re.sub(
        r"(?i)\b(token|password|passwd|secret|api[_-]?key|authorization)\s*[:=]\s*[^\s,;]+",
        r"\1=***",
        text,
    )
    return text


def fingerprint(shortcut: str, stage: str, symptom: str) -> str:
    payload = json.dumps(
        {
            "shortcut": normalize(shortcut),
            "stage": normalize(stage),
            "symptom": normalize(symptom),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def default_registry_path() -> Path:
    configured = os.environ.get("HERMES_SHORTCUT_REGISTRY", "").strip()
    repo_root = next(
        (parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists()),
        Path(__file__).resolve().parents[2],
    )
    candidates = [
        Path(configured).expanduser() if configured else None,
        repo_root / "team-shortcuts/payload/ai-context/prompt-shortcut-registry.md",
        Path.home() / "ObsidianVault/HermesAgent/ai-context/prompt-shortcut-registry.md",
    ]
    return next((path for path in candidates if path and path.is_file()), candidates[-1])


def shortcut_graph(registry_path: Path) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    registry = registry_path.resolve()
    root = registry.parent.parent
    rows: list[dict[str, Any]] = []
    for line in registry.read_text(encoding="utf-8").splitlines():
        match = REGISTRY_ROW.match(line)
        if not match:
            continue
        names = re.findall(r"`([^`]+)`", match.group("name_cell"))
        if not names:
            continue
        name = names[0].strip()
        aliases = [*names[1:], *re.findall(r"`([^`]+)`", match.group("aliases"))]
        link_cell = match.group("link").strip()
        wiki = re.search(r"\[\[([^]|]+)(?:\|[^]]+)?\]\]", link_cell)
        linked = wiki.group(1).strip() if wiki else link_cell.strip("` ")
        target = root / linked
        if not target.suffix:
            target = target.with_suffix(".md")
        rows.append({"name": name, "aliases": [name, *aliases], "target": target.resolve()})

    graph = {row["name"]: set() for row in rows}
    by_target: dict[Path, list[str]] = {}
    for row in rows:
        by_target.setdefault(row["target"], []).append(row["name"])
    for names in by_target.values():
        for name in names:
            graph[name].update(other for other in names if other != name)

    canonical_lookup = {row["name"].casefold(): row["name"] for row in rows}
    canonical_pattern = re.compile(
        r"(?<![\w-])(?:"
        + "|".join(re.escape(name) for name in sorted(canonical_lookup, key=len, reverse=True))
        + r")(?![\w-])",
        re.I,
    ) if canonical_lookup else None
    shared_links: dict[Path, set[str]] = {}
    for row in rows:
        target = row["target"]
        if not target.is_file():
            continue
        text = target.read_text(encoding="utf-8", errors="replace")
        linked_paths: list[Path] = []
        for raw in re.findall(r"\[\[([^]|]+)(?:\|[^]]+)?\]\]", text):
            candidate = root / raw.strip()
            if not candidate.suffix:
                candidate = candidate.with_suffix(".md")
            linked_paths.append(candidate.resolve())
        for linked_path in linked_paths:
            shared_links.setdefault(linked_path, set()).add(row["name"])
        mentioned = {
            canonical_lookup[match.group(0).casefold()]
            for match in canonical_pattern.finditer(text)
        } if canonical_pattern else set()
        mentioned.discard(row["name"])
        mentioned.update(
            other["name"]
            for other in rows
            if other["name"] != row["name"] and other["target"] in linked_paths
        )
        for other_name in mentioned:
            graph[row["name"]].add(other_name)
            graph[other_name].add(row["name"])
    for names in shared_links.values():
        if len(names) < 2:
            continue
        for name in names:
            graph[name].update(other for other in names if other != name)
    return rows, graph


def related_shortcuts(shortcut: str, registry_path: Path | None = None) -> list[str]:
    registry = registry_path or default_registry_path()
    try:
        rows, graph = shortcut_graph(registry)
    except (OSError, ValueError):
        return [str(shortcut).strip()]
    lookup = normalize(shortcut)
    start = next(
        (row["name"] for row in rows if lookup in {normalize(alias) for alias in row["aliases"]}),
        None,
    )
    if start is None:
        return [str(shortcut).strip()]
    connected: set[str] = set()
    pending = [start]
    while pending:
        name = pending.pop()
        if name in connected:
            continue
        connected.add(name)
        pending.extend(sorted(graph.get(name, set()) - connected))
    return [row["name"] for row in rows if row["name"] in connected]


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            Path(tmp_name).unlink()
        except FileNotFoundError:
            pass


class ShortcutIncidentStore:
    def __init__(self, path: str | Path | None = None, registry_path: str | Path | None = None) -> None:
        self.path = Path(path).expanduser() if path else default_store_path()
        self.registry_path = Path(registry_path).expanduser() if registry_path else default_registry_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL UNIQUE,
                    shortcut TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    symptom TEXT NOT NULL,
                    expected TEXT NOT NULL,
                    actual TEXT NOT NULL,
                    status TEXT NOT NULL,
                    occurrence_count INTEGER NOT NULL DEFAULT 0,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    prompt_path TEXT,
                    closed_version TEXT,
                    close_evidence TEXT
                );
                CREATE TABLE IF NOT EXISTS occurrences (
                    occurrence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    project TEXT NOT NULL,
                    machine TEXT NOT NULL,
                    git_root TEXT,
                    branch TEXT,
                    git_sha TEXT,
                    evidence_json TEXT NOT NULL,
                    source TEXT NOT NULL,
                    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
                );
                CREATE INDEX IF NOT EXISTS idx_occurrences_incident
                    ON occurrences(incident_id, occurrence_id);
                """
            )
            conn.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    def record(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = ("shortcut", "stage", "symptom", "expected", "actual", "project", "machine")
        missing = [key for key in required if not str(payload.get(key) or "").strip()]
        if missing:
            raise ValueError("ข้อมูลเหตุไม่ครบ: " + ", ".join(missing))

        clean = {key: redact(str(value or "").strip()) for key, value in payload.items() if key != "evidence"}
        evidence = [redact(str(item)) for item in (payload.get("evidence") or []) if str(item).strip()]
        fp = fingerprint(clean["shortcut"], clean["stage"], clean["symptom"])
        incident_id = f"SCG-INC-{fp[:12].upper()}"
        timestamp = utc_now()

        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM incidents WHERE fingerprint = ?", (fp,)
            ).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO incidents(
                        incident_id, fingerprint, shortcut, stage, symptom,
                        expected, actual, status, occurrence_count,
                        first_seen_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'tracking', 0, ?, ?)
                    """,
                    (
                        incident_id,
                        fp,
                        clean["shortcut"],
                        clean["stage"],
                        clean["symptom"],
                        clean["expected"],
                        clean["actual"],
                        timestamp,
                        timestamp,
                    ),
                )
            conn.execute(
                """
                INSERT INTO occurrences(
                    incident_id, occurred_at, project, machine, git_root,
                    branch, git_sha, evidence_json, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident_id,
                    timestamp,
                    clean["project"],
                    clean["machine"],
                    clean.get("git_root", ""),
                    clean.get("branch", ""),
                    clean.get("git_sha", ""),
                    json.dumps(evidence, ensure_ascii=False),
                    clean.get("source", "manual") or "manual",
                ),
            )
            count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM occurrences WHERE incident_id = ?", (incident_id,)
                ).fetchone()[0]
            )
            status = "escalate_to_hermes" if count > ESCALATION_THRESHOLD else "tracking"
            conn.execute(
                """
                UPDATE incidents
                SET occurrence_count = ?, last_seen_at = ?, status = ?,
                    expected = ?, actual = ?
                WHERE incident_id = ?
                """,
                (count, timestamp, status, clean["expected"], clean["actual"], incident_id),
            )

        prompt_path = None
        if count > ESCALATION_THRESHOLD:
            prompt_path = self._write_repair_prompt(incident_id)
            with self.connect() as conn:
                conn.execute(
                    "UPDATE incidents SET prompt_path = ? WHERE incident_id = ?",
                    (str(prompt_path), incident_id),
                )

        result = self.get(incident_id)
        result["decision"] = "ESCALATE_TO_HERMES" if count > ESCALATION_THRESHOLD else "SHORTCUT_REPORT_ONLY"
        result["prompt_created"] = prompt_path is not None
        return result

    def get(self, incident_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"ไม่พบเหตุ {incident_id}")
            occurrences = conn.execute(
                "SELECT * FROM occurrences WHERE incident_id = ? ORDER BY occurrence_id",
                (incident_id,),
            ).fetchall()
        data = dict(row)
        data["occurrences"] = [
            {
                **dict(item),
                "evidence": json.loads(item["evidence_json"]),
            }
            for item in occurrences
        ]
        for item in data["occurrences"]:
            item.pop("evidence_json", None)
        data["related_shortcuts"] = related_shortcuts(data["shortcut"], self.registry_path)
        data["related_shortcuts_source"] = str(self.registry_path)
        return data

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM incidents"
        params: tuple[Any, ...] = ()
        if status:
            sql += " WHERE status = ?"
            params = (status,)
        sql += " ORDER BY last_seen_at DESC, incident_id"
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def close(self, incident_id: str, version: str, evidence: Iterable[str]) -> dict[str, Any]:
        if not str(version or "").strip():
            raise ValueError("ต้องระบุรุ่นที่กระจายแล้ว")
        evidence_rows = [redact(str(item)) for item in evidence if str(item).strip()]
        if not evidence_rows:
            raise ValueError("ต้องมีหลักฐานปิดเหตุอย่างน้อย 1 รายการ")
        with self.connect() as conn:
            changed = conn.execute(
                """
                UPDATE incidents
                SET status = 'closed', closed_version = ?, close_evidence = ?, last_seen_at = ?
                WHERE incident_id = ?
                """,
                (str(version).strip(), json.dumps(evidence_rows, ensure_ascii=False), utc_now(), incident_id),
            ).rowcount
        if not changed:
            raise KeyError(f"ไม่พบเหตุ {incident_id}")
        return self.get(incident_id)

    def _write_repair_prompt(self, incident_id: str) -> Path:
        incident = self.get(incident_id)
        projects = sorted({row["project"] for row in incident["occurrences"]})
        machines = sorted({row["machine"] for row in incident["occurrences"]})
        evidence: list[str] = []
        for row in incident["occurrences"]:
            evidence.extend(row["evidence"])
        related = "\n".join(f"- {name}" for name in incident["related_shortcuts"])
        evidence_text = "\n".join(f"- {item}" for item in evidence) or "- ยังไม่มีไฟล์หลักฐานแนบ"
        content = f"""# Prompt ซ่อม Shortcut กลาง — {incident_id}

ทำงานในโปรเจกต์ Hermes Agent เท่านั้น ห้ามแก้ Shortcut จากโปรเจกต์ผู้แจ้ง

Incident: {incident_id}
Shortcut หลัก: {incident['shortcut']}
ขั้นที่เสีย: {incident['stage']}
เกิดซ้ำ: {incident['occurrence_count']} ครั้ง
โปรเจกต์ที่พบ: {', '.join(projects)}
เครื่องที่พบ: {', '.join(machines)}
สิ่งที่ควรเกิด: {incident['expected']}
สิ่งที่เกิดจริง: {incident['actual']}
อาการร่วมที่ใช้รวมเหตุ: {incident['symptom']}

หลักฐาน:
{evidence_text}

Shortcut ที่ต้องตรวจร่วมกัน:
{related}

งานที่ต้องทำ:
1. ตรวจต้นเหตุจากไฟล์ต้นทางจริง ห้ามแก้เฉพาะข้อความปลายทาง
2. ตรวจทะเบียน Prompt เต็ม Hook ตัวติดตั้ง และชุดกระจายที่เกี่ยวข้อง
3. สร้างกรณีทดสอบที่ทำให้อาการนี้เกิดก่อนแก้ แล้วพิสูจน์ว่าหลังแก้ไม่เกิดซ้ำ
4. แก้เฉพาะใน Hermes Agent และห้ามแก้ไฟล์ Shortcut ในโปรเจกต์ผู้แจ้ง
5. ตรวจ Shortcut ที่เกี่ยวข้องทั้งหมด ไม่ใช่เฉพาะตัวหลัก
6. เทียบรุ่นและแฮชของต้นทาง ชุดกระจาย Mac VPS และเครื่องทีม
7. รายงานทุก Issue เป็น N/M และเปอร์เซ็นต์จากหลักฐานจริง
8. ถ้ายังไม่ครบ ห้ามประกาศพร้อมใช้ และต้องสร้าง Prompt ทำงานต่อ
"""
        path = self.path.parent / "repair-prompts" / f"{incident_id}.md"
        _atomic_write(path, content)
        return path
