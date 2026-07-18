"""Six Agent Center tool handlers over the catalog, routing, and policy modules.

Each handler accepts an ``args`` dict and returns a JSON string with stable key
ordering and ``ensure_ascii=False``. Failures are caught and returned as
``{"ok": false, "code": ...}`` reports without leaking tracebacks. Handlers never
write files, never touch the network, and never persist anything.

Standard library only.
"""

from __future__ import annotations

import json
from typing import Any

from plugins.agent_center import catalog, policies, routing


def _json(payload: dict[str, Any]) -> str:
    """Serialize a report deterministically for tool output."""

    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _fail(code: str, error: str) -> dict[str, Any]:
    return {"ok": False, "code": code, "error": error}


def _optional_str(args: dict[str, Any], key: str) -> str | None:
    """Return a trimmed string arg, or None when absent/blank/non-string."""

    value = args.get(key)
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def agent_center_list_agents(args: dict[str, Any]) -> str:
    """List lead and specialist agents, optionally filtered by kind/domain/lead."""

    try:
        kind = _optional_str(args, "kind")
        domain = _optional_str(args, "domain")
        lead_id = _optional_str(args, "lead_id")
        agents = catalog.list_agents(kind=kind, domain=domain, lead_id=lead_id)
        return _json({"ok": True, "code": "agents_listed", "count": len(agents), "agents": agents})
    except catalog.CatalogError as exc:
        return _json({"ok": False, "code": exc.code, "errors": exc.errors})
    except Exception as exc:  # noqa: BLE001 - defensive: never leak a traceback
        return _json(_fail("list_agents_failed", str(exc)))


def agent_center_get_agent(args: dict[str, Any]) -> str:
    """Fetch a single agent (lead or specialist) by id."""

    try:
        agent_id = _optional_str(args, "agent_id")
        if agent_id is None:
            return _json(_fail("agent_id_required", "agent_id is required"))
        agent = catalog.get_agent(agent_id)
        if agent is None:
            return _json({"ok": False, "code": "agent_not_found", "agent_id": agent_id})
        return _json({"ok": True, "code": "agent_found", "agent": agent})
    except catalog.CatalogError as exc:
        return _json({"ok": False, "code": exc.code, "errors": exc.errors})
    except Exception as exc:  # noqa: BLE001 - defensive: never leak a traceback
        return _json(_fail("get_agent_failed", str(exc)))


def agent_center_list_skills(args: dict[str, Any]) -> str:
    """List skills, optionally filtered by family and/or domain."""

    try:
        family = _optional_str(args, "family")
        domain = _optional_str(args, "domain")
        skills = catalog.list_skills(family=family, domain=domain)
        return _json({"ok": True, "code": "skills_listed", "count": len(skills), "skills": skills})
    except catalog.CatalogError as exc:
        return _json({"ok": False, "code": exc.code, "errors": exc.errors})
    except Exception as exc:  # noqa: BLE001 - defensive: never leak a traceback
        return _json(_fail("list_skills_failed", str(exc)))


def agent_center_route(args: dict[str, Any]) -> str:
    """Validate a diagnosis, build a Team Manifest, and assemble a Work Packet.

    ``diagnosis`` plus the seat pool (``seats``) and the current session's
    ``current_provider_id`` and ``current_session_id`` are all required. When
    any are missing, or the deterministic seat assignment cannot be satisfied,
    the report carries a top-level ``blocked: true`` so callers stop instead of
    silently downgrading.
    """

    try:
        diagnosis = args.get("diagnosis")
        diag_report = routing.validate_diagnosis(diagnosis)
        if not diag_report["ok"]:
            return _json(diag_report)
        normalized = diag_report["diagnosis"]

        seats = args.get("seats")
        current_provider_id = _optional_str(args, "current_provider_id")
        current_session_id = _optional_str(args, "current_session_id")

        missing: list[str] = []
        if not isinstance(seats, list) or not seats:
            missing.append("seats: must be a non-empty list of seat objects")
        if current_provider_id is None:
            missing.append("current_provider_id is required")
        if current_session_id is None:
            missing.append("current_session_id is required")
        if missing:
            return _json(
                {
                    "ok": False,
                    "code": "route_seats_required",
                    "blocked": True,
                    "diagnosis": normalized,
                    "errors": missing,
                }
            )

        manifest = routing.build_team_manifest(normalized)
        packet_report = routing.build_work_packet(
            normalized,
            seats,
            current_provider_id,
            current_session_id,
        )

        report: dict[str, Any] = {
            "ok": packet_report["ok"],
            "code": "route_ready" if packet_report["ok"] else "route_seats_unassigned",
            "diagnosis": normalized,
            "team": manifest,
            "packet_report": packet_report,
        }
        if not packet_report["ok"]:
            report["blocked"] = True

        return _json(report)
    except catalog.CatalogError as exc:
        return _json({"ok": False, "code": exc.code, "errors": exc.errors})
    except Exception as exc:  # noqa: BLE001 - defensive: never leak a traceback
        return _json(_fail("route_failed", str(exc)))


def agent_center_prepare_training_candidate(args: dict[str, Any]) -> str:
    """Validate + normalize a training candidate for owner review (no writes)."""

    try:
        candidate = args.get("candidate")
        report = routing.prepare_training_candidate(candidate)
        return _json(report)
    except Exception as exc:  # noqa: BLE001 - defensive: never leak a traceback
        return _json(_fail("prepare_training_candidate_failed", str(exc)))


def agent_center_validate(args: dict[str, Any]) -> str:
    """Validate a Work Packet, a Work Receipt, or the bundled catalog.

    Supply exactly one of ``packet`` or ``receipt`` to validate that object (no
    persistence); supplying both is rejected. When neither is given the bundled
    catalog is validated and its totals and versions are reported.
    """

    try:
        has_packet = "packet" in args
        has_receipt = "receipt" in args
        if has_packet and has_receipt:
            return _json(
                _fail("validate_ambiguous", "provide either packet or receipt, not both")
            )
        if has_packet:
            return _json(routing.validate_work_packet(args.get("packet")))
        if has_receipt:
            return _json(policies.validate_work_receipt(args.get("receipt")))
        return _json(catalog.validate_catalog())
    except Exception as exc:  # noqa: BLE001 - defensive: never leak a traceback
        return _json(_fail("validate_failed", str(exc)))
