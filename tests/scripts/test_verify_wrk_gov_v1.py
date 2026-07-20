from pathlib import Path

from scripts.verify_wrk_gov_v1 import mapped_prompt_files, validate_adapter


REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_ROOT = (
    REPO_ROOT / "team-shortcuts/payload/skills/prompt-shortcuts/references"
)


def test_pilot_adapter_has_one_writer_and_runtime_machine() -> None:
    import json

    adapter = json.loads(
        (REFERENCE_ROOT / "hermes-agent.worktree-adapter.example.json").read_text(
            encoding="utf-8"
        )
    )

    assert validate_adapter(adapter) == []
    assert adapter["default_writer_machine_id"] == "notebook-nat"
    assert adapter["runtime_machine_id"] == "vps-linux-nat"


def test_shortcut_map_has_33_families_and_existing_prompt_files() -> None:
    skill_text = (
        REPO_ROOT / "team-shortcuts/payload/skills/prompt-shortcuts/SKILL.md"
    ).read_text(encoding="utf-8")

    rows, prompt_files = mapped_prompt_files(skill_text)

    assert len(rows) == 33
    assert prompt_files
    assert not [name for name in prompt_files if not (REFERENCE_ROOT / name).is_file()]


def test_wrk_gov_core_has_five_parts() -> None:
    expected = {
        "work-execution-policy.md",
        "project-worktree-adapter.schema.json",
        "worktree-registry-v2.schema.json",
        "recovery-cleanup-gate.md",
        "shortcut-worktree-contract.md",
    }

    assert {path.name for path in REFERENCE_ROOT.iterdir()} >= expected
