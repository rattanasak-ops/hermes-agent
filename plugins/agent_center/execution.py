"""Run Agent Center seats through the host-owned plugin LLM facade.

The module never reads credentials. Hermes resolves authentication and model
routing through ``PluginContext.llm``. A packet ``session_id`` remains a
logical seat-run identity; plugin LLM calls are bounded completions and are not
resumable Hermes child sessions.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from . import policies, routing


MIN_MAX_TOKENS = 128
MAX_MAX_TOKENS = 8192
DEFAULT_MAX_TOKENS = 1200
MIN_TIMEOUT_SECONDS = 5.0
MAX_TIMEOUT_SECONDS = 600.0
DEFAULT_TIMEOUT_SECONDS = 120.0
SUPPORTED_RUNTIME_PROVIDERS = frozenset(
    {
        "anthropic",
        "gemini",
        "nous",
        "openai",
        "openai-codex",
        "openrouter",
        "xai",
        "xai-oauth",
    }
)


def _clean_string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _bounded_number(
    value: Any,
    *,
    default: int | float,
    minimum: int | float,
    maximum: int | float,
    integer: bool,
) -> int | float | None:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if integer and not isinstance(value, int):
        return None
    if value < minimum or value > maximum:
        return None
    return int(value) if integer else float(value)


def _usage_view(result: Any) -> dict[str, Any]:
    usage = getattr(result, "usage", None)
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        "cache_read_tokens": int(getattr(usage, "cache_read_tokens", 0) or 0),
        "cache_write_tokens": int(getattr(usage, "cache_write_tokens", 0) or 0),
        "cost_usd": getattr(usage, "cost_usd", None),
    }


def _system_prompt(seat_name: str, packet: dict[str, Any]) -> str:
    shared = (
        "You are an active seat in a Hermes Agent Center work packet. "
        "Stay inside the stated goal, allowed paths, forbidden actions, and "
        "evidence gates. State assumptions and risks plainly. Do not claim "
        "that files, tests, deployments, or external actions happened unless "
        "their evidence is included in the supplied context."
    )
    duties = {
        "planner_primary": (
            "Act as the primary planner. Produce a concrete answer and explain "
            "the evidence behind the important decisions."
        ),
        "planner_challenger": (
            "Act as an independent challenger. Look for wrong assumptions, "
            "missing domains, unsafe shortcuts, and a better alternative."
        ),
        "worker": (
            "Act as the producing worker. Return the bounded work product or "
            "implementation draft requested by the packet. This completion has "
            "no file or terminal tools, so never claim repository mutations."
        ),
        "reviewer": (
            "Act as a read-only reviewer. Inspect the worker output supplied in "
            "the prompt, identify blocking defects, and give a pass/fail decision."
        ),
    }
    return f"{shared}\n\n{duties[seat_name]}\n\nExecution mode: {packet['execution_mode']}"


def _packet_context(packet: dict[str, Any], request: str) -> str:
    context = {
        "packet_id": packet["packet_id"],
        "project_id": packet["project_id"],
        "goal": packet["goal"],
        "phase": packet["phase"],
        "execution_mode": packet["execution_mode"],
        "domains": packet["domains"],
        "risk_tags": packet["risk_tags"],
        "signals": packet["signals"],
        "project_context_refs": packet["project_context_refs"],
        "allowed_paths": packet["allowed_paths"],
        "forbidden_actions": packet["forbidden_actions"],
        "deliverables": packet["deliverables"],
        "evidence_gates": packet["evidence_gates"],
    }
    return (
        f"Owner request:\n{request}\n\n"
        "Validated work packet context:\n"
        + json.dumps(context, ensure_ascii=False, sort_keys=True)
    )


async def _call_seat(
    *,
    seat_name: str,
    packet: dict[str, Any],
    prompt: str,
    llm: Any,
    provider: str | None,
    max_tokens: int,
    timeout: float,
    execution_id: str,
    request_sha256: str,
) -> dict[str, Any]:
    seat = packet["seats"][seat_name]
    requested_model = _clean_string(seat.get("model_id")) or seat["provider_id"]
    expected_family = policies.provider_family(seat["provider_id"])
    actual_target_family = policies.provider_family(requested_model)
    if actual_target_family != expected_family:
        raise ValueError(
            f"runtime model family '{actual_target_family}' does not match "
            f"packet seat family '{expected_family}'"
        )

    result = await llm.acomplete(
        [
            {"role": "system", "content": _system_prompt(seat_name, packet)},
            {"role": "user", "content": prompt},
        ],
        provider=provider,
        model=requested_model,
        temperature=None,
        max_tokens=max_tokens,
        timeout=timeout,
        purpose=f"agent-center:{seat_name}",
    )
    text = _clean_string(getattr(result, "text", ""))
    if not text:
        raise RuntimeError("model returned an empty response")
    real_provider = _clean_string(getattr(result, "provider", "")) or provider or "auto"
    real_model = _clean_string(getattr(result, "model", "")) or requested_model
    reported_family = policies.provider_family(real_model)
    if reported_family != expected_family:
        raise RuntimeError(
            f"reported model family '{reported_family}' does not match "
            f"packet seat family '{expected_family}'"
        )
    output_sha256 = policies.runtime_output_sha256(
        packet_id=packet["packet_id"],
        request_sha256=request_sha256,
        execution_id=execution_id,
        seat_name=seat_name,
        provider_id=seat["provider_id"],
        session_id=seat["session_id"],
        runtime_provider=real_provider,
        runtime_model=real_model,
        output_text=text,
    )
    return {
        "seat": seat_name,
        "provider": real_provider,
        "model": real_model,
        "logical_session_id": seat["session_id"],
        "resumable": False,
        "text": text,
        "output_ref": f"agent-center://execution/{execution_id}/seat/{seat_name}",
        "output_sha256": output_sha256,
        "usage": _usage_view(result),
    }


async def _synthesize(
    *,
    packet: dict[str, Any],
    request: str,
    planner_outputs: dict[str, dict[str, Any]],
    llm: Any,
    provider: str | None,
    max_tokens: int,
    timeout: float,
) -> dict[str, Any]:
    primary = packet["seats"]["planner_primary"]
    primary_model = _clean_string(primary.get("model_id")) or primary["provider_id"]
    prompt = (
        f"Original request:\n{request}\n\n"
        "Primary analysis:\n"
        f"{planner_outputs['planner_primary']['text']}\n\n"
        "Independent challenge:\n"
        f"{planner_outputs['planner_challenger']['text']}\n\n"
        "Reconcile the disagreement. Keep supported conclusions, correct weak "
        "assumptions, list unresolved risks, and give one recommended decision."
    )
    result = await llm.acomplete(
        [
            {
                "role": "system",
                "content": (
                    "Synthesize two independently produced analyses. Do not hide "
                    "material disagreement and do not invent execution evidence."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        provider=provider,
        model=primary_model,
        temperature=None,
        max_tokens=max_tokens,
        timeout=timeout,
        purpose="agent-center:planner-synthesis",
    )
    text = _clean_string(getattr(result, "text", ""))
    if not text:
        raise RuntimeError("synthesis model returned an empty response")
    return {
        "text": text,
        "provider": _clean_string(getattr(result, "provider", "")) or provider or "auto",
        "model": _clean_string(getattr(result, "model", "")) or primary_model,
        "usage": _usage_view(result),
    }


def _error_text(exc: BaseException) -> str:
    message = str(exc).strip().replace("\n", " ")
    return f"{type(exc).__name__}: {message[:500]}"


async def execute_packet(
    args: dict[str, Any],
    *,
    llm: Any,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Execute every active packet seat and return packet-bound evidence."""

    packet = args.get("packet")
    packet_report = routing.validate_work_packet(packet)
    if not packet_report["ok"]:
        return {
            "ok": False,
            "code": "packet_invalid",
            "blocked": True,
            "packet_report": packet_report,
        }

    if packet["execution_mode"] == "build":
        return {
            "ok": False,
            "code": "BUILD_EXECUTION_UNAVAILABLE",
            "blocked": True,
            "reason": (
                "Plugin LLM completions have no file or terminal tools. "
                "Use a tool-capable worker runtime and a separate read-only reviewer."
            ),
            "receipt": None,
        }

    request = _clean_string(args.get("request"))
    provider_value = args.get("provider")
    provider = _clean_string(provider_value).lower() or None
    max_tokens = _bounded_number(
        args.get("max_tokens"),
        default=DEFAULT_MAX_TOKENS,
        minimum=MIN_MAX_TOKENS,
        maximum=MAX_MAX_TOKENS,
        integer=True,
    )
    timeout = _bounded_number(
        args.get("timeout_seconds"),
        default=DEFAULT_TIMEOUT_SECONDS,
        minimum=MIN_TIMEOUT_SECONDS,
        maximum=MAX_TIMEOUT_SECONDS,
        integer=False,
    )
    errors: list[str] = []
    if not request:
        errors.append("request must be a non-empty string")
    if provider_value is not None and not provider:
        errors.append("provider must be a non-empty string when supplied")
    elif provider and provider.lower() not in SUPPORTED_RUNTIME_PROVIDERS:
        errors.append(
            "provider must be one of " + ", ".join(sorted(SUPPORTED_RUNTIME_PROVIDERS))
        )
    if max_tokens is None:
        errors.append(f"max_tokens must be an integer from {MIN_MAX_TOKENS} to {MAX_MAX_TOKENS}")
    if timeout is None:
        errors.append(
            f"timeout_seconds must be a number from {MIN_TIMEOUT_SECONDS:g} "
            f"to {MAX_TIMEOUT_SECONDS:g}"
        )
    if errors:
        return {
            "ok": False,
            "code": "execution_input_invalid",
            "blocked": True,
            "errors": errors,
        }

    execution_id = "acrun_" + uuid.uuid4().hex[:20]
    request_sha256 = policies.runtime_request_sha256(packet["packet_id"], request)
    base_prompt = _packet_context(packet, request)
    outputs: dict[str, dict[str, Any]] = {}

    planner_names = policies.PLANNER_SEAT_NAMES
    planner_results = await asyncio.gather(
        *(
            _call_seat(
                seat_name=name,
                packet=packet,
                prompt=base_prompt,
                llm=llm,
                provider=provider,
                max_tokens=int(max_tokens),
                timeout=float(timeout),
                execution_id=execution_id,
                request_sha256=request_sha256,
            )
            for name in planner_names
        ),
        return_exceptions=True,
    )
    failed_seats: dict[str, str] = {}
    for name, result in zip(planner_names, planner_results):
        if isinstance(result, BaseException):
            failed_seats[name] = _error_text(result)
        else:
            outputs[name] = result
    if failed_seats:
        return {
            "ok": False,
            "code": "seat_execution_failed",
            "blocked": True,
            "execution_id": execution_id,
            "failed_seats": failed_seats,
            "outputs": outputs,
            "receipt": None,
        }

    planner_families = {
        policies.provider_family(outputs[name]["model"]) for name in planner_names
    }
    if len(planner_families) != len(planner_names):
        return {
            "ok": False,
            "code": "seat_identity_mismatch",
            "blocked": True,
            "execution_id": execution_id,
            "error": "planner runtime outputs did not report two distinct model families",
            "outputs": outputs,
            "receipt": None,
        }

    try:
        synthesis = await _synthesize(
            packet=packet,
            request=request,
            planner_outputs=outputs,
            llm=llm,
            provider=provider,
            max_tokens=int(max_tokens),
            timeout=float(timeout),
        )
    except Exception as exc:  # noqa: BLE001 - fail closed with a bounded report
        return {
            "ok": False,
            "code": "synthesis_failed",
            "blocked": True,
            "execution_id": execution_id,
            "error": _error_text(exc),
            "outputs": outputs,
            "receipt": None,
        }

    mode = packet["execution_mode"]
    active_names = policies.required_seat_names(mode)
    seat_evidence = {
        name: {
            "provider_id": packet["seats"][name]["provider_id"],
            "session_id": packet["seats"][name]["session_id"],
            "output_ref": outputs[name]["output_ref"],
            "output_sha256": outputs[name]["output_sha256"],
            "output_text": outputs[name]["text"],
            "runtime_provider": outputs[name]["provider"],
            "runtime_model": outputs[name]["model"],
            "resumable": False,
        }
        for name in active_names
    }
    skills_used = [
        skill.get("name")
        for skill in packet.get("team", {}).get("skills", [])
        if isinstance(skill, dict) and _clean_string(skill.get("name"))
    ]
    receipt = {
        "evidence_level": policies.RUNTIME_EVIDENCE_LEVEL,
        "execution_id": execution_id,
        "packet_id": packet["packet_id"],
        "request": request,
        "request_sha256": request_sha256,
        "execution_mode": mode,
        "seats": deepcopy_json(packet["seats"]),
        "seat_evidence": seat_evidence,
        "synthesis": synthesis["text"],
        "synthesis_sha256": policies.runtime_synthesis_sha256(
            packet_id=packet["packet_id"],
            request_sha256=request_sha256,
            planner_primary_sha256=outputs["planner_primary"]["output_sha256"],
            planner_challenger_sha256=outputs["planner_challenger"]["output_sha256"],
            synthesis_text=synthesis["text"],
        ),
        "skills_used": skills_used,
        "gate_results": ["all active model seats returned non-empty output"],
        "candidate_links": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": policies.RECEIPT_SCHEMA_VERSION,
    }
    receipt_report = policies.validate_work_receipt(receipt, expected_packet=packet)
    if not receipt_report["ok"]:
        return {
            "ok": False,
            "code": "receipt_invalid",
            "blocked": True,
            "execution_id": execution_id,
            "outputs": outputs,
            "synthesis": synthesis,
            "receipt": receipt,
            "receipt_report": receipt_report,
        }

    return {
        "ok": True,
        "code": "execution_complete",
        "execution_id": execution_id,
        "execution_kind": "thinking_pair",
        "task_id": task_id or "",
        "resumable_sessions": False,
        "repository_gates_complete": False,
        "pending_evidence_gates": list(packet.get("evidence_gates", [])),
        "outputs": outputs,
        "synthesis": synthesis,
        "receipt": receipt,
        "receipt_report": receipt_report,
    }


def deepcopy_json(value: Any) -> Any:
    """Copy JSON-compatible packet data without exposing mutable references."""

    return json.loads(json.dumps(value, ensure_ascii=False))


async def agent_center_execute(
    args: dict[str, Any],
    *,
    llm: Any,
    task_id: str | None = None,
    **_: Any,
) -> str:
    """Tool wrapper returning a JSON string for the Hermes registry."""

    report = await execute_packet(args, llm=llm, task_id=task_id)
    return json.dumps(report, ensure_ascii=False, sort_keys=True)


__all__ = ["agent_center_execute", "execute_packet"]
