"""Agent Center bundled plugin: catalog, routing, policy, and execution tools.

Registers six deterministic catalog/policy tools plus one bounded runtime tool.
The runtime tool uses Hermes-owned model credentials through ``ctx.llm``. It
never reads credentials, writes files, opens a terminal, or persists anything.
"""

from __future__ import annotations

from . import execution, tools


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
            "Validate a Work Packet before execution; validate a Work Receipt "
            "together with its original packet so mode and seat identities are "
            "bound; or validate the bundled catalog when neither is supplied. "
            "A receipt alone is rejected (no persistence).",
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

    ctx.register_tool(
        name="agent_center_execute",
        toolset="agent_center",
        schema={
            "name": "agent_center_execute",
            "description": (
                "Execute a validated think, plan, review, or train Work Packet "
                "through the real cross-family planner pair using Hermes-owned "
                "model credentials, synthesize both outputs, and return a "
                "packet-bound Work Receipt. Build mode fails closed because "
                "plugin model completions have no file or terminal tools."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "packet": {"type": "object"},
                    "request": {"type": "string"},
                    "provider": {
                        "type": "string",
                        "enum": sorted(execution.SUPPORTED_RUNTIME_PROVIDERS),
                    },
                    "max_tokens": {
                        "type": "integer",
                        "minimum": execution.MIN_MAX_TOKENS,
                        "maximum": execution.MAX_MAX_TOKENS,
                    },
                    "timeout_seconds": {
                        "type": "number",
                        "minimum": execution.MIN_TIMEOUT_SECONDS,
                        "maximum": execution.MAX_TIMEOUT_SECONDS,
                    },
                },
                "required": ["packet", "request"],
                "additionalProperties": False,
            },
        },
        handler=lambda args, _ctx=ctx, **kwargs: execution.agent_center_execute(
            args, llm=_ctx.llm, **kwargs
        ),
        is_async=True,
    )
