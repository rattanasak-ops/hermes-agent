"""Subscription execution tests for the bundled Agent Center plugin."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import shutil
import subprocess
import sys
import types
from copy import deepcopy
from pathlib import Path

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
    diagnosis = {
        "project_id": "runtime-pilot",
        "goal": "cross-check and complete the proposed approach",
        "phase": "build" if mode == "build" else "discovery",
        "execution_mode": mode,
        "domains": ["engineering"],
        "risk_tags": ["wrong-assumption"],
        "signals": ["two-model-check"],
        "deliverables": ["cross-checked answer"],
        "evidence_gates": ["planner disagreement resolved"],
    }
    if mode == "build":
        diagnosis["allowed_paths"] = ["plugins/agent_center/**"]
        diagnosis["forbidden_actions"] = ["commit", "push", "deploy"]
    return diagnosis


def _packet(mode: str = "think") -> dict:
    pool = [
        _seat("codex-subscription", "planner-primary-1", "planner"),
        _seat("xai-oauth", "planner-challenger-1", "analysis"),
    ]
    if mode == "build":
        pool.extend(
            [
                _seat("codex-worker", "worker-1", "worker", "code"),
                _seat("claude-opus", "reviewer-1", "review"),
            ]
        )
    report = routing.build_work_packet(
        _diagnosis(mode), pool, "codex-subscription", "planner-primary-1"
    )
    assert report["ok"] is True
    return report["packet"]


class FakeRunner:
    def __init__(
        self,
        *,
        fail_seat: str | None = None,
        identical_planners: bool = False,
        reported_family: dict[str, str] | None = None,
        initial_paths: list[str] | None = None,
        changed_paths: list[str] | None = None,
        initial_ignored_paths: list[str] | None = None,
        changed_ignored_paths: list[str] | None = None,
        reviewer_text: str | None = None,
        evidence_error: execution.SubscriptionSeatError | None = None,
    ):
        self.calls: list[dict] = []
        self.fail_seat = fail_seat
        self.identical_planners = identical_planners
        self.reported_family = reported_family or {}
        self.initial_paths = initial_paths or []
        self.changed_paths = changed_paths or ["plugins/agent_center/execution.py"]
        self.initial_ignored_paths = initial_ignored_paths or []
        self.changed_ignored_paths = changed_ignored_paths or []
        self.reviewer_text = reviewer_text
        self.evidence_error = evidence_error
        self.state_calls = 0
        self.ignored_calls = 0

    async def run_seat(self, **kwargs):
        await asyncio.sleep(0)
        self.calls.append(deepcopy(kwargs))
        seat_name = kwargs["seat_name"]
        if seat_name == self.fail_seat:
            raise execution.SubscriptionSeatError("subscription_seat_failed", "quota exhausted")
        family = self.reported_family.get(
            seat_name, execution._seat_family(kwargs["seat"])
        )
        model = {
            "codex": "codex-cli-subscription",
            "grok": "grok-4.3-subscription",
            "opus": "claude-opus-subscription",
        }[family]
        if seat_name == "reviewer":
            text = self.reviewer_text or (
                "No blocking findings.\nREVIEW_DECISION: PASS"
            )
        else:
            text = (
                "same answer"
                if self.identical_planners and seat_name.startswith("planner_")
                else f"answer from {seat_name}"
            )
        return {
            "seat": seat_name,
            "provider": f"{family}-subscription",
            "model": model,
            "runtime_session_ref": f"real-{seat_name}",
            "logical_session_id": kwargs["seat"]["session_id"],
            "resumable": False,
            "text": text,
            "auth_channel": "subscription",
        }

    async def workspace_root(self, cwd):
        return cwd

    async def workspace_state(self, cwd):
        self.state_calls += 1
        return list(self.initial_paths if self.state_calls == 1 else self.changed_paths)

    async def workspace_ignored(self, cwd, *, allowed_paths):
        self.ignored_calls += 1
        return list(
            self.initial_ignored_paths
            if self.ignored_calls == 1
            else self.changed_ignored_paths
        )

    async def workspace_evidence(self, cwd, *, changed_paths, allowed_paths):
        if self.evidence_error:
            raise self.evidence_error
        return "M plugins/agent_center/execution.py\n"


def _run(args: dict, runner: FakeRunner) -> dict:
    return asyncio.run(execution.execute_packet(args, runner=runner, task_id="task-1"))


@pytest.mark.parametrize("mode", ["think", "plan", "review", "train"])
def test_non_build_modes_call_two_subscriptions_and_fresh_primary_synthesis(mode):
    packet = _packet(mode)
    runner = FakeRunner()

    out = _run(
        {"packet": packet, "request": "Decide whether this design is safe."},
        runner,
    )

    assert out["ok"] is True
    assert out["code"] == "execution_complete"
    assert out["execution_kind"] == "subscription_thinking_pair"
    assert [call["seat_name"] for call in runner.calls] == [
        "planner_primary",
        "planner_challenger",
        "planner_synthesis",
    ]
    assert all(call["writable"] is False for call in runner.calls)
    assert set(out["outputs"]) == set(policies.PLANNER_SEAT_NAMES)
    assert all(
        evidence["auth_channel"] == "subscription"
        for evidence in out["receipt"]["seat_evidence"].values()
    )
    assert policies.validate_work_receipt(
        out["receipt"], expected_packet=packet
    )["code"] == "receipt_runtime_valid"


def test_build_runs_worker_then_different_read_only_reviewer():
    packet = _packet("build")
    runner = FakeRunner()

    out = _run(
        {"packet": packet, "request": "Implement the bounded change."}, runner
    )

    assert out["ok"] is True
    assert out["execution_kind"] == "subscription_build_team"
    assert [call["seat_name"] for call in runner.calls] == [
        "planner_primary",
        "planner_challenger",
        "planner_synthesis",
        "worker",
        "reviewer",
    ]
    assert runner.calls[3]["writable"] is True
    assert runner.calls[4]["writable"] is False
    assert execution._seat_family(packet["seats"]["worker"]) != execution._seat_family(
        packet["seats"]["reviewer"]
    )
    assert set(out["receipt"]["seat_evidence"]) == set(policies.BUILD_SEAT_NAMES)
    assert out["receipt_report"]["code"] == "receipt_runtime_valid"
    assert "independent reviewer returned explicit PASS" in out["receipt"]["gate_results"]


def test_build_reviewer_fail_blocks_completion_and_receipt():
    packet = _packet("build")
    runner = FakeRunner(
        reviewer_text="Blocking finding exists.\nREVIEW_DECISION: FAIL"
    )

    out = _run({"packet": packet, "request": "Implement it."}, runner)

    assert out["ok"] is False
    assert out["code"] == "REVIEW_REJECTED"
    assert out["blocked"] is True
    assert out["review_decision"] == "FAIL"
    assert out["receipt"] is None
    assert "reviewer" in out["outputs"]


@pytest.mark.parametrize(
    "reviewer_text",
    [
        "No machine-readable decision.",
        "REVIEW_DECISION: pass",
        "REVIEW_DECISION: PASS\nREVIEW_DECISION: FAIL",
        "```\nREVIEW_DECISION: PASS\n```",
    ],
)
def test_build_reviewer_missing_or_ambiguous_decision_fails_closed(reviewer_text):
    packet = _packet("build")

    out = _run(
        {"packet": packet, "request": "Implement it."},
        FakeRunner(reviewer_text=reviewer_text),
    )

    assert out["ok"] is False
    assert out["code"] == "REVIEW_DECISION_INVALID"
    assert out["review_decision"] == "INVALID"
    assert out["receipt"] is None


def test_incomplete_review_evidence_blocks_before_reviewer_with_specific_code():
    packet = _packet("build")
    runner = FakeRunner(
        evidence_error=execution.SubscriptionSeatError(
            "review_evidence_incomplete", "new file is too large"
        )
    )

    out = _run({"packet": packet, "request": "Implement it."}, runner)

    assert out["ok"] is False
    assert out["code"] == "REVIEW_EVIDENCE_INCOMPLETE"
    assert out["receipt"] is None
    assert "reviewer" not in [call["seat_name"] for call in runner.calls]


def test_build_blocks_dirty_workspace_before_worker():
    packet = _packet("build")
    runner = FakeRunner(initial_paths=["unrelated.txt"])

    out = _run({"packet": packet, "request": "Build it."}, runner)

    assert out["ok"] is False
    assert out["code"] == "CURRENT_WORKSPACE_DIRTY"
    assert "worker" not in [call["seat_name"] for call in runner.calls]


def test_build_blocks_preexisting_ignored_path_before_worker():
    packet = _packet("build")
    runner = FakeRunner(
        initial_ignored_paths=["plugins/agent_center/private-note.txt"]
    )

    out = _run({"packet": packet, "request": "Build it."}, runner)

    assert out["ok"] is False
    assert out["code"] == "BUILD_SCOPE_IGNORED_PATHS_PRESENT"
    assert out["ignored_paths"] == ["plugins/agent_center/private-note.txt"]
    assert out["receipt"] is None
    assert "worker" not in [call["seat_name"] for call in runner.calls]


def test_build_blocks_new_ignored_path_before_reviewer():
    packet = _packet("build")
    runner = FakeRunner(
        changed_ignored_paths=["plugins/agent_center/private-note.txt"]
    )

    out = _run({"packet": packet, "request": "Build it."}, runner)

    assert out["ok"] is False
    assert out["code"] == "BUILD_IGNORED_PATH_CREATED"
    assert out["ignored_paths"] == ["plugins/agent_center/private-note.txt"]
    assert out["receipt"] is None
    assert "worker" in [call["seat_name"] for call in runner.calls]
    assert "reviewer" not in [call["seat_name"] for call in runner.calls]


def test_build_blocks_changed_path_outside_packet_scope():
    packet = _packet("build")
    runner = FakeRunner(changed_paths=["outside.txt"])

    out = _run({"packet": packet, "request": "Build it."}, runner)

    assert out["ok"] is False
    assert out["code"] == "BUILD_SCOPE_VIOLATION"
    assert out["outside_paths"] == ["outside.txt"]
    assert "reviewer" not in [call["seat_name"] for call in runner.calls]


def test_executor_fails_closed_when_one_subscription_fails():
    packet = _packet("think")
    runner = FakeRunner(fail_seat="planner_challenger")

    out = _run({"packet": packet, "request": "Cross-check this."}, runner)

    assert out["ok"] is False
    assert out["code"] == "SUBSCRIPTION_SEAT_EXECUTION_FAILED"
    assert out["receipt"] is None
    assert "planner_challenger" in out["failed_seats"]


def test_executor_rejects_runtime_family_identity_mismatch():
    packet = _packet("think")
    runner = FakeRunner(reported_family={"planner_challenger": "codex"})

    out = _run({"packet": packet, "request": "Cross-check this."}, runner)

    assert out["ok"] is False
    assert out["code"] == "seat_identity_mismatch"
    assert out["receipt"] is None


def test_executor_rejects_invalid_packet_before_any_subscription_call():
    packet = _packet("think")
    packet["goal"] = "tampered"
    runner = FakeRunner()

    out = _run({"packet": packet, "request": "Do not run."}, runner)

    assert out["code"] == "packet_invalid"
    assert runner.calls == []


def test_output_refs_are_unique_even_when_planners_return_identical_text():
    packet = _packet("think")
    out = _run(
        {"packet": packet, "request": "Cross-check this."},
        FakeRunner(identical_planners=True),
    )
    refs = [
        evidence["output_ref"]
        for evidence in out["receipt"]["seat_evidence"].values()
    ]
    assert len(refs) == len(set(refs)) == 2


def test_runtime_receipt_detects_request_output_and_synthesis_tampering():
    packet = _packet("think")
    out = _run(
        {"packet": packet, "request": "Cross-check this."}, FakeRunner()
    )
    mutations = []
    changed_request = deepcopy(out["receipt"])
    changed_request["request"] = "different request"
    mutations.append(changed_request)
    changed_output = deepcopy(out["receipt"])
    changed_output["seat_evidence"]["planner_challenger"]["output_text"] += " tampered"
    mutations.append(changed_output)
    changed_synthesis = deepcopy(out["receipt"])
    changed_synthesis["synthesis"] += " tampered"
    mutations.append(changed_synthesis)
    for receipt in mutations:
        report = policies.validate_work_receipt(receipt, expected_packet=packet)
        assert report["ok"] is False
        assert report["code"] == "receipt_invalid"


def test_executor_requires_non_empty_request_and_bounded_timeout():
    packet = _packet("think")
    runner = FakeRunner()
    assert _run({"packet": packet, "request": "  "}, runner)["code"] == "execution_input_invalid"
    assert _run(
        {"packet": packet, "request": "x", "timeout_seconds": 99999}, runner
    )["code"] == "execution_input_invalid"
    assert runner.calls == []


def test_subscription_commands_use_logins_and_never_api_overrides(tmp_path):
    binaries = {name: f"/bin/{name}" for name in ("codex", "claude", "hermes")}
    runner = execution.SubscriptionSeatRunner(which=binaries.get)
    codex = runner._command(
        family="codex", prompt="p", cwd=str(tmp_path), writable=True
    )
    claude = runner._command(
        family="opus", prompt="p", cwd=str(tmp_path), writable=False
    )
    grok = runner._command(
        family="grok", prompt="p", cwd=str(tmp_path), writable=False
    )
    joined = " ".join(codex + claude + grok).lower()
    assert "workspace-write" in codex
    assert "plan" in claude
    assert "https://api.anthropic.com" in joined
    assert "xai-oauth" in grok
    assert "grok-4.3" in grok
    assert "openrouter" not in joined
    assert "ai-relay" not in joined


def test_subscription_environment_removes_api_and_relay_overrides(monkeypatch):
    for key in (
        "OPENROUTER_API_KEY",
        "AI_RELAY_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
    ):
        monkeypatch.setenv(key, "secret")
    assert "OPENROUTER_API_KEY" not in execution.SubscriptionSeatRunner._clean_env("codex")
    assert "AI_RELAY_API_KEY" not in execution.SubscriptionSeatRunner._clean_env("opus")
    assert "OPENAI_API_KEY" not in execution.SubscriptionSeatRunner._clean_env("codex")
    assert "ANTHROPIC_API_KEY" not in execution.SubscriptionSeatRunner._clean_env("opus")
    assert "XAI_API_KEY" not in execution.SubscriptionSeatRunner._clean_env("grok")


def test_path_scope_rejects_traversal_absolute_and_invalid_patterns():
    assert execution._path_allowed(
        "plugins/agent_center/execution.py", ["plugins/agent_center/**"]
    )
    assert not execution._path_allowed("../secret.txt", ["**"])
    assert not execution._path_allowed("/tmp/secret.txt", ["**"])
    assert not execution._path_allowed("secret.txt", ["../**"])

    with pytest.raises(execution.SubscriptionSeatError) as traversal:
        execution._git_scope_pathspecs(["../**"])
    assert traversal.value.code == "workspace_scope_invalid"
    with pytest.raises(execution.SubscriptionSeatError):
        execution._git_scope_pathspecs(["/tmp/**"])


def test_workspace_ignored_finds_only_ignored_files_in_allowed_scope(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("hidden/**\noutside/**\n", encoding="utf-8")
    hidden = tmp_path / "hidden"
    hidden.mkdir()
    (hidden / "proof.txt").write_text("ignored", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "other.txt").write_text("ignored", encoding="utf-8")
    runner = execution.SubscriptionSeatRunner()

    paths = asyncio.run(
        runner.workspace_ignored(str(tmp_path), allowed_paths=["hidden/**"])
    )

    assert paths == ["hidden/proof.txt"]
    assert asyncio.run(
        runner.workspace_ignored(str(tmp_path), allowed_paths=["safe/**"])
    ) == []


def test_untracked_text_content_is_included_bounded_and_redacted(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    new_dir = tmp_path / "new"
    new_dir.mkdir()
    new_file = new_dir / "proof.txt"
    credential_name = "api_" + "key"
    credential_value = "fixture-" + "credential-value"
    new_file.write_text(
        f"visible evidence\n{credential_name}={credential_value}\n",
        encoding="utf-8",
    )
    runner = execution.SubscriptionSeatRunner()

    paths = asyncio.run(runner.workspace_state(str(tmp_path)))
    evidence = asyncio.run(
        runner.workspace_evidence(
            str(tmp_path),
            changed_paths=paths,
            allowed_paths=["new/**"],
        )
    )

    assert paths == ["new/proof.txt"]
    assert "untracked:new/proof.txt" in evidence
    assert "visible evidence" in evidence
    assert credential_value not in evidence
    assert "<redacted>" in evidence
    assert "sha256=" in evidence


def test_untracked_binary_content_is_omitted_with_hash(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    binary = tmp_path / "asset.bin"
    binary.write_bytes(b"header\x00secret-binary")
    runner = execution.SubscriptionSeatRunner()

    paths = asyncio.run(runner.workspace_state(str(tmp_path)))
    evidence = asyncio.run(
        runner.workspace_evidence(
            str(tmp_path),
            changed_paths=paths,
            allowed_paths=["asset.bin"],
        )
    )

    assert "[binary content omitted]" in evidence
    assert "secret-binary" not in evidence
    assert "sha256=" in evidence


def test_oversized_untracked_file_blocks_instead_of_sending_partial_content(tmp_path):
    oversized = tmp_path / "large.txt"
    oversized.write_bytes(b"x" * (execution._MAX_UNTRACKED_FILE_BYTES + 1))

    with pytest.raises(execution.SubscriptionSeatError) as error:
        execution._read_untracked_evidence(str(tmp_path), ["large.txt"])

    assert error.value.code == "review_evidence_incomplete"


def test_untracked_symlink_and_sensitive_path_fail_closed(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    target = tmp_path / "target.txt"
    target.write_text("safe", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    with pytest.raises(execution.SubscriptionSeatError) as link_error:
        execution._read_untracked_evidence(str(tmp_path), ["link.txt"])
    assert link_error.value.code == "review_evidence_unsafe_file"

    sensitive_file = tmp_path / ".env"
    sensitive_file.write_text("SAMPLE=not-read", encoding="utf-8")
    with pytest.raises(execution.SubscriptionSeatError) as secret_error:
        execution._read_untracked_evidence(str(tmp_path), [".env"])
    assert secret_error.value.code == "review_evidence_sensitive_path"


def test_real_subprocess_captures_nonzero_stderr(tmp_path):
    runner = execution.SubscriptionSeatRunner()
    code, stdout, stderr = asyncio.run(
        runner._run_process(
            [sys.executable, "-c", "import sys; print('bad', file=sys.stderr); sys.exit(7)"],
            cwd=str(tmp_path),
            env={},
            timeout=10,
        )
    )
    assert code == 7
    assert stdout == ""
    assert stderr.strip() == "bad"


def test_subscription_output_parsers():
    codex_text, codex_session = execution.SubscriptionSeatRunner._parse_codex(
        '\n'.join(
            [
                json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "answer"},
                    }
                ),
            ]
        )
    )
    assert (codex_text, codex_session) == ("answer", "thread-1")
    claude_text, claude_session, error = execution.SubscriptionSeatRunner._parse_claude(
        json.dumps({"result": "review", "session_id": "claude-1", "is_error": False})
    )
    assert (claude_text, claude_session, error) == ("review", "claude-1", "")


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
