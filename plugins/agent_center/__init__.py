"""Agent Center bundled plugin: catalog, routing, and policy tools.

Registers six read-only tools over the bundled agent/skill catalog. Every tool
is deterministic, standard-library only, and never writes files, touches the
network, or persists anything. Tool bodies live in ``tools.py``; the catalog,
routing, and policy logic live in ``catalog.py``, ``routing.py``, and
``policies.py`` respectively.
"""

from __future__ import annotations

from plugins.agent_center import tools


def register(ctx) -> None:
    entries = [
        (
            "agent_center_list_agents",
            "List lead and specialist agents from the bundled catalog, optionally "
            "filtered by kind ('lead' or 'specialist'), domain, or lead_id.",
            tools.agent_center_list_agents,
            {
                "kind": {"type": "string"},
                "domain": {"type": "string"},
                "lead_id": {"type": "string"},
            },
            [],
        ),
        (
            "agent_center_get_agent",
            "Fetch a single lead or specialist agent from the catalog by id.",
            tools.agent_center_get_agent,
            {"agent_id": {"type": "string"}},
            ["agent_id"],
        ),
        (
            "agent_center_list_skills",
            "List skills from the bundled catalog, optionally filtered by family "
            "and/or domain.",
            tools.agent_center_list_skills,
            {
                "family": {"type": "string"},
                "domain": {"type": "string"},
            },
            [],
        ),
        (
            "agent_center_route",
            "Validate a structured diagnosis and build a deterministic Team "
            "Manifest, then assemble the Work Packet with assigned AI seats. "
            "diagnosis, seats, current_provider_id, and current_session_id are "
            "all required; a top-level 'blocked' is returned when the seats "
            "cannot be assigned.",
            tools.agent_center_route,
            {
                "diagnosis": {"type": "object"},
                "seats": {"type": "array"},
                "current_provider_id": {"type": "string"},
                "current_session_id": {"type": "string"},
            },
            ["diagnosis", "seats", "current_provider_id", "current_session_id"],
        ),
        (
            "agent_center_prepare_training_candidate",
            "Validate and normalize a training candidate for owner review, "
            "returning a deterministic id, suggested review path, and Markdown "
            "without writing any files.",
            tools.agent_center_prepare_training_candidate,
            {"candidate": {"type": "object"}},
            ["candidate"],
        ),
        (
            "agent_center_validate",
            "Validate a Work Packet or a Work Receipt (supply exactly one; "
            "supplying both is rejected), or validate the bundled catalog and "
            "report totals and versions when neither is supplied (no persistence).",
            tools.agent_center_validate,
            {
                "packet": {"type": "object"},
                "receipt": {"type": "object"},
            },
            [],
        ),
    ]
    for name, description, handler, properties, required in entries:
        parameters: dict[str, object] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            parameters["required"] = required
        ctx.register_tool(
            name=name,
            toolset="agent_center",
            schema={
                "name": name,
                "description": description,
                "parameters": parameters,
            },
            handler=lambda args, _handler=handler, **_: _handler(args),
        )
