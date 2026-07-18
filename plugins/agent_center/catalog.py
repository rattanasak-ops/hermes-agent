"""Agent Center catalog loader and validator.

Loads the immutable agents/skills catalog shipped with this plugin, validates
it fail-closed with structured errors, and exposes read-only list/filter/get
helpers. Every public result is an independent deep copy so callers can never
mutate cached catalog state.

Standard library only. No writes, no network, no clock, no randomness.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


_DATA_DIR = Path(__file__).resolve().parent / "data"
_AGENTS_PATH = _DATA_DIR / "agents.json"
_SKILLS_PATH = _DATA_DIR / "skills.json"

EXPECTED_LEAD_COUNT = 9
EXPECTED_SPECIALIST_COUNT = 37
EXPECTED_DOMAIN_COUNT = 12
EXPECTED_FAMILY_COUNT = 12
EXPECTED_SKILL_COUNT = 52

_PLACEHOLDER_TOKENS = {"todo", "tbd", "placeholder", "n/a", "none", "changeme"}

LEAD_REQUIRED_FIELDS = (
    "id",
    "name_th",
    "mission",
    "activates_when",
    "must_not_use_when",
    "owned_outcomes",
    "required_inputs",
    "project_context",
    "skills_required",
    "skills_optional",
    "allowed_tools",
    "write_policy",
    "deliverables",
    "acceptance_gates",
    "reviewer_policy",
    "memory_scope",
    "ai_preferences",
    "metrics",
    "version",
    "domain_tags",
    "routing_priority",
)

SPECIALIST_REQUIRED_FIELDS = (
    "id",
    "name_th",
    "group",
    "lead_agent_id",
    "domain_tags",
    "activates_when",
    "must_not_use_when",
    "skills_required",
    "deliverables",
    "acceptance_gates",
    "reviewer_policy",
    "version",
)

SKILL_REQUIRED_FIELDS = (
    "name",
    "family",
    "name_th",
    "domain_tags",
    "description",
    "triggers",
    "not_for",
    "required_inputs",
    "steps",
    "deliverables",
    "evidence",
    "allowed_tools",
    "risks",
    "examples",
    "training_metrics",
    "version",
)

FAMILY_REQUIRED_FIELDS = (
    "name",
    "name_th",
    "domain",
    "skills",
)

# Fields whose values may legitimately be empty (skills_optional can be empty).
_ALLOW_EMPTY_FIELDS = {"skills_optional"}


class CatalogError(Exception):
    """Structured, fail-closed catalog error.

    Carries a machine code plus a list of human-readable problem strings so
    tools can surface a clear ``ok:false`` payload without leaking tracebacks.
    """

    def __init__(self, code: str, errors: list[str]) -> None:
        self.code = code
        self.errors = list(errors)
        super().__init__(f"{code}: {'; '.join(self.errors)}")


def _is_meaningful(value: Any) -> bool:
    """Return True when a value is present and not a placeholder.

    Recursive: lists/dicts must be non-empty with every member meaningful.
    Strings must be non-blank and not a known placeholder token. Booleans and
    numbers count as meaningful (including 0 / False, which are real values).
    """

    if value is None:
        return False
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return False
        return stripped.lower() not in _PLACEHOLDER_TOKENS
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, (list, tuple)):
        if not value:
            return False
        return all(_is_meaningful(item) for item in value)
    if isinstance(value, dict):
        if not value:
            return False
        return all(_is_meaningful(item) for item in value.values())
    return True


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise CatalogError("file_missing", [f"catalog file not found: {path.name}"])
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogError("file_unreadable", [f"cannot read {path.name}: {exc}"]) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CatalogError("file_malformed", [f"invalid JSON in {path.name}: {exc}"]) from exc
    if not isinstance(data, dict):
        raise CatalogError("file_malformed", [f"{path.name} must contain a JSON object"])
    return data


def _check_required_fields(
    record: dict[str, Any],
    required: tuple[str, ...],
    label: str,
    errors: list[str],
) -> None:
    for field in required:
        if field not in record:
            errors.append(f"{label}: missing field '{field}'")
            continue
        if field in _ALLOW_EMPTY_FIELDS:
            continue
        if not _is_meaningful(record[field]):
            errors.append(f"{label}: field '{field}' is empty or placeholder")


def _validate_agents(agents: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    for key in ("schema_version", "catalog_version", "supported_domains", "lead_agents", "specialist_roles"):
        if key not in agents:
            errors.append(f"agents.json: missing top-level key '{key}'")

    domains = agents.get("supported_domains")
    if not isinstance(domains, list):
        errors.append("agents.json: 'supported_domains' must be a list")
        domains = []
    if len(domains) != EXPECTED_DOMAIN_COUNT:
        errors.append(
            f"agents.json: expected {EXPECTED_DOMAIN_COUNT} supported_domains, found {len(domains)}"
        )
    domain_set = set(domains)
    if len(domain_set) != len(domains):
        errors.append("agents.json: duplicate domain id in supported_domains")

    leads = agents.get("lead_agents")
    if not isinstance(leads, list):
        errors.append("agents.json: 'lead_agents' must be a list")
        leads = []
    if len(leads) != EXPECTED_LEAD_COUNT:
        errors.append(f"agents.json: expected {EXPECTED_LEAD_COUNT} lead_agents, found {len(leads)}")

    specialists = agents.get("specialist_roles")
    if not isinstance(specialists, list):
        errors.append("agents.json: 'specialist_roles' must be a list")
        specialists = []
    if len(specialists) != EXPECTED_SPECIALIST_COUNT:
        errors.append(
            f"agents.json: expected {EXPECTED_SPECIALIST_COUNT} specialist_roles, found {len(specialists)}"
        )

    # Collected (label, skill_name) references for cross-check against the
    # skills catalog, which is validated after agents in _build_catalog.
    skill_refs: list[tuple[str, str]] = []

    def _collect_skill_refs(record: dict[str, Any], label: str, fields: tuple[str, ...]) -> None:
        for field_name in fields:
            values = record.get(field_name)
            if not isinstance(values, list):
                continue
            for ref in values:
                if isinstance(ref, str) and ref:
                    skill_refs.append((label, ref))

    lead_ids: set[str] = set()
    for index, lead in enumerate(leads):
        if not isinstance(lead, dict):
            errors.append(f"lead_agents[{index}]: must be an object")
            continue
        label = f"lead '{lead.get('id', index)}'"
        _check_required_fields(lead, LEAD_REQUIRED_FIELDS, label, errors)
        lead_id = lead.get("id")
        if isinstance(lead_id, str) and lead_id:
            if lead_id in lead_ids:
                errors.append(f"{label}: duplicate lead id")
            lead_ids.add(lead_id)
        _collect_skill_refs(lead, label, ("skills_required", "skills_optional"))
        for tag in lead.get("domain_tags", []) if isinstance(lead.get("domain_tags"), list) else []:
            if tag not in domain_set:
                errors.append(f"{label}: domain_tag '{tag}' not in supported_domains")

    spec_ids: set[str] = set()
    for index, spec in enumerate(specialists):
        if not isinstance(spec, dict):
            errors.append(f"specialist_roles[{index}]: must be an object")
            continue
        label = f"specialist '{spec.get('id', index)}'"
        _check_required_fields(spec, SPECIALIST_REQUIRED_FIELDS, label, errors)
        spec_id = spec.get("id")
        if isinstance(spec_id, str) and spec_id:
            if spec_id in spec_ids:
                errors.append(f"{label}: duplicate specialist id")
            if spec_id in lead_ids:
                errors.append(f"{label}: id '{spec_id}' also used as a lead id")
            spec_ids.add(spec_id)
        lead_ref = spec.get("lead_agent_id")
        if isinstance(lead_ref, str) and lead_ref and lead_ref not in lead_ids:
            errors.append(f"{label}: lead_agent_id '{lead_ref}' not found in lead_agents")
        _collect_skill_refs(spec, label, ("skills_required",))
        for tag in spec.get("domain_tags", []) if isinstance(spec.get("domain_tags"), list) else []:
            if tag not in domain_set:
                errors.append(f"{label}: domain_tag '{tag}' not in supported_domains")

    return {
        "schema_version": agents.get("schema_version"),
        "catalog_version": agents.get("catalog_version"),
        "supported_domains": list(domains),
        "lead_agents": leads,
        "specialist_roles": specialists,
        "skill_refs": skill_refs,
    }


def _validate_skills(
    skills_doc: dict[str, Any],
    domain_set: set[str],
    errors: list[str],
) -> dict[str, Any]:
    for key in ("schema_version", "catalog_version", "families", "skills"):
        if key not in skills_doc:
            errors.append(f"skills.json: missing top-level key '{key}'")

    families = skills_doc.get("families")
    if not isinstance(families, list):
        errors.append("skills.json: 'families' must be a list")
        families = []
    if len(families) != EXPECTED_FAMILY_COUNT:
        errors.append(f"skills.json: expected {EXPECTED_FAMILY_COUNT} families, found {len(families)}")

    skills = skills_doc.get("skills")
    if not isinstance(skills, list):
        errors.append("skills.json: 'skills' must be a list")
        skills = []
    if len(skills) != EXPECTED_SKILL_COUNT:
        errors.append(f"skills.json: expected {EXPECTED_SKILL_COUNT} skills, found {len(skills)}")

    family_names: set[str] = set()
    family_members: dict[str, list[str]] = {}
    for index, family in enumerate(families):
        if not isinstance(family, dict):
            errors.append(f"families[{index}]: must be an object")
            continue
        label = f"family '{family.get('name', index)}'"
        _check_required_fields(family, FAMILY_REQUIRED_FIELDS, label, errors)
        fam_name = family.get("name")
        if isinstance(fam_name, str) and fam_name:
            if fam_name in family_names:
                errors.append(f"{label}: duplicate family name")
            family_names.add(fam_name)
        fam_domain = family.get("domain")
        if isinstance(fam_domain, str) and fam_domain and fam_domain not in domain_set:
            errors.append(f"{label}: domain '{fam_domain}' not in supported_domains")
        members = family.get("skills")
        if isinstance(members, list) and isinstance(fam_name, str):
            member_list = [m for m in members if isinstance(m, str)]
            if len(set(member_list)) != len(member_list):
                errors.append(f"{label}: duplicate skill name in family members")
            family_members[fam_name] = member_list

    skill_names: set[str] = set()
    skills_by_family: dict[str, list[str]] = {}
    for index, skill in enumerate(skills):
        if not isinstance(skill, dict):
            errors.append(f"skills[{index}]: must be an object")
            continue
        label = f"skill '{skill.get('name', index)}'"
        _check_required_fields(skill, SKILL_REQUIRED_FIELDS, label, errors)
        skill_name = skill.get("name")
        if isinstance(skill_name, str) and skill_name:
            if skill_name in skill_names:
                errors.append(f"{label}: duplicate skill name")
            skill_names.add(skill_name)
        fam_ref = skill.get("family")
        if isinstance(fam_ref, str) and fam_ref:
            if fam_ref not in family_names:
                errors.append(f"{label}: family '{fam_ref}' not found in families")
            if isinstance(skill_name, str):
                skills_by_family.setdefault(fam_ref, []).append(skill_name)
        for tag in skill.get("domain_tags", []) if isinstance(skill.get("domain_tags"), list) else []:
            if tag not in domain_set:
                errors.append(f"{label}: domain_tag '{tag}' not in supported_domains")

    # Cross-check family membership against actual skill.family assignments.
    for fam_name, declared in family_members.items():
        actual = sorted(skills_by_family.get(fam_name, []))
        if sorted(declared) != actual:
            errors.append(
                f"family '{fam_name}': membership does not match skill.family assignments"
            )

    return {
        "schema_version": skills_doc.get("schema_version"),
        "catalog_version": skills_doc.get("catalog_version"),
        "families": families,
        "skills": skills,
        "skill_names": skill_names,
    }


def _build_catalog() -> dict[str, Any]:
    """Read and validate both files, returning the internal catalog or raising."""

    errors: list[str] = []
    agents_doc = _read_json(_AGENTS_PATH)
    skills_doc = _read_json(_SKILLS_PATH)

    agents = _validate_agents(agents_doc, errors)
    domain_set = set(agents["supported_domains"])
    skills = _validate_skills(skills_doc, domain_set, errors)

    # Cross-reference agent skill references against known skill names. This runs
    # after both documents parse because skill names only exist once skills load.
    skill_names = skills["skill_names"]
    for label, ref in agents["skill_refs"]:
        if ref not in skill_names:
            errors.append(f"{label}: references unknown skill '{ref}'")

    if errors:
        raise CatalogError("catalog_invalid", errors)

    return {
        "agents_schema_version": agents["schema_version"],
        "agents_catalog_version": agents["catalog_version"],
        "skills_schema_version": skills["schema_version"],
        "skills_catalog_version": skills["catalog_version"],
        "supported_domains": agents["supported_domains"],
        "lead_agents": agents["lead_agents"],
        "specialist_roles": agents["specialist_roles"],
        "families": skills["families"],
        "skills": skills["skills"],
    }


_CACHE: dict[str, Any] | None = None


def _catalog() -> dict[str, Any]:
    """Return the cached, validated internal catalog (loaded once)."""

    global _CACHE
    if _CACHE is None:
        _CACHE = _build_catalog()
    return _CACHE


def load_catalog() -> dict[str, Any]:
    """Return a deep copy of the full validated catalog."""

    return copy.deepcopy(_catalog())


def validate_catalog() -> dict[str, Any]:
    """Validate the catalog and return a structured report (never raises)."""

    try:
        catalog = _catalog()
    except CatalogError as exc:
        return {"ok": False, "code": exc.code, "errors": exc.errors}
    return {
        "ok": True,
        "code": "catalog_valid",
        "totals": {
            "lead_agents": len(catalog["lead_agents"]),
            "specialist_roles": len(catalog["specialist_roles"]),
            "supported_domains": len(catalog["supported_domains"]),
            "families": len(catalog["families"]),
            "skills": len(catalog["skills"]),
        },
        "versions": {
            "agents_schema_version": catalog["agents_schema_version"],
            "agents_catalog_version": catalog["agents_catalog_version"],
            "skills_schema_version": catalog["skills_schema_version"],
            "skills_catalog_version": catalog["skills_catalog_version"],
        },
    }


def get_supported_domains() -> list[str]:
    """Return a copy of the supported domain id list in catalog order."""

    return list(_catalog()["supported_domains"])


def list_agents(
    kind: str | None = None,
    domain: str | None = None,
    lead_id: str | None = None,
) -> list[dict[str, Any]]:
    """List leads and/or specialists with optional filters (deep-copied).

    ``kind`` is ``lead``, ``specialist``, or None for both. ``domain`` filters
    by domain_tags membership. ``lead_id`` filters specialists by their lead.
    Results carry an added ``kind`` discriminator and preserve catalog order.

    Fail-closed: an unknown ``kind`` or unknown ``domain`` filter raises
    ``CatalogError`` instead of silently returning an empty list.
    """

    catalog = _catalog()

    if kind is not None and kind not in ("lead", "specialist"):
        raise CatalogError("invalid_kind", [f"unknown kind '{kind}'"])
    if domain is not None and domain not in catalog["supported_domains"]:
        raise CatalogError("unknown_domain", [f"unknown domain '{domain}'"])

    results: list[dict[str, Any]] = []

    if kind in (None, "lead"):
        for lead in catalog["lead_agents"]:
            if domain is not None and domain not in lead.get("domain_tags", []):
                continue
            if lead_id is not None and lead.get("id") != lead_id:
                continue
            record = copy.deepcopy(lead)
            record["kind"] = "lead"
            results.append(record)

    if kind in (None, "specialist"):
        for spec in catalog["specialist_roles"]:
            if domain is not None and domain not in spec.get("domain_tags", []):
                continue
            if lead_id is not None and spec.get("lead_agent_id") != lead_id:
                continue
            record = copy.deepcopy(spec)
            record["kind"] = "specialist"
            results.append(record)

    return results


def get_agent(agent_id: str) -> dict[str, Any] | None:
    """Return a deep copy of a lead or specialist by id, or None if absent."""

    if not isinstance(agent_id, str) or not agent_id.strip():
        return None
    target = agent_id.strip()
    catalog = _catalog()
    for lead in catalog["lead_agents"]:
        if lead.get("id") == target:
            record = copy.deepcopy(lead)
            record["kind"] = "lead"
            return record
    for spec in catalog["specialist_roles"]:
        if spec.get("id") == target:
            record = copy.deepcopy(spec)
            record["kind"] = "specialist"
            return record
    return None


def list_skills(
    family: str | None = None,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    """List skills with optional family/domain filters (deep-copied).

    Fail-closed: an unknown ``family`` or unknown ``domain`` filter raises
    ``CatalogError`` instead of silently returning an empty list.
    """

    catalog = _catalog()

    if family is not None:
        family_names = {f.get("name") for f in catalog["families"]}
        if family not in family_names:
            raise CatalogError("unknown_family", [f"unknown family '{family}'"])
    if domain is not None and domain not in catalog["supported_domains"]:
        raise CatalogError("unknown_domain", [f"unknown domain '{domain}'"])

    results: list[dict[str, Any]] = []
    for skill in catalog["skills"]:
        if family is not None and skill.get("family") != family:
            continue
        if domain is not None and domain not in skill.get("domain_tags", []):
            continue
        results.append(copy.deepcopy(skill))
    return results


def list_families() -> list[dict[str, Any]]:
    """Return deep copies of all skill families in catalog order."""

    return copy.deepcopy(_catalog()["families"])
