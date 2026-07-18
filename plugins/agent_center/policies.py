"""Provider/session seat policy and work-receipt validation.

Assigns four AI seats (planner_primary, planner_challenger, worker, reviewer)
deterministically from a pool of provider/session "seats", enforcing
never-same-provider cross-checks and unique sessions. Also validates a returned
Work Receipt without persisting anything.

Standard library only. No writes, no network, no clock, no randomness.
"""

from __future__ import annotations

from typing import Any


REVIEW_WRITE_PREFIX = "95-Inbox-Lab/review/"

SEAT_NAMES = ("planner_primary", "planner_challenger", "worker", "reviewer")

# Roles that qualify a seat to act as the challenger planner.
CHALLENGER_ROLES = frozenset({"planner", "analysis", "brain"})


def normalize_id(value: Any) -> str:
    """Lower-case and trim an id string; empty for non-strings/blank."""

    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _provider_family(provider_id: str) -> str:
    """Classify a normalized provider id into a coarse family for preferences."""

    pid = provider_id
    if "grok" in pid:
        return "grok"
    if "opus" in pid or "claude" in pid:
        return "opus"
    if "codex" in pid or "gpt" in pid or "openai" in pid:
        return "codex"
    return pid or "unknown"


def provider_family(provider_id: Any) -> str:
    """Public classifier: derive the coarse provider family from any id value.

    Normalizes the id first, so callers derive the family from the provider id
    itself rather than trusting a caller-supplied family field.
    """

    return _provider_family(normalize_id(provider_id))


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
        normalized.append(
            {
                "order": index,
                "provider_id": provider_id,
                "session_id": session_id,
                "healthy": bool(seat.get("healthy", False)),
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
) -> dict[str, Any]:
    """Assign the four AI seats deterministically from the seat pool.

    Returns a dict with ``ok``, ``decision`` (assigned/blocked), ``seats`` map,
    ``policy`` reasons, and any ``errors``. Never silently downgrades: if a seat
    cannot be filled the whole decision is ``blocked``.
    """

    errors: list[str] = []
    reasons: list[str] = []
    pool = _normalize_seat_pool(seats, errors)

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

    assigned = {
        "planner_primary": _seat_view(primary),
        "planner_challenger": _seat_view(challenger),
        "worker": _seat_view(worker),
        "reviewer": _seat_view(reviewer, read_only=True),
    }

    return {
        "ok": True,
        "decision": "assigned",
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


def validate_work_receipt(receipt: Any) -> dict[str, Any]:
    """Validate a returned Work Receipt (no persistence). Returns a report."""

    errors: list[str] = []
    if not isinstance(receipt, dict):
        return {"ok": False, "code": "receipt_invalid", "errors": ["receipt must be an object"]}

    required = (
        "packet_id",
        "seats",
        "skills_used",
        "gate_results",
        "candidate_links",
        "created_at",
        "version",
    )
    for field in required:
        if field not in receipt:
            errors.append(f"receipt: missing field '{field}'")

    packet_id = receipt.get("packet_id")
    if not isinstance(packet_id, str) or not packet_id.strip():
        errors.append("receipt: 'packet_id' must be a non-empty string")

    seats = receipt.get("seats")
    seat_pairs: dict[str, tuple[str, str]] = {}
    if not isinstance(seats, dict):
        errors.append("receipt: 'seats' must be an object with four seat records")
    else:
        for name in SEAT_NAMES:
            if name not in seats:
                errors.append(f"receipt.seats: missing seat '{name}'")
                continue
            pair = _validate_seat_record(seats[name], f"receipt.seats.{name}", errors)
            if pair is not None:
                seat_pairs[name] = pair

    if len(seat_pairs) == len(SEAT_NAMES):
        sessions = [pair[1] for pair in seat_pairs.values()]
        if len(set(sessions)) != len(sessions):
            errors.append("receipt.seats: all four session ids must be unique")

        p_primary = seat_pairs["planner_primary"]
        p_challenger = seat_pairs["planner_challenger"]
        if _provider_family(p_primary[0]) == _provider_family(p_challenger[0]):
            errors.append("receipt.seats: planner pair must be cross-provider")

        worker = seat_pairs["worker"]
        reviewer = seat_pairs["reviewer"]
        if _provider_family(worker[0]) == _provider_family(reviewer[0]):
            errors.append("receipt.seats: worker and reviewer must be cross-provider")
        if worker[1] == reviewer[1]:
            errors.append("receipt.seats: worker and reviewer must use different sessions")

        reviewer_record = seats.get("reviewer") if isinstance(seats, dict) else None
        if not (isinstance(reviewer_record, dict) and reviewer_record.get("read_only") is True):
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

    if errors:
        return {"ok": False, "code": "receipt_invalid", "errors": errors}
    return {"ok": True, "code": "receipt_valid", "packet_id": packet_id.strip()}
