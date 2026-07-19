"""Runtime execution tests for the bundled Agent Center plugin."""

from __future__ import annotations

import asyncio
import importlib.util
import shutil
import sys
import types
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from plugins.agent_center import execution, policies, routing


def _seat(provider_id: str, session_id: str, *roles: str) -> dict:
    return {
        "provider_id": provider_id,
        "session_id": session_id,
        "healthy": True,
        "roles": list(roles),
    }


def _diagnosis(mode: str = "think") -> dict:
    return {
        "project_id": "runtime-pilot",
        "goal": "cross-check the proposed approach",
        "phase": "build" if mode == "build" else "discovery",
        "execution_mode": mode,
        "domains": ["engineering"],
        "risk_tags": ["wrong-assumption"],
        "signals": ["two-model-check"],
        "deliverables": ["cross-checked answer"],
        "evidence_gates": ["planner disagreement resolved"],
    }


def _packet(mode: str = "think") -> dict:
    pool = [
        _seat("anthropic/claude-opus-4.6", "planner-primary-1", "planner"),
        _seat("openai/gpt-5.4", "planner-challenger-1", "analysis"),
    ]
    if mode == "build":
        pool.extend(
            [
                _seat("openai/gpt-5.4", "worker-1", "worker", "code"),
                _seat("anthropic/claude-opus-4.6", "reviewer-1", "review"),
            ]
        )
    report = routing.build_work_packet(
        _diagnosis(mode),
        pool,
        "anthropic/claude-opus-4.6",
        "planner-primary-1",
    )
    assert report["ok"] is True
    return report["packet"]


class FakeLlm:
    def __init__(
        self,
        *,
        fail_model: str | None = None,
        identical: bool = False,
        reported_models: dict[str, str] | None = None,
    ):
        self.calls: list[dict] = []
        self.fail_model = fail_model
        self.identical = identical
        self.reported_models = reported_models or {}

    async def acomplete(self, messages, **kwargs):
        await asyncio.sleep(0)
        self.calls.append({"messages": deepcopy(messages), **kwargs})
        if kwargs.get("model") == self.fail_model:
            raise RuntimeError("provider call failed")
        purpose = kwargs["purpose"]
        text = "same answer" if self.identical else f"answer from {purpose}"
        return SimpleNamespace(
            text=text,
            provider=kwargs.get("provider") or "openrouter",
            model=self.reported_models.get(purpose, kwargs["model"]),
            agent_id="default",
            usage=SimpleNamespace(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                cache_read_tokens=0,
                cache_write_tokens=0,
                cost_usd=None,
            ),
            audit={"purpose": purpose},
        )


def _run(args: dict, llm: FakeLlm) -> dict:
    return asyncio.run(execution.execute_packet(args, llm=llm, task_id="task-1"))


@pytest.mark.parametrize("mode", ["think", "plan", "review", "train"])
def test_non_build_modes_call_two_models_and_primary_synthesis(mode):
    packet = _packet(mode)
    llm = FakeLlm()

    out = _run(
        {
            "packet": packet,
            "request": "Decide whether this design is safe.",
            "provider": "openrouter",
        },
        llm,
    )

    assert out["ok"] is True
    assert out["code"] == "execution_complete"
    assert out["execution_kind"] == "thinking_pair"
    assert len(llm.calls) == 3
    first_models = {call["model"] for call in llm.calls[:2]}
    assert first_models == {
        "anthropic/claude-opus-4.6",
        "openai/gpt-5.4",
    }
    assert llm.calls[2]["purpose"] == "agent-center:planner-synthesis"
    assert set(out["outputs"]) == set(policies.PLANNER_SEAT_NAMES)
    receipt_report = policies.validate_work_receipt(
        out["receipt"], expected_packet=packet
    )
    assert receipt_report["code"] == "receipt_runtime_valid"
    assert receipt_report["evidence_level"] == policies.RUNTIME_EVIDENCE_LEVEL


def test_build_mode_fails_closed_without_a_tool_capable_worker_runtime():
    packet = _packet("build")
    llm = FakeLlm()

    out = _run(
        {
            "packet": packet,
            "request": "Prepare and review a bounded implementation.",
            "provider": "openrouter",
        },
        llm,
    )

    assert out["ok"] is False
    assert out["code"] == "BUILD_EXECUTION_UNAVAILABLE"
    assert out["blocked"] is True
    assert out["receipt"] is None
    assert llm.calls == []


def test_executor_fails_closed_when_one_required_model_fails():
    packet = _packet("think")
    llm = FakeLlm(fail_model="openai/gpt-5.4")

    out = _run(
        {
            "packet": packet,
            "request": "Cross-check this.",
            "provider": "openrouter",
        },
        llm,
    )

    assert out["ok"] is False
    assert out["code"] == "seat_execution_failed"
    assert out["blocked"] is True
    assert out["receipt"] is None
    assert "planner_challenger" in out["failed_seats"]


def test_executor_rejects_runtime_model_identity_mismatch():
    packet = _packet("think")
    llm = FakeLlm(
        reported_models={
            "agent-center:planner_challenger": "anthropic/claude-opus-4.6"
        }
    )

    out = _run(
        {
            "packet": packet,
            "request": "Cross-check this.",
            "provider": "openrouter",
        },
        llm,
    )

    assert out["ok"] is False
    assert out["code"] == "seat_execution_failed"
    assert out["receipt"] is None
    assert "planner_challenger" in out["failed_seats"]


def test_executor_rejects_invalid_packet_before_any_model_call():
    packet = _packet("think")
    packet["goal"] = "tampered"
    llm = FakeLlm()

    out = _run(
        {"packet": packet, "request": "Do not run."},
        llm,
    )

    assert out["ok"] is False
    assert out["code"] == "packet_invalid"
    assert llm.calls == []


def test_output_refs_are_unique_even_when_models_return_identical_text():
    packet = _packet("think")
    llm = FakeLlm(identical=True)

    out = _run(
        {"packet": packet, "request": "Cross-check this."},
        llm,
    )

    refs = [
        evidence["output_ref"]
        for evidence in out["receipt"]["seat_evidence"].values()
    ]
    assert len(refs) == len(set(refs)) == 2


def test_runtime_receipt_detects_request_output_and_synthesis_tampering():
    packet = _packet("think")
    out = _run(
        {"packet": packet, "request": "Cross-check this."},
        FakeLlm(),
    )
    assert out["receipt_report"]["evidence_level"] == policies.RUNTIME_EVIDENCE_LEVEL

    mutations = []
    missing_hash = deepcopy(out["receipt"])
    missing_hash["seat_evidence"]["planner_primary"].pop("output_sha256")
    mutations.append(missing_hash)

    changed_request = deepcopy(out["receipt"])
    changed_request["request"] = "different request"
    mutations.append(changed_request)

    changed_output = deepcopy(out["receipt"])
    changed_output["seat_evidence"]["planner_challenger"]["output_text"] += " tampered"
    mutations.append(changed_output)

    changed_synthesis = deepcopy(out["receipt"])
    changed_synthesis["synthesis"] += " tampered"
    mutations.append(changed_synthesis)

    downgraded = deepcopy(out["receipt"])
    downgraded["evidence_level"] = "structural_only"
    downgraded["request"] = "different request"
    mutations.append(downgraded)

    for receipt in mutations:
        report = policies.validate_work_receipt(receipt, expected_packet=packet)
        assert report["ok"] is False
        assert report["code"] == "receipt_invalid"


def test_executor_requires_non_empty_request_and_bounded_limits():
    packet = _packet("think")
    llm = FakeLlm()

    missing = _run({"packet": packet, "request": "  "}, llm)
    assert missing["code"] == "execution_input_invalid"

    oversized = _run(
        {"packet": packet, "request": "x", "max_tokens": 99999}, llm
    )
    assert oversized["code"] == "execution_input_invalid"

    unknown_provider = _run(
        {"packet": packet, "request": "x", "provider": "unknown"}, llm
    )
    assert unknown_provider["code"] == "execution_input_invalid"
    assert llm.calls == []


def test_installed_plugin_copy_imports_its_own_modules(tmp_path, monkeypatch):
    source = Path(execution.__file__).resolve().parent
    installed = tmp_path / "agent-center"
    shutil.copytree(source, installed)

    namespace = types.ModuleType("hermes_plugins")
    namespace.__path__ = [str(tmp_path)]
    monkeypatch.setitem(sys.modules, "hermes_plugins", namespace)
    module_name = "hermes_plugins.agent_center_installed_test"
    spec = importlib.util.spec_from_file_location(
        module_name,
        installed / "__init__.py",
        submodule_search_locations=[str(installed)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)

    assert Path(module.execution.__file__).resolve().parent == installed.resolve()
    assert Path(module.tools.__file__).resolve().parent == installed.resolve()
