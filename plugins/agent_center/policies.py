"""Provider/session seat policy and work-receipt validation.

Assigns the active AI seats deterministically from a pool of provider/session
"seats". Every mode gets a cross-provider planner pair; build mode also gets a
separate worker/reviewer pair. It enforces unique sessions and validates a
returned Work Receipt without persisting anything.

Standard library only. No writes, no network, no clock, no randomness.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any


REVIEW_WRITE_PREFIX = "95-Inbox-Lab/review/"
RECEIPT_SCHEMA_VERSION = "2.0"

PLANNER_SEAT_NAMES = ("planner_primary", "planner_challenger")
BUILD_SEAT_NAMES = (*PLANNER_SEAT_NAMES, "worker", "reviewer")
SEAT_NAMES = BUILD_SEAT_NAMES

EXECUTION_MODES = frozenset({"think", "plan", "build", "review", "train"})
RUNTIME_EVIDENCE_LEVEL = "runtime_bound_v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXECUTION_ID_RE = re.compile(r"^acrun_[0-9a-f]{20}$")

# Roles that qualify a seat to act as the challenger planner.
CHALLENGER_ROLES = frozenset({"planner", "analysis", "brain"})


def normalize_id(value: Any) -> str:
    """Lower-case and trim an id string; empty for non-strings/blank."""

    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _sha256_parts(*parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def runtime_request_sha256(packet_id: str, request: str) -> str:
    """Bind a runtime request to the validated packet id."""

    return _sha256_parts("request", packet_id, request)


def runtime_output_sha256(
    *,
    packet_id: str,
    request_sha256: str,
    execution_id: str,
    seat_name: str,
    provider_id: str,
    session_id: str,
    runtime_provider: str,
    runtime_model: str,
    output_text: str,
) -> str:
    """Bind one returned model output to its request, packet, and seat."""

    return _sha256_parts(
        "seat-output",
        packet_id,
        request_sha256,
        execution_id,
        seat_name,
        normalize_id(provider_id),
        normalize_id(session_id),
        normalize_id(runtime_provider),
        normalize_id(runtime_model),
        output_text,
    )


def runtime_synthesis_sha256(
    *,
    packet_id: str,
    request_sha256: str,
    planner_primary_sha256: str,
    planner_challenger_sha256: str,
    synthesis_text: str,
) -> str:
    """Bind the synthesis to both planner outputs and the original request."""

    return _sha256_parts(
        "synthesis",
        packet_id,
        request_sha256,
        planner_primary_sha256,
        planner_challenger_sha256,
        synthesis_text,
    )


def _provider_family(provider_id: str) -> str:
    """Classify a normalized provider id into a coarse family for preferences."""

    pid = provider_id
    if "grok" in pid or "xai" in pid:
        return "grok"
    if "opus" in pid or "claude" in pid or "anthropic" in pid:
        return "opus"
    if "codex" in pid or "gpt" in pid or "openai" in pid:
        return "codex"
    if "gemini" in pid or "google" in pid:
        return "gemini"
    return pid or "unknown"


def provider_family(provider_id: Any) -> str:
    """Public classifier: derive the coarse provider family from any id value.

    Normalizes the id first, so callers derive the family from the provider id
    itself rather than trusting a caller-supplied family field.
    """

    return _provider_family(normalize_id(provider_id))


def required_seat_names(execution_mode: Any) -> tuple[str, ...]:
    """Return the active seat contract for one execution mode.

    Thinking, planning, review, and training need the cross-provider planner
    pair. Only build work activates the separate worker/reviewer pair.
    """

    mode = normalize_id(execution_mode)
    if mode not in EXECUTION_MODES:
        raise ValueError(f"unsupported execution_mode: {mode or '<empty>'}")
    return BUILD_SEAT_NAMES if mode == "build" else PLANNER_SEAT_NAMES


def is_safe_review_path(path: Any) -> bool:
    """True when path is a safe relative path under the review prefix."""

    if not isinstance(path, str) or not path.strip():
        return False
    candidate = path.strip()
    if candidate.startswith("/"):
        return False
    parts = candidate.split("/")
    if ".." in parts:
        return False
    if any(not segment for segment in parts):
        return False
    return candidate.startswith(REVIEW_WRITE_PREFIX)


def _normalize_seat_pool(seats: Any, errors: list[str]) -> list[dict[str, Any]]:
    """Validate and normalize the incoming seat pool into ordered records."""

    if not isinstance(seats, list) or not seats:
        errors.append("seats: must be a non-empty list of seat objects")
        return []

    normalized: list[dict[str, Any]] = []
    seen_sessions: set[str] = set()
    for index, seat in enumerate(seats):
        if not isinstance(seat, dict):
            errors.append(f"seats[{index}]: must be an object")
            continue
        provider_id = normalize_id(seat.get("provider_id"))
        session_id = normalize_id(seat.get("session_id"))
        if not provider_id:
            errors.append(f"seats[{index}]: missing provider_id")
        if not session_id:
            errors.append(f"seats[{index}]: missing session_id")
        if session_id and session_id in seen_sessions:
            errors.append(f"seats[{index}]: duplicate session_id '{session_id}'")
        if session_id:
            seen_sessions.add(session_id)
        roles_raw = seat.get("roles")
        roles = [normalize_id(r) for r in roles_raw] if isinstance(roles_raw, list) else []
        roles = [r for r in roles if r]
        healthy_raw = seat.get("healthy")
        if not isinstance(healthy_raw, bool):
            errors.append(f"seats[{index}]: 'healthy' must be a boolean")
        healthy = healthy_raw is True
        normalized.append(
            {
                "order": index,
                "provider_id": provider_id,
                "session_id": session_id,
                "healthy": healthy,
                "roles": roles,
                "provider_family": _provider_family(provider_id),
            }
        )
    return normalized


def _seat_view(seat: dict[str, Any], **extra: Any) -> dict[str, Any]:
    view = {
        "provider_id": seat["provider_id"],
        "session_id": seat["session_id"],
        "provider_family": seat["provider_family"],
        "healthy": seat["healthy"],
        "roles": list(seat["roles"]),
    }
    view.update(extra)
    return view


def assign_seats(
    seats: Any,
    current_provider_id: Any,
    current_session_id: Any,
    execution_mode: Any = "build",
) -> dict[str, Any]:
    """Assign the active AI seats deterministically from the seat pool.

    Returns a dict with ``ok``, ``decision`` (assigned/blocked), ``seats`` map,
    ``policy`` reasons, and any ``errors``. Never silently downgrades: if a seat
    cannot be filled the whole decision is ``blocked``.
    """

    errors: list[str] = []
    reasons: list[str] = []
    pool = _normalize_seat_pool(seats, errors)

    mode = normalize_id(execution_mode)
    if mode not in EXECUTION_MODES:
        errors.append(
            "execution_mode: must be one of " + ", ".join(sorted(EXECUTION_MODES))
        )

    primary_provider = normalize_id(current_provider_id)
    primary_session = normalize_id(current_session_id)
    if not primary_provider:
        errors.append("current_provider_id is required")
    if not primary_session:
        errors.append("current_session_id is required")

    if errors:
        return {"ok": False, "decision": "blocked", "seats": {}, "policy": reasons, "errors": errors}

    # Primary planner: exact match on the current provider+session.
    primary = next(
        (
            s
            for s in pool
            if s["provider_id"] == primary_provider and s["session_id"] == primary_session
        ),
        None,
    )
    if primary is None:
        errors.append(
            "planner_primary: current provider/session not present in seat pool"
        )
        return {"ok": False, "decision": "blocked", "seats": {}, "policy": reasons, "errors": errors}
    if not primary["healthy"]:
        errors.append("planner_primary: current session is not healthy")
        return {"ok": False, "decision": "blocked", "seats": {}, "policy": reasons, "errors": errors}
    if not (CHALLENGER_ROLES & set(primary["roles"])):
        errors.append(
            "planner_primary: current session must support planner, analysis, or brain"
        )
        return {"ok": False, "decision": "blocked", "seats": {}, "policy": reasons, "errors": errors}

    used_sessions = {primary["session_id"]}
    reasons.append(
        f"planner_primary = current provider '{primary['provider_id']}' session '{primary['session_id']}'"
    )

    # Challenger: healthy, different provider AND session from primary.
    challenger = _pick_challenger(pool, primary, used_sessions)
    if challenger is None:
        errors.append(
            "planner_challenger: no healthy cross-provider distinct session available"
        )
        return {"ok": False, "decision": "blocked", "seats": {}, "policy": reasons, "errors": errors}
    used_sessions.add(challenger["session_id"])
    reasons.append(
        f"planner_challenger = cross-provider '{challenger['provider_id']}' (never same provider as primary)"
    )

    assigned = {
        "planner_primary": _seat_view(primary),
        "planner_challenger": _seat_view(challenger),
    }

    if mode != "build":
        reasons.append(
            f"execution_mode '{mode}' activates THINK_PAIR only; no build work is authorized"
        )
        return {
            "ok": True,
            "decision": "assigned",
            "execution_mode": mode,
            "seats": assigned,
            "policy": reasons,
            "errors": [],
        }

    # Worker: healthy, supports worker/code, unused session.
    worker = next(
        (
            s
            for s in pool
            if s["healthy"]
            and s["session_id"] not in used_sessions
            and ({"worker", "code"} & set(s["roles"]))
        ),
        None,
    )
    if worker is None:
        errors.append("worker: no healthy unused session supporting 'worker' or 'code'")
        return {"ok": False, "decision": "blocked", "seats": {}, "policy": reasons, "errors": errors}
    used_sessions.add(worker["session_id"])
    reasons.append(f"worker = '{worker['provider_id']}' supporting worker/code")

    # Reviewer: healthy, supports review, unused session, differ from worker by
    # provider_family AND session (aliases within one family count as same).
    reviewer = next(
        (
            s
            for s in pool
            if s["healthy"]
            and s["session_id"] not in used_sessions
            and "review" in s["roles"]
            and s["provider_family"] != worker["provider_family"]
        ),
        None,
    )
    if reviewer is None:
        errors.append(
            "reviewer: no healthy unused session supporting 'review' cross-provider from worker"
        )
        return {"ok": False, "decision": "blocked", "seats": {}, "policy": reasons, "errors": errors}
    used_sessions.add(reviewer["session_id"])
    reasons.append(
        f"reviewer = cross-provider '{reviewer['provider_id']}' from worker, read_only enforced"
    )

    assigned.update(
        {
            "worker": _seat_view(worker),
            "reviewer": _seat_view(reviewer, read_only=True),
        }
    )

    return {
        "ok": True,
        "decision": "assigned",
        "execution_mode": mode,
        "seats": assigned,
        "policy": reasons,
        "errors": [],
    }


def _pick_challenger(
    pool: list[dict[str, Any]],
    primary: dict[str, Any],
    used_sessions: set[str],
) -> dict[str, Any] | None:
    """Pick the challenger planner following the preference ladder.

    A candidate must be healthy, use an unused session, be a different
    provider_family than the primary (aliases within one family count as the
    same provider), and carry at least one challenger-qualifying role
    (``planner``, ``analysis``, or ``brain``). Seats that cannot plan/analyze
    (e.g. review-only or worker-only seats) are never eligible as challenger.

    Ladder: healthy Grok first; else if primary is not Opus prefer Opus; else
    if primary is Opus prefer Codex; else first qualifying distinct family in
    stable catalog (pool) order.
    """

    candidates = [
        s
        for s in pool
        if s["healthy"]
        and s["session_id"] not in used_sessions
        and s["provider_family"] != primary["provider_family"]
        and (CHALLENGER_ROLES & set(s["roles"]))
    ]
    if not candidates:
        return None

    primary_family = primary["provider_family"]

    preferred_families: list[str] = ["grok"]
    if primary_family != "opus":
        preferred_families.append("opus")
    else:
        preferred_families.append("codex")

    for family in preferred_families:
        match = next((s for s in candidates if s["provider_family"] == family), None)
        if match is not None:
            return match

    return candidates[0]


def _validate_seat_record(
    record: Any,
    label: str,
    errors: list[str],
) -> tuple[str, str] | None:
    """Validate a receipt seat record; return (provider, session) or None."""

    if not isinstance(record, dict):
        errors.append(f"{label}: must be an object")
        return None
    provider = normalize_id(record.get("provider_id"))
    session = normalize_id(record.get("session_id"))
    if not provider:
        errors.append(f"{label}: missing provider_id")
    if not session:
        errors.append(f"{label}: missing session_id")
    if not provider or not session:
        return None
    return provider, session


def validate_work_receipt(receipt: Any, expected_packet: Any = None) -> dict[str, Any]:
    """Validate a Work Receipt against its original Work Packet.

    A receipt without the original packet is intentionally rejected. Structural
    validity alone cannot prove that its mode and seat identities belong to the
    packet id it claims.
    """

    errors: list[str] = []
    if not isinstance(receipt, dict):
        return {"ok": False, "code": "receipt_invalid", "errors": ["receipt must be an object"]}

    if not isinstance(expected_packet, dict):
        return {
            "ok": False,
            "code": "receipt_packet_required",
            "errors": ["expected_packet is required to bind the receipt to its Work Packet"],
        }

    required = (
        "packet_id",
        "execution_mode",
        "seats",
        "seat_evidence",
        "synthesis",
        "skills_used",
        "gate_results",
        "candidate_links",
        "created_at",
        "version",
    )
    for field in required:
        if field not in receipt:
            errors.append(f"receipt: missing field '{field}'")

    evidence_level = receipt.get("evidence_level", "structural_only")
    runtime_markers_present = any(
        field in receipt
        for field in (
            "execution_id",
            "request",
            "request_sha256",
            "synthesis_sha256",
        )
    )
    raw_seat_evidence = receipt.get("seat_evidence")
    if isinstance(raw_seat_evidence, dict):
        runtime_markers_present = runtime_markers_present or any(
            isinstance(record, dict)
            and any(
                field in record
                for field in (
                    "output_sha256",
                    "output_text",
                    "runtime_provider",
                    "runtime_model",
                    "resumable",
                )
            )
            for record in raw_seat_evidence.values()
        )
    runtime_bound = evidence_level == RUNTIME_EVIDENCE_LEVEL
    if evidence_level not in {"structural_only", RUNTIME_EVIDENCE_LEVEL}:
        errors.append(
            "receipt: 'evidence_level' must be structural_only or "
            + RUNTIME_EVIDENCE_LEVEL
        )
    if runtime_markers_present and not runtime_bound:
        errors.append(
            "receipt: runtime evidence cannot be downgraded to structural_only"
        )
    if runtime_bound:
        for field in (
            "execution_id",
            "request",
            "request_sha256",
            "synthesis_sha256",
        ):
            if field not in receipt:
                errors.append(f"receipt: missing runtime field '{field}'")

    if receipt.get("version") != RECEIPT_SCHEMA_VERSION:
        errors.append(
            "receipt: 'version' must be " + RECEIPT_SCHEMA_VERSION
        )

    packet_id = receipt.get("packet_id")
    if not isinstance(packet_id, str) or not packet_id.strip():
        errors.append("receipt: 'packet_id' must be a non-empty string")

    execution_mode = normalize_id(receipt.get("execution_mode"))
    try:
        active_seat_names = required_seat_names(execution_mode)
    except ValueError:
        errors.append(
            "receipt: 'execution_mode' must be one of "
            + ", ".join(sorted(EXECUTION_MODES))
        )
        active_seat_names = ()

    seats = receipt.get("seats")
    seat_pairs: dict[str, tuple[str, str]] = {}
    if not isinstance(seats, dict):
        errors.append("receipt: 'seats' must be an object with the active seat records")
    else:
        unexpected_seats = sorted(set(seats) - set(active_seat_names))
        if unexpected_seats:
            errors.append(
                "receipt.seats: inactive or unknown seat(s) for execution_mode "
                f"'{execution_mode}': " + ", ".join(unexpected_seats)
            )
        for name in active_seat_names:
            if name not in seats:
                errors.append(f"receipt.seats: missing seat '{name}'")
                continue
            pair = _validate_seat_record(seats[name], f"receipt.seats.{name}", errors)
            if pair is not None:
                seat_pairs[name] = pair

    if active_seat_names and len(seat_pairs) == len(active_seat_names):
        sessions = [pair[1] for pair in seat_pairs.values()]
        if len(set(sessions)) != len(sessions):
            errors.append("receipt.seats: all active session ids must be unique")

        p_primary = seat_pairs["planner_primary"]
        p_challenger = seat_pairs["planner_challenger"]
        if _provider_family(p_primary[0]) == _provider_family(p_challenger[0]):
            errors.append("receipt.seats: planner pair must be cross-provider")

        if execution_mode == "build":
            worker = seat_pairs["worker"]
            reviewer = seat_pairs["reviewer"]
            if _provider_family(worker[0]) == _provider_family(reviewer[0]):
                errors.append("receipt.seats: worker and reviewer must be cross-provider")
            if worker[1] == reviewer[1]:
                errors.append("receipt.seats: worker and reviewer must use different sessions")

            reviewer_record = seats.get("reviewer") if isinstance(seats, dict) else None
            if not (
                isinstance(reviewer_record, dict)
                and reviewer_record.get("read_only") is True
            ):
                errors.append("receipt.seats.reviewer: must be marked read_only:true")

    for field in ("skills_used", "gate_results", "candidate_links"):
        value = receipt.get(field)
        if field in receipt and not isinstance(value, list):
            errors.append(f"receipt: '{field}' must be a list")

    links = receipt.get("candidate_links")
    if isinstance(links, list):
        for index, link in enumerate(links):
            if not is_safe_review_path(link):
                errors.append(
                    f"receipt.candidate_links[{index}]: must be a safe relative path under {REVIEW_WRITE_PREFIX}"
                )

    expected_packet_id = expected_packet.get("packet_id")
    if packet_id != expected_packet_id:
        errors.append("receipt: 'packet_id' must match expected_packet.packet_id")

    expected_mode = normalize_id(expected_packet.get("execution_mode"))
    if execution_mode != expected_mode:
        errors.append("receipt: 'execution_mode' must match expected_packet.execution_mode")

    execution_id = receipt.get("execution_id")
    request = receipt.get("request")
    request_sha256 = receipt.get("request_sha256")
    if runtime_bound:
        if not isinstance(execution_id, str) or not _EXECUTION_ID_RE.fullmatch(execution_id):
            errors.append("receipt: 'execution_id' must match acrun_<20 lowercase hex>")
        if not isinstance(request, str) or not request.strip():
            errors.append("receipt: 'request' must be a non-empty string")
        if not isinstance(request_sha256, str) or not _SHA256_RE.fullmatch(request_sha256):
            errors.append("receipt: 'request_sha256' must be a lowercase SHA-256")
        elif isinstance(packet_id, str) and isinstance(request, str):
            expected_request_sha256 = runtime_request_sha256(packet_id, request)
            if request_sha256 != expected_request_sha256:
                errors.append(
                    "receipt: 'request_sha256' does not bind request to packet_id"
                )

    expected_seats = expected_packet.get("seats")
    if not isinstance(expected_seats, dict):
        errors.append("expected_packet: 'seats' must be an object")
    elif active_seat_names:
        for name in active_seat_names:
            receipt_record = seats.get(name) if isinstance(seats, dict) else None
            expected_record = expected_seats.get(name)
            receipt_pair = (
                normalize_id(receipt_record.get("provider_id")),
                normalize_id(receipt_record.get("session_id")),
            ) if isinstance(receipt_record, dict) else ("", "")
            expected_pair = (
                normalize_id(expected_record.get("provider_id")),
                normalize_id(expected_record.get("session_id")),
            ) if isinstance(expected_record, dict) else ("", "")
            if receipt_pair != expected_pair:
                errors.append(
                    f"receipt.seats.{name}: provider/session must match expected packet"
                )

    seat_evidence = receipt.get("seat_evidence")
    if not isinstance(seat_evidence, dict):
        errors.append("receipt: 'seat_evidence' must be an object")
    else:
        output_refs: list[str] = []
        unexpected_evidence = sorted(set(seat_evidence) - set(active_seat_names))
        if unexpected_evidence:
            errors.append(
                "receipt.seat_evidence: inactive or unknown seat(s): "
                + ", ".join(unexpected_evidence)
            )
        for name in active_seat_names:
            evidence = seat_evidence.get(name)
            if not isinstance(evidence, dict):
                errors.append(f"receipt.seat_evidence.{name}: must be an object")
                continue
            seat = seats.get(name) if isinstance(seats, dict) else None
            for field in ("provider_id", "session_id"):
                if normalize_id(evidence.get(field)) != normalize_id(
                    seat.get(field) if isinstance(seat, dict) else None
                ):
                    errors.append(
                        f"receipt.seat_evidence.{name}.{field}: must match receipt seat"
                    )
            output_ref = evidence.get("output_ref")
            if not isinstance(output_ref, str) or not output_ref.strip():
                errors.append(
                    f"receipt.seat_evidence.{name}.output_ref: must be non-empty"
                )
            else:
                output_refs.append(output_ref.strip())
            if runtime_bound:
                output_text = evidence.get("output_text")
                output_sha256 = evidence.get("output_sha256")
                runtime_provider = evidence.get("runtime_provider")
                runtime_model = evidence.get("runtime_model")
                if not isinstance(output_text, str) or not output_text.strip():
                    errors.append(
                        f"receipt.seat_evidence.{name}.output_text: must be non-empty"
                    )
                if not isinstance(output_sha256, str) or not _SHA256_RE.fullmatch(
                    output_sha256
                ):
                    errors.append(
                        f"receipt.seat_evidence.{name}.output_sha256: must be a lowercase SHA-256"
                    )
                if not isinstance(runtime_provider, str) or not runtime_provider.strip():
                    errors.append(
                        f"receipt.seat_evidence.{name}.runtime_provider: must be non-empty"
                    )
                if not isinstance(runtime_model, str) or not runtime_model.strip():
                    errors.append(
                        f"receipt.seat_evidence.{name}.runtime_model: must be non-empty"
                    )
                elif isinstance(seat, dict) and provider_family(runtime_model) != provider_family(
                    seat.get("provider_id")
                ):
                    errors.append(
                        f"receipt.seat_evidence.{name}.runtime_model: family must match packet seat"
                    )
                expected_ref = f"agent-center://execution/{execution_id}/seat/{name}"
                if output_ref != expected_ref:
                    errors.append(
                        f"receipt.seat_evidence.{name}.output_ref: must bind execution and seat"
                    )
                if all(
                    isinstance(value, str) and value
                    for value in (
                        packet_id,
                        request_sha256,
                        execution_id,
                        runtime_provider,
                        runtime_model,
                        output_text,
                    )
                ) and isinstance(seat, dict):
                    expected_output_sha256 = runtime_output_sha256(
                        packet_id=packet_id,
                        request_sha256=request_sha256,
                        execution_id=execution_id,
                        seat_name=name,
                        provider_id=seat.get("provider_id", ""),
                        session_id=seat.get("session_id", ""),
                        runtime_provider=runtime_provider,
                        runtime_model=runtime_model,
                        output_text=output_text,
                    )
                    if output_sha256 != expected_output_sha256:
                        errors.append(
                            f"receipt.seat_evidence.{name}.output_sha256: does not bind runtime output"
                        )
        if len(output_refs) != len(set(output_refs)):
            errors.append("receipt.seat_evidence: output_ref must be unique per active seat")

    synthesis = receipt.get("synthesis")
    if not isinstance(synthesis, str) or not synthesis.strip():
        errors.append("receipt: 'synthesis' must be a non-empty string")

    if runtime_bound:
        synthesis_sha256 = receipt.get("synthesis_sha256")
        if not isinstance(synthesis_sha256, str) or not _SHA256_RE.fullmatch(
            synthesis_sha256
        ):
            errors.append("receipt: 'synthesis_sha256' must be a lowercase SHA-256")
        elif isinstance(seat_evidence, dict) and isinstance(synthesis, str):
            primary_evidence = seat_evidence.get("planner_primary")
            challenger_evidence = seat_evidence.get("planner_challenger")
            primary_sha = (
                primary_evidence.get("output_sha256")
                if isinstance(primary_evidence, dict)
                else None
            )
            challenger_sha = (
                challenger_evidence.get("output_sha256")
                if isinstance(challenger_evidence, dict)
                else None
            )
            if all(
                isinstance(value, str) and value
                for value in (
                    packet_id,
                    request_sha256,
                    primary_sha,
                    challenger_sha,
                )
            ):
                expected_synthesis_sha256 = runtime_synthesis_sha256(
                    packet_id=packet_id,
                    request_sha256=request_sha256,
                    planner_primary_sha256=primary_sha,
                    planner_challenger_sha256=challenger_sha,
                    synthesis_text=synthesis,
                )
                if synthesis_sha256 != expected_synthesis_sha256:
                    errors.append(
                        "receipt: 'synthesis_sha256' does not bind both planner outputs"
                    )

    if errors:
        return {"ok": False, "code": "receipt_invalid", "errors": errors}
    return {
        "ok": True,
        "code": (
            "receipt_runtime_valid" if runtime_bound else "receipt_structural_valid"
        ),
        "packet_id": packet_id.strip(),
        "evidence_level": evidence_level,
    }
