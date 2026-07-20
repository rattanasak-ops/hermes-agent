#!/usr/bin/env python3
"""สร้างรายชื่อ Shortcut ที่ต้องตรวจร่วมจากทะเบียนและ Graph Links จริง."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


WIKI_REFERENCE_RE = re.compile(
    r"\[\[(?:skills/prompt-shortcuts/)?references/([a-z0-9-]+)(?:\|[^\]]+)?\]\]",
    re.IGNORECASE,
)
REGISTRY_ROW_RE = re.compile(
    r"^\|\s*`([^`]+)`\s*\|.*?\[\[(?:skills/prompt-shortcuts/)?references/"
    r"([a-z0-9-]+)(?:\|[^\]]+)?\]\].*?\|\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def default_sources() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[1]
    skill = root / "team-shortcuts" / "payload" / "skills" / "prompt-shortcuts"
    return (
        root / "team-shortcuts" / "payload" / "ai-context" / "prompt-shortcut-registry.md",
        skill / "references",
    )


def build_graph(registry_path: Path, reference_dir: Path) -> tuple[dict[str, set[str]], dict[str, str]]:
    """อ่านเฉพาะทะเบียนที่ระบุและไฟล์ตรงใต้ references."""
    registry_text = registry_path.read_text(encoding="utf-8")
    rows = REGISTRY_ROW_RE.findall(registry_text)
    names = {slug.casefold(): name.strip() for name, slug in rows}
    graph = {slug: set() for slug in names}

    # ไม่ค้นทั้งโครงการ จึงไม่หยิบ .backup-* หรือ .project/scratchpad มาปน
    for path in sorted(reference_dir.glob("*.md")):
        source = path.stem.casefold()
        if source not in names:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for target in WIKI_REFERENCE_RE.findall(text):
            target = target.casefold()
            if target == source or target not in names:
                continue
            graph[source].add(target)
            graph[target].add(source)

    # ความสัมพันธ์ที่ทะเบียนบอกตรง ๆ เช่น Shortcut หนึ่งสร้างบนอีกตัว
    canonical = sorted(names.items(), key=lambda item: len(item[1]), reverse=True)
    for line in registry_text.splitlines():
        match = REGISTRY_ROW_RE.match(line)
        if not match:
            continue
        _, source = match.groups()
        source = source.casefold()
        for target, display in canonical:
            if target == source:
                continue
            if re.search(rf"(?<![\w-]){re.escape(display)}(?![\w-])", line, re.I):
                graph[source].add(target)
                graph[target].add(source)
    return graph, names


def related_shortcuts(
    shortcut: str,
    registry_path: Path,
    reference_dir: Path,
) -> list[dict[str, str]]:
    graph, names = build_graph(registry_path, reference_dir)
    wanted = " ".join(shortcut.casefold().split())
    start = next(
        (slug for slug, display in names.items() if " ".join(display.casefold().split()) == wanted),
        None,
    )
    if start is None:
        return []

    seen: set[str] = set()
    queue: list[tuple[str, str]] = [(start, "requested")]
    reasons: dict[str, str] = {start: "requested"}
    while queue:
        current, _ = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        for target in sorted(graph.get(current, set())):
            if target not in reasons:
                reasons[target] = f"linked-from:{current}"
            if target not in seen:
                queue.append((target, reasons[target]))
    return [
        {"shortcut": names[slug], "slug": slug, "reason": reasons[slug]}
        for slug in sorted(seen, key=lambda item: names[item].casefold())
    ]


def main(argv: list[str] | None = None) -> int:
    default_registry, default_references = default_sources()
    parser = argparse.ArgumentParser()
    parser.add_argument("--shortcut", required=True)
    parser.add_argument("--registry", type=Path, default=default_registry)
    parser.add_argument("--references", type=Path, default=default_references)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        rows = related_shortcuts(args.shortcut, args.registry, args.references)
    except OSError as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}, ensure_ascii=False))
        return 2
    if not rows:
        print(json.dumps({"ok": False, "reason": "SHORTCUT_NOT_REGISTERED"}, ensure_ascii=False))
        return 2
    payload = {
        "ok": True,
        "requested": args.shortcut,
        "count": len(rows),
        "shortcuts": rows,
        "registry": str(args.registry.resolve()),
        "references": str(args.references.resolve()),
        "excluded_search_roots": [".backup-*", ".project/scratchpad"],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        for row in rows:
            print(f"{row['shortcut']} · {row['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
