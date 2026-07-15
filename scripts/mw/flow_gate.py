#!/usr/bin/env python3
"""CLI gate for live Migrate Web flow evidence.

Commands:

  flow_gate.py status <menu> [--project-root DIR] [--rules FILE] [--json]
  flow_gate.py can-enter <STEP> <menu> [--project-root DIR] [--rules FILE] [--json]

Exit codes: 0 = readable/pass, 1 = cannot enter, 2 = usage/config error.
No state or cache files are created; every invocation reads evidence live.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from flow_eval import ConfigError, can_enter, evaluate, load_rules

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_ERROR = 2
DEFAULT_RULES_PATH = Path(__file__).with_name("flow-rules.yaml")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flow_gate.py",
        description=(
            "Evaluate the 13-step Migrate Web flow from live evidence. "
            "Exit 0 for status/readable or enterable, 1 when blocked, 2 on error."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Show every flow step")
    status.add_argument("menu", help="Safe menu slug")
    _add_common_arguments(status)

    enter = subparsers.add_parser("can-enter", help="Check all steps before STEP")
    enter.add_argument("step", help="Target step id, for example M4")
    enter.add_argument("menu", help="Safe menu slug")
    _add_common_arguments(enter)
    return parser


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root containing evidence (default: cwd)",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=None,
        help=(
            "Complete rules file (default: <project>/.work/flow-rules.yaml "
            "when present, otherwise the rules beside this script)"
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")


def resolve_rules_path(project_root: Path, explicit: Optional[Path]) -> Path:
    """Choose one complete rules file; project override replaces the default."""
    if explicit is not None:
        path = explicit.expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.is_file():
            raise ConfigError(f"rules file not found: {path}")
        return path

    override = project_root / ".work" / "flow-rules.yaml"
    if override.is_file():
        return override
    if DEFAULT_RULES_PATH.is_file():
        return DEFAULT_RULES_PATH
    raise ConfigError(
        f"rules file not found: neither {override} nor {DEFAULT_RULES_PATH} exists"
    )


def _print_error(message: str, as_json: bool) -> None:
    if as_json:
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    else:
        print(f"error: {message}", file=sys.stderr)


def _format_status(result: dict) -> str:
    lines = ["ขั้น | ชื่อ | สถานะ | ขาดอะไร", "--- | --- | --- | ---"]
    for step in result["steps"]:
        missing = "; ".join(step["missing"]) if step["missing"] else "-"
        lines.append(
            f"{step['id']} | {step['title']} | {step['status']} | {missing}"
        )
    current = result["current_step"] if result["current_step"] is not None else "none"
    lines.append(
        f"flow: {result['done_count']}/{result['total']} done · current={current}"
    )
    return "\n".join(lines)


def run(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI and return its process exit code."""
    args = _parser().parse_args(argv)
    root = (args.project_root or Path.cwd()).expanduser().resolve()
    try:
        rules_path = resolve_rules_path(root, args.rules)
        rules = load_rules(rules_path)
        if args.command == "status":
            result = evaluate(root, args.menu, rules)
            if args.json:
                print(json.dumps(result, ensure_ascii=False))
            else:
                print(_format_status(result))
            return EXIT_OK

        allowed, reasons = can_enter(root, args.menu, args.step, rules)
        payload = {
            "menu": args.menu,
            "step": args.step,
            "can_enter": allowed,
            "missing": reasons,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        elif allowed:
            print(f"can-enter {args.step}: YES")
        else:
            print(f"can-enter {args.step}: NO")
            for reason in reasons:
                print(f"- {reason}")
        return EXIT_OK if allowed else EXIT_BLOCKED
    except ConfigError as exc:
        _print_error(str(exc), bool(getattr(args, "json", False)))
        return EXIT_ERROR
    except (OSError, UnicodeError) as exc:
        _print_error(f"cannot evaluate flow: {exc}", bool(getattr(args, "json", False)))
        return EXIT_ERROR


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
