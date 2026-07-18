"""Deterministic tests for the bundled ``agent_center`` plugin.

Covers the catalog (counts, filters, negative cases), structured-diagnosis
routing over domains, the four-seat policy (THINK_PAIR + BUILD_REVIEW), the
Grok challenger fallback ladder, provider aliases within a family, Work Packet
build + validation, Work Receipt validation, training-candidate preparation,
the six registered tool handlers, and their error paths.

Standard library + pytest only. No writes, no network, no randomness.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import plugins.agent_center as agent_center
from plugins.agent_center import catalog, policies, routing, tools


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Shared builders — deterministic synthetic inputs
# ---------------------------------------------------------------------------

def _seat(provider_id, session_id, healthy=True, roles=None):
    """Build one seat-pool record with explicit provider/session/roles."""

    return {
        "provider_id": provider_id,
        "session_id": session_id,
        "healthy": healthy,
        "roles": list(roles) if roles else [],
    }


def _full_pool():
    """A healthy pool that satisfies all four seats across three families."""

    return [
        _seat("opus-primary", "sess-opus", roles=["planner"]),
        _seat("grok-1", "sess-grok", roles=["planner", "review"]),
        _seat("codex-worker", "sess-codex", roles=["worker", "code"]),
        _seat("opus-review", "sess-opus-2", roles=["review"]),
    ]


def _valid_diagnosis():
    """A minimal valid diagnosis using a real catalog domain."""

    domain = catalog.get_supported_domains()[0]
    return {
        "project_id": "proj-1",
        "goal": "ship the thing",
        "phase": "build",
        "domains": [domain],
        "risk_tags": [],
        "signals": [],
    }


def _valid_candidate():
    """A minimal valid training candidate."""

    return {
        "submitter": "owner",
        "project": "proj-1",
        "task": "improve routing",
        "target_type": "skill",
        "target_id": "some-skill",
        "observed_result": "worked well",
        "scope": "team",
        "privacy": "internal",
        "submitted_at": "2026-07-18",
        "feedback": "clear win",
        "evidence_refs": ["95-Inbox-Lab/review/note.md"],
        "repeat_count": 2,
    }


# ---------------------------------------------------------------------------
# Catalog — counts, filters, negatives
# ---------------------------------------------------------------------------

def test_validate_catalog_reports_expected_totals():
    report = catalog.validate_catalog()
    assert report["ok"] is True
    assert report["code"] == "catalog_valid"
    totals = report["totals"]
    assert totals["lead_agents"] == catalog.EXPECTED_LEAD_COUNT == 9
    assert totals["specialist_roles"] == catalog.EXPECTED_SPECIALIST_COUNT == 37
    assert totals["supported_domains"] == catalog.EXPECTED_DOMAIN_COUNT == 12
    assert totals["families"] == catalog.EXPECTED_FAMILY_COUNT == 12
    assert totals["skills"] == catalog.EXPECTED_SKILL_COUNT == 52


def test_validate_catalog_exposes_schema_versions():
    versions = catalog.validate_catalog()["versions"]
    for key in (
        "agents_schema_version",
        "agents_catalog_version",
        "skills_schema_version",
        "skills_catalog_version",
    ):
        assert isinstance(versions[key], str) and versions[key]


def test_supported_domains_count_and_copy():
    domains = catalog.get_supported_domains()
    assert len(domains) == 12
    # Returned list is a copy; mutating it must not corrupt the cache.
    domains.append("bogus")
    assert "bogus" not in catalog.get_supported_domains()


def test_list_agents_kind_filter_counts():
    leads = catalog.list_agents(kind="lead")
    specialists = catalog.list_agents(kind="specialist")
    assert len(leads) == 9
    assert len(specialists) == 37
    assert all(a["kind"] == "lead" for a in leads)
    assert all(a["kind"] == "specialist" for a in specialists)


def test_list_agents_all_kinds_sum():
    assert len(catalog.list_agents()) == 9 + 37


def test_list_agents_domain_filter_subset():
    domain = catalog.get_supported_domains()[0]
    filtered = catalog.list_agents(domain=domain)
    assert filtered  # at least one agent covers the first domain
    for agent in filtered:
        assert domain in agent["domain_tags"]


def test_list_agents_lead_id_filter():
    a_specialist = catalog.list_agents(kind="specialist")[0]
    lead_id = a_specialist["lead_agent_id"]
    for spec in catalog.list_agents(kind="specialist", lead_id=lead_id):
        assert spec["lead_agent_id"] == lead_id


def test_list_agents_invalid_kind_raises():
    with pytest.raises(catalog.CatalogError) as exc:
        catalog.list_agents(kind="captain")
    assert exc.value.code == "invalid_kind"


def test_list_agents_unknown_domain_raises():
    with pytest.raises(catalog.CatalogError) as exc:
        catalog.list_agents(domain="no-such-domain")
    assert exc.value.code == "unknown_domain"


def test_get_agent_found_and_missing():
    consultor = catalog.get_agent("consultor")
    assert consultor is not None
    assert consultor["kind"] == "lead"
    assert catalog.get_agent("does-not-exist") is None
    assert catalog.get_agent("") is None
    assert catalog.get_agent(None) is None


def test_get_agent_returns_independent_copy():
    first = catalog.get_agent("consultor")
    first["name_th"] = "MUTATED"
    second = catalog.get_agent("consultor")
    assert second["name_th"] != "MUTATED"


def test_list_skills_count_and_family_filter():
    all_skills = catalog.list_skills()
    assert len(all_skills) == 52
    families = catalog.list_families()
    assert len(families) == 12
    fam = families[0]["name"]
    for skill in catalog.list_skills(family=fam):
        assert skill["family"] == fam


def test_list_skills_unknown_family_raises():
    with pytest.raises(catalog.CatalogError) as exc:
        catalog.list_skills(family="ghost-family")
    assert exc.value.code == "unknown_family"


def test_list_skills_unknown_domain_raises():
    with pytest.raises(catalog.CatalogError) as exc:
        catalog.list_skills(domain="ghost-domain")
    assert exc.value.code == "unknown_domain"


# ---------------------------------------------------------------------------
# Provider family classification + aliases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "provider_id, expected",
    [
        ("grok-4", "grok"),
        ("opus-4", "opus"),
        ("claude-sonnet", "opus"),
        ("codex-mini", "codex"),
        ("gpt-5", "codex"),
        ("openai-o3", "codex"),
        ("  OPUS-Primary  ", "opus"),
        ("something-else", "something-else"),
        (None, "unknown"),
        (123, "unknown"),
    ],
)
def test_provider_family_classification(provider_id, expected):
    assert policies.provider_family(provider_id) == expected


def test_normalize_id_trims_and_lowercases():
    assert policies.normalize_id("  ABC ") == "abc"
    assert policies.normalize_id("") == ""
    assert policies.normalize_id(None) == ""
    assert policies.normalize_id(42) == ""


# ---------------------------------------------------------------------------
# Safe review path guard
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path, ok",
    [
        ("95-Inbox-Lab/review/note.md", True),
        ("95-Inbox-Lab/review/sub/deep.md", True),
        ("/95-Inbox-Lab/review/abs.md", False),
        ("95-Inbox-Lab/review/../escape.md", False),
        ("other/place/note.md", False),
        ("95-Inbox-Lab/review//blank.md", False),
        ("", False),
        (None, False),
    ],
)
def test_is_safe_review_path(path, ok):
    assert policies.is_safe_review_path(path) is ok


# ---------------------------------------------------------------------------
# Four-seat policy — happy path
# ---------------------------------------------------------------------------

def test_assign_seats_happy_path_four_unique_sessions():
    report = policies.assign_seats(_full_pool(), "opus-primary", "sess-opus")
    assert report["ok"] is True
    assert report["decision"] == "assigned"
    seats = report["seats"]
    assert set(seats) == set(policies.SEAT_NAMES)

    sessions = [seats[name]["session_id"] for name in policies.SEAT_NAMES]
    assert len(set(sessions)) == 4  # all four sessions unique

    # planner_primary is exactly the current provider/session.
    assert seats["planner_primary"]["provider_id"] == "opus-primary"
    assert seats["planner_primary"]["session_id"] == "sess-opus"

    # THINK_PAIR: planner pair must be different families.
    assert (
        seats["planner_primary"]["provider_family"]
        != seats["planner_challenger"]["provider_family"]
    )
    # BUILD_REVIEW: worker and reviewer must be different families.
    assert seats["worker"]["provider_family"] != seats["reviewer"]["provider_family"]
    # Reviewer is read-only.
    assert seats["reviewer"]["read_only"] is True


def test_assign_seats_reviewer_cross_family_from_worker():
    # worker=codex, so reviewer must not be codex; here opus review seat wins.
    report = policies.assign_seats(_full_pool(), "opus-primary", "sess-opus")
    seats = report["seats"]
    assert seats["worker"]["provider_family"] == "codex"
    assert seats["reviewer"]["provider_family"] == "opus"


# ---------------------------------------------------------------------------
# Grok challenger fallback ladder
# ---------------------------------------------------------------------------

def test_challenger_prefers_grok_when_available():
    pool = [
        _seat("opus-primary", "s1", roles=["planner"]),
        _seat("codex-c", "s2", roles=["planner"]),
        _seat("grok-c", "s3", roles=["planner"]),
        _seat("codex-worker", "s4", roles=["worker", "code"]),
        _seat("opus-review", "s5", roles=["review"]),
    ]
    report = policies.assign_seats(pool, "opus-primary", "s1")
    assert report["ok"] is True
    assert report["seats"]["planner_challenger"]["provider_family"] == "grok"


def test_challenger_falls_back_to_opus_when_primary_not_opus_and_no_grok():
    # primary is codex, no grok present -> ladder prefers opus.
    pool = [
        _seat("codex-primary", "s1", roles=["planner"]),
        _seat("opus-c", "s2", roles=["planner"]),
        _seat("codex-worker", "s3", roles=["worker", "code"]),
        _seat("opus-review", "s4", roles=["review"]),
    ]
    report = policies.assign_seats(pool, "codex-primary", "s1")
    assert report["ok"] is True
    # worker is codex, reviewer opus keeps BUILD_REVIEW valid.
    assert report["seats"]["planner_challenger"]["provider_family"] == "opus"


def test_challenger_falls_back_to_codex_when_primary_opus_and_no_grok():
    # primary is opus, no grok present -> ladder prefers codex.
    pool = [
        _seat("opus-primary", "s1", roles=["planner"]),
        _seat("codex-c", "s2", roles=["planner"]),
        _seat("codex-worker", "s3", roles=["worker", "code"]),
        _seat("opus-review", "s4", roles=["review"]),
    ]
    report = policies.assign_seats(pool, "opus-primary", "s1")
    assert report["ok"] is True
    assert report["seats"]["planner_challenger"]["provider_family"] == "codex"


def test_challenger_never_same_family_as_primary_via_alias():
    # Two opus aliases: challenger must not be the second opus alias.
    pool = [
        _seat("opus-primary", "s1", roles=["planner"]),
        _seat("claude-alias", "s2", roles=["planner"]),  # same family as primary
        _seat("codex-c", "s3", roles=["planner"]),
        _seat("codex-worker", "s4", roles=["worker", "code"]),
        _seat("opus-review", "s5", roles=["review"]),
    ]
    report = policies.assign_seats(pool, "opus-primary", "s1")
    assert report["ok"] is True
    assert report["seats"]["planner_challenger"]["provider_family"] != "opus"


def test_challenger_rejects_seats_without_challenger_role():
    # Spec: a challenger must carry a planner/analysis/brain role. Here every
    # cross-family healthy seat is review-only, so no seat qualifies and the
    # whole decision is blocked (never silently downgraded).
    pool = [
        _seat("opus-primary", "s1", roles=["planner"]),
        _seat("codex-review-only", "s2", roles=["review"]),  # no planner role
        _seat("opus-worker", "s3", roles=["worker", "code"]),
        _seat("grok-review", "s4", roles=["review"]),  # no planner role
    ]
    report = policies.assign_seats(pool, "opus-primary", "s1")
    assert report["ok"] is False
    assert report["decision"] == "blocked"
    assert report["seats"] == {}
    assert any("planner_challenger" in err for err in report["errors"])


def test_challenger_skips_unqualified_grok_and_falls_back_to_role_seat():
    # Spec + ladder: the ladder prefers grok, but this grok seat lacks a
    # challenger role, so it is skipped. The codex seat carries "brain" (a
    # challenger role) and is chosen instead, proving the role gate and the
    # fallback down the ladder both apply.
    pool = [
        _seat("opus-primary", "s1", roles=["planner"]),
        _seat("grok-review-only", "s2", roles=["review"]),  # preferred but unqualified
        _seat("codex-brain", "s3", roles=["analysis", "brain"]),
        _seat("codex-worker", "s4", roles=["worker", "code"]),
        _seat("opus-review", "s5", roles=["review"]),
    ]
    report = policies.assign_seats(pool, "opus-primary", "s1")
    assert report["ok"] is True
    challenger = report["seats"]["planner_challenger"]
    assert challenger["provider_family"] == "codex"
    assert policies.CHALLENGER_ROLES & set(challenger["roles"])


# ---------------------------------------------------------------------------
# Four-seat policy — blocked / negative cases
# ---------------------------------------------------------------------------

def test_assign_seats_blocks_on_empty_pool():
    report = policies.assign_seats([], "opus-primary", "sess-opus")
    assert report["ok"] is False
    assert report["decision"] == "blocked"
    assert report["seats"] == {}


def test_assign_seats_blocks_when_current_session_missing_from_pool():
    report = policies.assign_seats(_full_pool(), "opus-primary", "no-such-session")
    assert report["ok"] is False
    assert any("planner_primary" in e for e in report["errors"])


def test_assign_seats_blocks_when_primary_unhealthy():
    pool = [
        _seat("opus-primary", "s1", healthy=False, roles=["planner"]),
        _seat("grok-c", "s2", roles=["planner"]),
        _seat("codex-worker", "s3", roles=["worker", "code"]),
        _seat("opus-review", "s4", roles=["review"]),
    ]
    report = policies.assign_seats(pool, "opus-primary", "s1")
    assert report["ok"] is False
    assert any("not healthy" in e for e in report["errors"])


def test_assign_seats_blocks_when_no_cross_family_challenger():
    # Only opus family present besides primary aliases -> no challenger.
    pool = [
        _seat("opus-primary", "s1", roles=["planner"]),
        _seat("claude-alias", "s2", roles=["planner"]),
        _seat("opus-worker", "s3", roles=["worker", "code"]),
        _seat("opus-review", "s4", roles=["review"]),
    ]
    report = policies.assign_seats(pool, "opus-primary", "s1")
    assert report["ok"] is False
    assert any("planner_challenger" in e for e in report["errors"])


def test_assign_seats_blocks_when_no_worker_role():
    pool = [
        _seat("opus-primary", "s1", roles=["planner"]),
        _seat("grok-c", "s2", roles=["planner", "review"]),
        _seat("codex-x", "s3", roles=["review"]),  # no worker/code role
        _seat("opus-review", "s4", roles=["review"]),
    ]
    report = policies.assign_seats(pool, "opus-primary", "s1")
    assert report["ok"] is False
    assert any("worker" in e for e in report["errors"])


def test_assign_seats_blocks_when_reviewer_same_family_as_worker():
    # worker=codex and only codex review seats remain -> reviewer blocked.
    pool = [
        _seat("opus-primary", "s1", roles=["planner"]),
        _seat("grok-c", "s2", roles=["planner"]),
        _seat("codex-worker", "s3", roles=["worker", "code"]),
        _seat("codex-review", "s4", roles=["review"]),
    ]
    report = policies.assign_seats(pool, "opus-primary", "s1")
    assert report["ok"] is False
    assert any("reviewer" in e for e in report["errors"])


def test_assign_seats_blocks_on_duplicate_sessions():
    pool = [
        _seat("opus-primary", "dup", roles=["planner"]),
        _seat("grok-c", "dup", roles=["planner"]),
        _seat("codex-worker", "s3", roles=["worker", "code"]),
        _seat("opus-review", "s4", roles=["review"]),
    ]
    report = policies.assign_seats(pool, "opus-primary", "dup")
    assert report["ok"] is False
    assert any("duplicate session_id" in e for e in report["errors"])


# ---------------------------------------------------------------------------
# Diagnosis validation + routing
# ---------------------------------------------------------------------------

def test_validate_diagnosis_rejects_raw_string():
    report = routing.validate_diagnosis("please build a website")
    assert report["ok"] is False
    assert report["code"] == "diagnosis_invalid"


def test_validate_diagnosis_requires_non_empty_domains():
    diag = _valid_diagnosis()
    diag["domains"] = []
    report = routing.validate_diagnosis(diag)
    assert report["ok"] is False
    assert any("domains" in e for e in report["errors"])


def test_validate_diagnosis_rejects_unknown_domain():
    diag = _valid_diagnosis()
    diag["domains"] = ["not-a-real-domain"]
    report = routing.validate_diagnosis(diag)
    assert report["ok"] is False
    assert any("unknown domain" in e for e in report["errors"])


def test_validate_diagnosis_requires_typed_list_keys():
    diag = _valid_diagnosis()
    del diag["risk_tags"]
    report = routing.validate_diagnosis(diag)
    assert report["ok"] is False
    assert any("risk_tags" in e for e in report["errors"])


def test_validate_diagnosis_success_normalizes():
    report = routing.validate_diagnosis(_valid_diagnosis())
    assert report["ok"] is True
    assert report["code"] == "diagnosis_valid"
    norm = report["diagnosis"]
    # Optional list fields are filled in as empty lists.
    for field in routing.DIAGNOSIS_OPTIONAL_LIST_FIELDS:
        assert norm[field] == []


def test_build_team_manifest_intake_is_consultor_non_producing():
    norm = routing.validate_diagnosis(_valid_diagnosis())["diagnosis"]
    manifest = routing.build_team_manifest(norm)
    assert manifest["intake"]["id"] == "consultor"
    assert manifest["intake"]["produces_deliverables"] is False
    # Consultor is never listed among producing leads.
    assert all(lead["id"] != "consultor" for lead in manifest["leads"])


def test_build_team_manifest_selects_leads_for_domain():
    norm = routing.validate_diagnosis(_valid_diagnosis())["diagnosis"]
    manifest = routing.build_team_manifest(norm)
    # The first domain should route to at least one lead + skills.
    assert manifest["leads"]
    assert manifest["skills"]


@pytest.mark.parametrize("domain", catalog.get_supported_domains())
def test_build_team_manifest_routes_every_supported_domain(domain):
    # Every one of the 12 catalog domains must route to at least one
    # producing lead (Consultor is intake-only, never a producing lead).
    diag = _valid_diagnosis()
    diag["domains"] = [domain]
    norm = routing.validate_diagnosis(diag)["diagnosis"]
    manifest = routing.build_team_manifest(norm)
    assert manifest["leads"], f"domain {domain!r} routed to no leads"
    assert all(lead["id"] != "consultor" for lead in manifest["leads"])


def test_every_supported_domain_reaches_a_ready_work_packet():
    # End-to-end over all domains: each must assemble a valid Work Packet
    # with the same healthy four-seat pool.
    pool = _full_pool()
    for domain in catalog.get_supported_domains():
        diag = _valid_diagnosis()
        diag["domains"] = [domain]
        report = routing.build_work_packet(diag, pool, "opus-primary", "sess-opus")
        assert report["ok"] is True, f"domain {domain!r} failed to route: {report}"
        assert report["code"] == "packet_ready"


# ---------------------------------------------------------------------------
# Work Packet build + validate
# ---------------------------------------------------------------------------

def test_build_work_packet_success_is_valid_and_deterministic():
    diag = _valid_diagnosis()
    pool = _full_pool()
    first = routing.build_work_packet(diag, pool, "opus-primary", "sess-opus")
    second = routing.build_work_packet(diag, pool, "opus-primary", "sess-opus")
    assert first["ok"] is True
    assert first["code"] == "packet_ready"
    # Same inputs -> identical content-addressed packet id (deterministic).
    assert first["packet"]["packet_id"] == second["packet"]["packet_id"]
    assert first["packet"]["packet_id"].startswith("packet_")

    validated = routing.validate_work_packet(first["packet"])
    assert validated["ok"] is True
    assert validated["code"] == "packet_valid"
    assert validated["packet_id"] == first["packet"]["packet_id"]


def test_build_work_packet_blocks_on_bad_seats():
    report = routing.build_work_packet(_valid_diagnosis(), [], "opus-primary", "sess-opus")
    assert report["ok"] is False
    assert report["code"] == "seats_unassigned"


def test_build_work_packet_propagates_diagnosis_error():
    diag = _valid_diagnosis()
    diag["domains"] = ["ghost"]
    report = routing.build_work_packet(diag, _full_pool(), "opus-primary", "sess-opus")
    assert report["ok"] is False
    assert report["code"] == "diagnosis_invalid"


def test_validate_work_packet_detects_tampered_hash():
    packet = routing.build_work_packet(
        _valid_diagnosis(), _full_pool(), "opus-primary", "sess-opus"
    )["packet"]
    packet["goal"] = "tampered goal"  # body changed, id no longer matches
    report = routing.validate_work_packet(packet)
    assert report["ok"] is False
    assert any("content hash" in e for e in report["errors"])


def test_validate_work_packet_rejects_missing_fields():
    report = routing.validate_work_packet({"packet_id": "packet_x"})
    assert report["ok"] is False
    assert report["code"] == "packet_invalid"


def test_validate_work_packet_rejects_non_dict():
    report = routing.validate_work_packet("not a packet")
    assert report["ok"] is False
    assert report["code"] == "packet_invalid"


# ---------------------------------------------------------------------------
# Work Receipt validation
# ---------------------------------------------------------------------------

def _valid_receipt():
    return {
        "packet_id": "packet_abc",
        "seats": {
            "planner_primary": {"provider_id": "opus-a", "session_id": "s1"},
            "planner_challenger": {"provider_id": "grok-b", "session_id": "s2"},
            "worker": {"provider_id": "codex-c", "session_id": "s3"},
            "reviewer": {"provider_id": "opus-d", "session_id": "s4", "read_only": True},
        },
        "skills_used": [],
        "gate_results": [],
        "candidate_links": ["95-Inbox-Lab/review/candidate.md"],
        "created_at": "2026-07-18",
        "version": "1.0",
    }


def test_validate_work_receipt_success():
    report = policies.validate_work_receipt(_valid_receipt())
    assert report["ok"] is True
    assert report["code"] == "receipt_valid"
    assert report["packet_id"] == "packet_abc"


def test_validate_work_receipt_rejects_non_dict():
    report = policies.validate_work_receipt(["nope"])
    assert report["ok"] is False
    assert report["code"] == "receipt_invalid"


def test_validate_work_receipt_rejects_duplicate_sessions():
    receipt = _valid_receipt()
    receipt["seats"]["reviewer"]["session_id"] = "s3"  # collide with worker
    report = policies.validate_work_receipt(receipt)
    assert report["ok"] is False
    assert any("unique" in e for e in report["errors"])


def test_validate_work_receipt_rejects_same_family_planners():
    receipt = _valid_receipt()
    receipt["seats"]["planner_challenger"]["provider_id"] = "claude-b"  # opus family
    report = policies.validate_work_receipt(receipt)
    assert report["ok"] is False
    assert any("planner pair must be cross-provider" in e for e in report["errors"])


def test_validate_work_receipt_requires_reviewer_read_only():
    receipt = _valid_receipt()
    receipt["seats"]["reviewer"].pop("read_only")
    report = policies.validate_work_receipt(receipt)
    assert report["ok"] is False
    assert any("read_only" in e for e in report["errors"])


def test_validate_work_receipt_rejects_unsafe_candidate_link():
    receipt = _valid_receipt()
    receipt["candidate_links"] = ["../escape.md"]
    report = policies.validate_work_receipt(receipt)
    assert report["ok"] is False
    assert any("candidate_links" in e for e in report["errors"])


# ---------------------------------------------------------------------------
# Training candidate preparation
# ---------------------------------------------------------------------------

def test_prepare_training_candidate_success():
    report = routing.prepare_training_candidate(_valid_candidate())
    assert report["ok"] is True
    assert report["code"] == "training_candidate_ready"
    candidate = report["candidate"]
    assert candidate["candidate_id"].startswith("training_")
    assert candidate["owner_decision"] == "pending"
    assert candidate["promoted"] is False
    assert policies.is_safe_review_path(report["suggested_path"])
    assert report["markdown"].startswith("# Training Candidate training_")


def test_prepare_training_candidate_is_deterministic():
    a = routing.prepare_training_candidate(_valid_candidate())
    b = routing.prepare_training_candidate(_valid_candidate())
    assert a["candidate"]["candidate_id"] == b["candidate"]["candidate_id"]


def test_prepare_training_candidate_rejects_non_dict():
    report = routing.prepare_training_candidate("nope")
    assert report["ok"] is False
    assert report["code"] == "training_candidate_invalid"


def test_prepare_training_candidate_requires_evidence_refs():
    candidate = _valid_candidate()
    candidate["evidence_refs"] = []
    report = routing.prepare_training_candidate(candidate)
    assert report["ok"] is False
    assert any("evidence_refs" in e for e in report["errors"])


def test_prepare_training_candidate_rejects_bool_repeat_count():
    candidate = _valid_candidate()
    candidate["repeat_count"] = True  # bool must not pass as int
    report = routing.prepare_training_candidate(candidate)
    assert report["ok"] is False
    assert any("repeat_count" in e for e in report["errors"])


def test_prepare_training_candidate_rejects_missing_str_field():
    candidate = _valid_candidate()
    candidate["submitter"] = "  "
    report = routing.prepare_training_candidate(candidate)
    assert report["ok"] is False
    assert any("submitter" in e for e in report["errors"])


# ---------------------------------------------------------------------------
# Tool handlers (JSON string outputs) — six tools + error paths
# ---------------------------------------------------------------------------

def _tool(handler, **args):
    """Invoke a tool handler and parse its JSON string output."""

    return json.loads(handler(args))


def test_tool_list_agents_ok_and_filter():
    out = _tool(tools.agent_center_list_agents, kind="lead")
    assert out["ok"] is True
    assert out["code"] == "agents_listed"
    assert out["count"] == 9


def test_tool_list_agents_invalid_kind_reports_error():
    out = _tool(tools.agent_center_list_agents, kind="captain")
    assert out["ok"] is False
    assert out["code"] == "invalid_kind"


def test_tool_get_agent_found_missing_and_required():
    found = _tool(tools.agent_center_get_agent, agent_id="consultor")
    assert found["ok"] is True and found["code"] == "agent_found"

    missing = _tool(tools.agent_center_get_agent, agent_id="ghost")
    assert missing["ok"] is False and missing["code"] == "agent_not_found"

    required = _tool(tools.agent_center_get_agent)
    assert required["ok"] is False and required["code"] == "agent_id_required"


def test_tool_list_skills_ok():
    out = _tool(tools.agent_center_list_skills)
    assert out["ok"] is True
    assert out["code"] == "skills_listed"
    assert out["count"] == 52


def test_tool_list_skills_unknown_family_error():
    out = _tool(tools.agent_center_list_skills, family="ghost")
    assert out["ok"] is False
    assert out["code"] == "unknown_family"


def test_tool_route_ready():
    out = _tool(
        tools.agent_center_route,
        diagnosis=_valid_diagnosis(),
        seats=_full_pool(),
        current_provider_id="opus-primary",
        current_session_id="sess-opus",
    )
    assert out["ok"] is True
    assert out["code"] == "route_ready"
    assert "team" in out
    assert out["packet_report"]["ok"] is True


def test_tool_route_blocks_when_seats_missing():
    out = _tool(
        tools.agent_center_route,
        diagnosis=_valid_diagnosis(),
        seats=[],
        current_provider_id="opus-primary",
        current_session_id="sess-opus",
    )
    assert out["ok"] is False
    assert out["blocked"] is True
    assert out["code"] == "route_seats_required"


def test_tool_route_blocks_when_seats_unassigned():
    # Non-empty but unsatisfiable pool -> seats can't be assigned.
    bad_pool = [_seat("opus-primary", "s1", roles=["planner"])]
    out = _tool(
        tools.agent_center_route,
        diagnosis=_valid_diagnosis(),
        seats=bad_pool,
        current_provider_id="opus-primary",
        current_session_id="s1",
    )
    assert out["ok"] is False
    assert out["blocked"] is True
    assert out["code"] == "route_seats_unassigned"


def test_tool_route_rejects_invalid_diagnosis():
    out = _tool(
        tools.agent_center_route,
        diagnosis="raw string",
        seats=_full_pool(),
        current_provider_id="opus-primary",
        current_session_id="sess-opus",
    )
    assert out["ok"] is False
    assert out["code"] == "diagnosis_invalid"


def test_tool_prepare_training_candidate():
    out = _tool(tools.agent_center_prepare_training_candidate, candidate=_valid_candidate())
    assert out["ok"] is True
    assert out["code"] == "training_candidate_ready"


def test_tool_validate_catalog_when_neither_supplied():
    out = _tool(tools.agent_center_validate)
    assert out["ok"] is True
    assert out["code"] == "catalog_valid"
    assert out["totals"]["skills"] == 52


def test_tool_validate_packet_only():
    packet = routing.build_work_packet(
        _valid_diagnosis(), _full_pool(), "opus-primary", "sess-opus"
    )["packet"]
    out = _tool(tools.agent_center_validate, packet=packet)
    assert out["ok"] is True
    assert out["code"] == "packet_valid"


def test_tool_validate_receipt_only():
    out = _tool(tools.agent_center_validate, receipt=_valid_receipt())
    assert out["ok"] is True
    assert out["code"] == "receipt_valid"


def test_tool_validate_rejects_both_packet_and_receipt():
    out = _tool(tools.agent_center_validate, packet={}, receipt={})
    assert out["ok"] is False
    assert out["code"] == "validate_ambiguous"


def test_tool_outputs_are_sorted_json_strings():
    raw = tools.agent_center_validate({})
    assert isinstance(raw, str)
    # sort_keys=True -> re-serializing parsed output yields identical bytes.
    assert raw == json.dumps(json.loads(raw), ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
# Bundled skill and team-shortcuts payload
# ---------------------------------------------------------------------------

def test_agent_center_skill_payload_is_byte_identical():
    source = REPO_ROOT / "skills" / "agent-center" / "SKILL.md"
    payload = (
        REPO_ROOT
        / "team-shortcuts"
        / "payload"
        / "skills"
        / "agent-center"
        / "SKILL.md"
    )
    assert source.read_bytes() == payload.read_bytes()


def test_agent_center_metadata_payload_is_byte_identical():
    source = REPO_ROOT / "skills" / "agent-center" / "agents" / "openai.yaml"
    payload = (
        REPO_ROOT
        / "team-shortcuts"
        / "payload"
        / "skills"
        / "agent-center"
        / "agents"
        / "openai.yaml"
    )
    assert source.read_bytes() == payload.read_bytes()


def test_agent_center_skill_frontmatter_and_tools():
    skill = (REPO_ROOT / "skills" / "agent-center" / "SKILL.md").read_text()
    frontmatter = skill.split("---", 2)[1]
    keys = {
        line.split(":", 1)[0]
        for line in frontmatter.splitlines()
        if ":" in line
    }
    assert keys == {"name", "description"}
    for tool_name in (
        "agent_center_list_agents",
        "agent_center_get_agent",
        "agent_center_list_skills",
        "agent_center_route",
        "agent_center_prepare_training_candidate",
        "agent_center_validate",
    ):
        assert tool_name in skill


def test_agent_center_skill_is_fail_closed_and_review_before_write():
    skill = (REPO_ROOT / "skills" / "agent-center" / "SKILL.md").read_text()
    assert "CURRENT_WORKSPACE_BLOCKED" in skill
    assert "Do not replace catalog results with a team invented from memory." in skill
    assert "Do not write it or promote it automatically." in skill
    assert "owner approval" in skill
    assert "Treat `Use AI Relay` as optional." in skill


def test_plugin_registers_exactly_six_agent_center_tools():
    registered = []

    class Context:
        def register_tool(self, **entry):
            registered.append(entry)

    agent_center.register(Context())

    assert [entry["name"] for entry in registered] == [
        "agent_center_list_agents",
        "agent_center_get_agent",
        "agent_center_list_skills",
        "agent_center_route",
        "agent_center_prepare_training_candidate",
        "agent_center_validate",
    ]
    assert all(entry["toolset"] == "agent_center" for entry in registered)
    assert all(callable(entry["handler"]) for entry in registered)


def test_use_agent_creative_web_design_pilot():
    diagnosis = {
        "project_id": "sample-web",
        "goal": "design a new public service page",
        "phase": "design",
        "domains": ["creative-brand", "ux", "ui-web-design"],
        "risk_tags": ["brand-drift"],
        "signals": ["public-site"],
        "project_context_refs": [".project/plan.md"],
        "allowed_paths": ["apps/web/**"],
        "forbidden_actions": ["deploy production"],
        "deliverables": ["team manifest", "work packet"],
        "evidence_gates": ["visual review"],
    }
    out = _tool(
        tools.agent_center_route,
        diagnosis=diagnosis,
        seats=_full_pool(),
        current_provider_id="opus-primary",
        current_session_id="sess-opus",
    )

    assert out["ok"] is True
    assert out["code"] == "route_ready"
    lead_ids = {lead["id"] for lead in out["team"]["leads"]}
    assert {"experience-design-lead", "creative-brand-lead"} <= lead_ids
    packet = out["packet_report"]["packet"]
    assert packet["packet_id"].startswith("packet_")
    assert routing.validate_work_packet(packet)["ok"] is True
    receipt = {
        "packet_id": packet["packet_id"],
        "seats": packet["seats"],
        "skills_used": [skill["name"] for skill in out["team"]["skills"]],
        "gate_results": ["visual review required before a UI completion claim"],
        "candidate_links": [],
        "created_at": "2026-07-18",
        "version": "1.0",
    }
    assert policies.validate_work_receipt(receipt)["code"] == "receipt_valid"


def test_use_agent_web_engine_pilot_selects_web_engine_as_core_team():
    diagnosis = {
        "project_id": "enterprise-web-engine",
        "goal": "extend a large multi-tenant web engine with reusable page modules",
        "phase": "build",
        "domains": ["web-engine", "engineering"],
        "risk_tags": ["tenant-isolation", "shared-module-regression"],
        "signals": ["multi-tenant", "page-builder", "large-application"],
        "project_context_refs": [".project/spec/UAG.md"],
        "allowed_paths": ["plugins/agent_center/**"],
        "forbidden_actions": ["change provider adapters", "deploy production"],
        "deliverables": ["team manifest", "work packet"],
        "evidence_gates": ["targeted tests", "catalog validation"],
    }
    out = _tool(
        tools.agent_center_route,
        diagnosis=diagnosis,
        seats=_full_pool(),
        current_provider_id="opus-primary",
        current_session_id="sess-opus",
    )

    assert out["ok"] is True
    assert out["code"] == "route_ready"
    lead_ids = [lead["id"] for lead in out["team"]["leads"]]
    assert lead_ids[0] == "web-engine-lead"
    assert "application-engineering-lead" in lead_ids
    specialist_ids = {specialist["id"] for specialist in out["team"]["specialists"]}
    assert "web-engine-architect" in specialist_ids
    selected_skills = {skill["name"] for skill in out["team"]["skills"]}
    assert {"multi-tenant-web", "page-builder", "reusable-module-design"} <= selected_skills
    packet = out["packet_report"]["packet"]
    assert packet["domains"] == ["web-engine", "engineering"]
    assert routing.validate_work_packet(packet)["code"] == "packet_valid"
    receipt = {
        "packet_id": packet["packet_id"],
        "seats": packet["seats"],
        "skills_used": sorted(selected_skills),
        "gate_results": ["targeted tests", "catalog validation"],
        "candidate_links": [],
        "created_at": "2026-07-18",
        "version": "1.0",
    }
    assert policies.validate_work_receipt(receipt)["code"] == "receipt_valid"


def test_use_agent_shortcut_and_skill_are_connected():
    skill = (REPO_ROOT / "skills/agent-center/SKILL.md").read_text(encoding="utf-8")
    prompt_root = REPO_ROOT / "team-shortcuts/payload/skills/prompt-shortcuts"
    prompt = (prompt_root / "references/use-agent.md").read_text(encoding="utf-8")
    shortcut_skill = (prompt_root / "SKILL.md").read_text(encoding="utf-8")
    shortcut_index = (prompt_root / "Prompt Shortcuts.md").read_text(encoding="utf-8")
    registry = (
        REPO_ROOT / "team-shortcuts/payload/ai-context/prompt-shortcut-registry.md"
    ).read_text(encoding="utf-8")

    assert "TODO" not in skill
    assert skill.startswith("---\nname: agent-center\n")
    assert "Use Agent" in skill
    assert "`Use AI Relay` as optional" in skill
    assert "Use AI Relay เฉพาะเมื่อเจ้าของเรียกชัดเจน" in prompt
    assert shortcut_skill.count("Use Agent") >= 3
    assert shortcut_skill.count("| `Use Agent` |") == 1
    assert shortcut_index.count("| `Use Agent` |") == 1
    assert registry.count("| `Use Agent` |") == 1
