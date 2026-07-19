"""Structured diagnosis validation, deterministic routing, and packet build.

This module never does natural-language diagnosis: the Consultor produces a
structured diagnosis outside the plugin and passes it in. Given that diagnosis,
routing deterministically selects domain leads, specialist roles, and family
skills from the catalog, then assembles a Team Manifest and a Work Packet with a
content-addressed packet id. It also prepares (without writing) a training
candidate for owner review.

Standard library only. No writes, no network, no clock, no randomness.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from plugins.agent_center import catalog, policies


CONSULTOR_ID = "consultor"
PACKET_SCHEMA_VERSION = "2.0"

DIAGNOSIS_REQUIRED_STR_FIELDS = ("project_id", "goal", "phase")
# Must be a list of strings AND carry at least one entry.
DIAGNOSIS_REQUIRED_LIST_FIELDS = ("domains",)
# Keys must be present and be lists of strings; the list may be empty, but a
# missing key or any wrong (non-list) type is rejected.
DIAGNOSIS_TYPED_LIST_FIELDS = ("risk_tags", "signals")
# Keys may be absent (treated as an empty list); if present they must be lists
# of strings, so wrong (non-list) types are rejected rather than silently dropped.
DIAGNOSIS_OPTIONAL_LIST_FIELDS = (
    "project_context_refs",
    "allowed_paths",
    "forbidden_actions",
    "deliverables",
    "evidence_gates",
)

PHASE_DEFAULT_EXECUTION_MODE = {
    "discovery": "think",
    "design": "plan",
    "build": "build",
    "review": "review",
    "release": "build",
}

# Every field the built Work Packet body carries must be present for the packet
# to be valid (packet_id is the content hash of all the other fields).
PACKET_REQUIRED_FIELDS = (
    "packet_id",
    "packet_schema_version",
    "project_id",
    "goal",
    "phase",
    "execution_mode",
    "domains",
    "risk_tags",
    "signals",
    "project_context_refs",
    "allowed_paths",
    "forbidden_actions",
    "deliverables",
    "evidence_gates",
    "team",
    "seats",
    "seat_policy",
    "training_receipt_required",
)

TRAINING_REQUIRED_STR_FIELDS = (
    "submitter",
    "project",
    "task",
    "target_type",
    "target_id",
    "observed_result",
    "scope",
    "privacy",
    "submitted_at",
)


def _canonical(payload: Any) -> str:
    """Serialize deterministically for hashing (stable keys, compact, UTF-8)."""

    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _content_id(prefix: str, payload: Any) -> str:
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def _clean_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _clean_str_list(value: Any) -> list[str]:
    """Return trimmed, de-duplicated strings preserving first-seen order."""

    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in value:
        text = _clean_str(item)
        if text and text not in seen:
            seen.add(text)
            cleaned.append(text)
    return cleaned


def _validate_list_field(
    value: Any,
    field: str,
    errors: list[str],
    *,
    require_key: bool = False,
    require_non_empty: bool = False,
) -> list[str]:
    """Validate a diagnosis list field, distinguishing empty from wrong type.

    A present value that is not a list is always rejected as a type error. A
    missing value (``None``) is treated as an empty list unless ``require_key``
    (the key must be present as a list) or ``require_non_empty`` (the list must
    also carry at least one entry) is set, in which case it is rejected. When
    ``require_non_empty`` is set, an empty (or all-blank) list is also rejected.
    """

    if value is None:
        if require_key:
            errors.append(f"diagnosis: '{field}' key is required and must be a list")
        elif require_non_empty:
            errors.append(f"diagnosis: '{field}' must be a non-empty list")
        return []
    if not isinstance(value, list):
        errors.append(f"diagnosis: '{field}' must be a list of strings")
        return []
    cleaned = _clean_str_list(value)
    if require_non_empty and not cleaned:
        errors.append(f"diagnosis: '{field}' must be a non-empty list")
    return cleaned


def validate_diagnosis(diagnosis: Any) -> dict[str, Any]:
    """Validate a structured diagnosis; return report with normalized payload.

    Rejects a raw request string or a missing structured object. ``domains``
    must be non-empty and reference only catalog-supported domain ids.
    """

    errors: list[str] = []
    if not isinstance(diagnosis, dict):
        return {
            "ok": False,
            "code": "diagnosis_invalid",
            "errors": ["diagnosis must be a structured object, not a raw request string"],
        }

    normalized: dict[str, Any] = {}
    for field in DIAGNOSIS_REQUIRED_STR_FIELDS:
        value = _clean_str(diagnosis.get(field))
        if not value:
            errors.append(f"diagnosis: '{field}' is required and must be a non-empty string")
        normalized[field] = value

    phase = normalized.get("phase", "")
    explicit_mode = _clean_str(diagnosis.get("execution_mode")).lower()
    execution_mode = explicit_mode or PHASE_DEFAULT_EXECUTION_MODE.get(phase, "")
    if execution_mode not in policies.EXECUTION_MODES:
        errors.append(
            "diagnosis: 'execution_mode' must be one of "
            + ", ".join(sorted(policies.EXECUTION_MODES))
        )
    normalized["execution_mode"] = execution_mode

    supported = set(catalog.get_supported_domains())
    for field in DIAGNOSIS_REQUIRED_LIST_FIELDS:
        normalized[field] = _validate_list_field(
            diagnosis.get(field), field, errors, require_non_empty=True
        )

    for field in DIAGNOSIS_TYPED_LIST_FIELDS:
        normalized[field] = _validate_list_field(
            diagnosis.get(field), field, errors, require_key=True
        )

    unknown = [d for d in normalized.get("domains", []) if d not in supported]
    if unknown:
        errors.append(
            "diagnosis: unknown domain id(s) not in supported_domains: " + ", ".join(unknown)
        )

    for field in DIAGNOSIS_OPTIONAL_LIST_FIELDS:
        normalized[field] = _validate_list_field(diagnosis.get(field), field, errors)

    if errors:
        return {"ok": False, "code": "diagnosis_invalid", "errors": errors}
    return {"ok": True, "code": "diagnosis_valid", "diagnosis": normalized}


def _score_by_domains(domain_tags: Any, wanted: list[str]) -> int:
    """Count how many wanted domains appear in an agent's domain_tags."""

    if not isinstance(domain_tags, list):
        return 0
    tags = set(domain_tags)
    return sum(1 for d in wanted if d in tags)


def _select_leads(wanted: list[str]) -> list[dict[str, Any]]:
    """Select every domain lead matching a wanted domain (never the Consultor).

    Ordered by descending domain-match score, then ascending routing_priority,
    then stable catalog order for byte-equivalent output.
    """

    candidates: list[tuple[int, int, int, dict[str, Any]]] = []
    for order, lead in enumerate(catalog.list_agents(kind="lead")):
        if lead.get("id") == CONSULTOR_ID:
            continue
        score = _score_by_domains(lead.get("domain_tags"), wanted)
        if score <= 0:
            continue
        priority = lead.get("routing_priority")
        priority = priority if isinstance(priority, int) else 10_000
        candidates.append((-score, priority, order, lead))

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))

    selected: list[dict[str, Any]] = []
    for neg_score, priority, _order, lead in candidates:
        selected.append(
            {
                "id": lead.get("id"),
                "name_th": lead.get("name_th"),
                "domain_tags": list(lead.get("domain_tags", [])),
                "routing_priority": priority,
                "match_score": -neg_score,
                "reason": (
                    f"matched {-neg_score} requested domain(s): "
                    + ", ".join(d for d in wanted if d in set(lead.get("domain_tags", [])))
                ),
            }
        )
    return selected


def _select_specialists(wanted: list[str]) -> list[dict[str, Any]]:
    """Select specialist roles whose domain_tags match a wanted domain."""

    selected: list[dict[str, Any]] = []
    for spec in catalog.list_agents(kind="specialist"):
        score = _score_by_domains(spec.get("domain_tags"), wanted)
        if score <= 0:
            continue
        matched = [d for d in wanted if d in set(spec.get("domain_tags", []))]
        selected.append(
            {
                "id": spec.get("id"),
                "name_th": spec.get("name_th"),
                "lead_agent_id": spec.get("lead_agent_id"),
                "domain_tags": list(spec.get("domain_tags", [])),
                "match_score": score,
                "reason": "matched domain(s): " + ", ".join(matched),
            }
        )
    return selected


def _select_skills(wanted: list[str]) -> list[dict[str, Any]]:
    """Select every family skill whose domain_tags match a wanted domain."""

    selected: list[dict[str, Any]] = []
    for skill in catalog.list_skills():
        score = _score_by_domains(skill.get("domain_tags"), wanted)
        if score <= 0:
            continue
        matched = [d for d in wanted if d in set(skill.get("domain_tags", []))]
        selected.append(
            {
                "name": skill.get("name"),
                "family": skill.get("family"),
                "domain_tags": list(skill.get("domain_tags", [])),
                "match_score": score,
                "reason": "matched domain(s): " + ", ".join(matched),
            }
        )
    return selected


def _consultor_intake() -> dict[str, Any]:
    """Return the Consultor as the fixed intake agent (never a producing lead)."""

    agent = catalog.get_agent(CONSULTOR_ID)
    name_th = agent.get("name_th") if isinstance(agent, dict) else None
    return {
        "id": CONSULTOR_ID,
        "name_th": name_th,
        "role": "intake",
        "produces_deliverables": False,
        "reason": "Consultor is always the intake agent and never a producing lead",
    }


def build_team_manifest(diagnosis: dict[str, Any]) -> dict[str, Any]:
    """Build the deterministic Team Manifest from a normalized diagnosis."""

    wanted = list(diagnosis.get("domains", []))
    return {
        "project_id": diagnosis.get("project_id"),
        "goal": diagnosis.get("goal"),
        "phase": diagnosis.get("phase"),
        "execution_mode": diagnosis.get("execution_mode"),
        "domains": wanted,
        "intake": _consultor_intake(),
        "leads": _select_leads(wanted),
        "specialists": _select_specialists(wanted),
        "skills": _select_skills(wanted),
    }


def build_work_packet(
    diagnosis: Any,
    seats: Any,
    current_provider_id: Any,
    current_session_id: Any,
) -> dict[str, Any]:
    """Validate diagnosis + assign seats, then assemble a Work Packet.

    Returns ``ok:false`` with a code when the diagnosis is invalid or the seats
    cannot be assigned (never silently downgrades). On success the packet carries
    a deterministic ``packet_id`` derived from its normalized content.
    """

    diag_report = validate_diagnosis(diagnosis)
    if not diag_report["ok"]:
        return diag_report
    normalized = diag_report["diagnosis"]

    seat_report = policies.assign_seats(
        seats,
        current_provider_id,
        current_session_id,
        normalized["execution_mode"],
    )
    if not seat_report["ok"]:
        return {
            "ok": False,
            "code": "seats_unassigned",
            "decision": seat_report["decision"],
            "policy": seat_report["policy"],
            "errors": seat_report["errors"],
        }

    manifest = build_team_manifest(normalized)

    body = {
        "packet_schema_version": PACKET_SCHEMA_VERSION,
        "project_id": normalized["project_id"],
        "goal": normalized["goal"],
        "phase": normalized["phase"],
        "execution_mode": normalized["execution_mode"],
        "domains": normalized["domains"],
        "risk_tags": normalized["risk_tags"],
        "signals": normalized["signals"],
        "project_context_refs": normalized["project_context_refs"],
        "allowed_paths": normalized["allowed_paths"],
        "forbidden_actions": normalized["forbidden_actions"],
        "deliverables": normalized["deliverables"],
        "evidence_gates": normalized["evidence_gates"],
        "team": manifest,
        "seats": seat_report["seats"],
        "seat_policy": seat_report["policy"],
        "training_receipt_required": True,
    }

    packet_id = _content_id("packet", body)
    packet = {"packet_id": packet_id}
    packet.update(body)

    return {"ok": True, "code": "packet_ready", "decision": "assigned", "packet": packet}


def _packet_seat(record: Any, label: str, errors: list[str]) -> dict[str, Any] | None:
    """Validate one packet seat record; return normalized fields or None."""

    if not isinstance(record, dict):
        errors.append(f"{label}: must be an object")
        return None
    provider = policies.normalize_id(record.get("provider_id"))
    session = policies.normalize_id(record.get("session_id"))
    if not provider:
        errors.append(f"{label}: missing provider_id")
    if not session:
        errors.append(f"{label}: missing session_id")
    healthy = record.get("healthy") is True
    if not healthy:
        errors.append(f"{label}: must be marked healthy:true")
    roles_raw = record.get("roles")
    roles = (
        [policies.normalize_id(role) for role in roles_raw]
        if isinstance(roles_raw, list)
        else []
    )
    roles = [role for role in roles if role]
    if not roles:
        errors.append(f"{label}: roles must be a non-empty list")
    if not provider or not session:
        return None
    # Derive the family from the provider id itself; never trust a caller-supplied
    # provider_family, so the cross-family checks cannot be spoofed by the payload.
    family = policies.provider_family(provider)
    return {
        "provider": provider,
        "session": session,
        "family": family,
        "healthy": healthy,
        "roles": roles,
    }


def validate_work_packet(packet: Any) -> dict[str, Any]:
    """Validate a built Work Packet without rebuilding or persisting anything.

    Checks required fields and the active seat contract. Every mode requires a
    cross-provider planner pair. Build mode additionally requires a distinct
    worker/reviewer pair with a read-only reviewer. ``packet_id`` must still
    match the content hash of the rest of the packet.
    """

    errors: list[str] = []
    if not isinstance(packet, dict):
        return {
            "ok": False,
            "code": "packet_invalid",
            "errors": ["packet must be a structured object"],
        }

    legacy_required_fields = set(PACKET_REQUIRED_FIELDS) - {
        "packet_schema_version",
        "execution_mode",
    }
    legacy_packet = (
        "packet_schema_version" not in packet
        and legacy_required_fields.issubset(packet)
    )

    for field in PACKET_REQUIRED_FIELDS:
        if field not in packet:
            errors.append(f"packet: missing field '{field}'")

    if packet.get("packet_schema_version") != PACKET_SCHEMA_VERSION:
        errors.append(
            "packet: 'packet_schema_version' must be " + PACKET_SCHEMA_VERSION
        )

    packet_id = packet.get("packet_id")
    packet_id_ok = isinstance(packet_id, str) and bool(packet_id.strip())
    if not packet_id_ok:
        errors.append("packet: 'packet_id' must be a non-empty string")

    execution_mode = policies.normalize_id(packet.get("execution_mode"))
    try:
        active_seat_names = policies.required_seat_names(execution_mode)
    except ValueError:
        errors.append(
            "packet: 'execution_mode' must be one of "
            + ", ".join(sorted(policies.EXECUTION_MODES))
        )
        active_seat_names = ()

    seats = packet.get("seats")
    seat_info: dict[str, dict[str, Any]] = {}
    if not isinstance(seats, dict):
        errors.append("packet: 'seats' must be an object with the active seat records")
    else:
        unexpected_seats = sorted(set(seats) - set(active_seat_names))
        if unexpected_seats:
            errors.append(
                "packet.seats: inactive or unknown seat(s) for execution_mode "
                f"'{execution_mode}': " + ", ".join(unexpected_seats)
            )
        for name in active_seat_names:
            if name not in seats:
                errors.append(f"packet.seats: missing seat '{name}'")
                continue
            info = _packet_seat(seats[name], f"packet.seats.{name}", errors)
            if info is not None:
                seat_info[name] = info

    if active_seat_names and len(seat_info) == len(active_seat_names):
        sessions = [info["session"] for info in seat_info.values()]
        if len(set(sessions)) != len(sessions):
            errors.append("packet.seats: all active session ids must be unique")

        primary = seat_info["planner_primary"]
        challenger = seat_info["planner_challenger"]
        for name, planner in (
            ("planner_primary", primary),
            ("planner_challenger", challenger),
        ):
            if not (policies.CHALLENGER_ROLES & set(planner["roles"])):
                errors.append(
                    f"packet.seats.{name}: must support planner, analysis, or brain"
                )
        if primary["family"] == challenger["family"]:
            errors.append(
                "packet.seats: planner pair must be cross-family (never same provider)"
            )

        if execution_mode == "build":
            worker = seat_info["worker"]
            reviewer = seat_info["reviewer"]
            if not ({"worker", "code"} & set(worker["roles"])):
                errors.append(
                    "packet.seats.worker: must support worker or code"
                )
            if "review" not in set(reviewer["roles"]):
                errors.append("packet.seats.reviewer: must support review")
            if worker["family"] == reviewer["family"]:
                errors.append("packet.seats: worker and reviewer must be cross-family")

            reviewer_record = seats.get("reviewer") if isinstance(seats, dict) else None
            if not (
                isinstance(reviewer_record, dict)
                and reviewer_record.get("read_only") is True
            ):
                errors.append("packet.seats.reviewer: must be marked read_only:true")

    team = packet.get("team")
    if not isinstance(team, dict):
        errors.append("packet: 'team' must be an object")
    else:
        for field in ("project_id", "goal", "phase", "execution_mode", "domains"):
            if team.get(field) != packet.get(field):
                errors.append(
                    f"packet.team: '{field}' must match packet '{field}'"
                )

    if packet_id_ok:
        body = {key: value for key, value in packet.items() if key != "packet_id"}
        expected = _content_id("packet", body)
        if expected != packet_id.strip():
            errors.append("packet: 'packet_id' does not match packet content hash")

    if errors:
        return {
            "ok": False,
            "code": "packet_legacy_unsupported" if legacy_packet else "packet_invalid",
            "errors": errors,
        }
    return {"ok": True, "code": "packet_valid", "packet_id": packet_id.strip()}


def prepare_training_candidate(candidate: Any) -> dict[str, Any]:
    """Validate + normalize a training candidate for owner review (no writes).

    Returns a deterministic candidate id, the normalized payload with
    ``owner_decision: pending`` and ``promoted: false``, plus a suggested safe
    relative review path and Markdown body. Never imports the Obsidian bridge and
    never writes any file.
    """

    errors: list[str] = []
    if not isinstance(candidate, dict):
        return {
            "ok": False,
            "code": "training_candidate_invalid",
            "errors": ["training candidate must be a structured object"],
        }

    normalized: dict[str, Any] = {}
    for field in TRAINING_REQUIRED_STR_FIELDS:
        value = _clean_str(candidate.get(field))
        if not value:
            errors.append(f"training candidate: '{field}' is required and must be non-empty")
        normalized[field] = value

    feedback = _clean_str(candidate.get("feedback"))
    if not feedback:
        errors.append("training candidate: 'feedback' is required and must be non-empty")
    normalized["feedback"] = feedback

    evidence_refs = _clean_str_list(candidate.get("evidence_refs"))
    if not evidence_refs:
        errors.append("training candidate: 'evidence_refs' must be a non-empty list")
    normalized["evidence_refs"] = evidence_refs

    repeat_count = candidate.get("repeat_count")
    if not isinstance(repeat_count, int) or isinstance(repeat_count, bool) or repeat_count < 1:
        errors.append("training candidate: 'repeat_count' must be an integer >= 1")
        repeat_count = None
    normalized["repeat_count"] = repeat_count

    if errors:
        return {"ok": False, "code": "training_candidate_invalid", "errors": errors}

    candidate_id = _content_id("training", normalized)

    payload = {"candidate_id": candidate_id}
    payload.update(normalized)
    payload["owner_decision"] = "pending"
    payload["promoted"] = False

    suggested_path = f"{policies.REVIEW_WRITE_PREFIX}training-candidate-{candidate_id}.md"
    markdown = _render_candidate_markdown(payload)

    return {
        "ok": True,
        "code": "training_candidate_ready",
        "candidate": payload,
        "suggested_path": suggested_path,
        "markdown": markdown,
    }


def _render_candidate_markdown(payload: dict[str, Any]) -> str:
    """Render a review-ready Markdown note (returned only, never written)."""

    lines = [
        f"# Training Candidate {payload['candidate_id']}",
        "",
        f"- submitter: {payload['submitter']}",
        f"- project: {payload['project']}",
        f"- task: {payload['task']}",
        f"- target: {payload['target_type']} / {payload['target_id']}",
        f"- scope: {payload['scope']}",
        f"- privacy: {payload['privacy']}",
        f"- repeat_count: {payload['repeat_count']}",
        f"- submitted_at: {payload['submitted_at']}",
        f"- owner_decision: {payload['owner_decision']}",
        f"- promoted: {str(payload['promoted']).lower()}",
        "",
        "## Feedback",
        payload["feedback"],
        "",
        "## Observed result",
        payload["observed_result"],
        "",
        "## Evidence refs",
    ]
    lines.extend(f"- {ref}" for ref in payload["evidence_refs"])
    return "\n".join(lines) + "\n"
