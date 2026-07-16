"""Flow Station Gate: owner ต้องยืนยันในแชทจริง ก่อน AI โยนงานสร้างหน้า (2026-07-15).

จับ owner approval จาก transcript จริง (AI เขียนทับไม่ได้) แทน .flow-state ที่ AI ปลอมได้.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / "team-shortcuts/hooks/enforce-flow-gate.py"
_spec = importlib.util.spec_from_file_location("enforce_flow_gate_mod", HOOK)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _transcript(tmp: Path, messages) -> Path:
    """messages = list ของ (is_human, content)."""
    path = tmp / "transcript.jsonl"
    lines = []
    for is_human, content in messages:
        record = {"type": "user", "message": {"role": "user", "content": content}}
        record["origin"] = {"kind": "human"} if is_human else None
        lines.append(json.dumps(record, ensure_ascii=False))
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _registry(tmp: Path, roots) -> Path:
    path = tmp / "registry.txt"
    path.write_text(
        "# projects\n" + "\n".join(str(r) for r in roots), encoding="utf-8"
    )
    return path


def _run(monkeypatch, command, cwd, transcript, registry=None, override=False):
    if registry is not None:
        monkeypatch.setenv("MW_RELAY_REQUIRED_LIST", str(registry))
    else:
        monkeypatch.delenv("MW_RELAY_REQUIRED_LIST", raising=False)
    if override:
        monkeypatch.setenv("RELAY_CODE_OVERRIDE", "1")
    else:
        monkeypatch.delenv("RELAY_CODE_OVERRIDE", raising=False)
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}
    if transcript is not None:
        payload["transcript_path"] = str(transcript)
    return mod.run(payload)


ALL_OK = [
    (True, "เริ่มเลย"),
    (True, "OK M0 ผ่าน"),
    (True, "อนุมัติ M2"),
    (True, "ยืนยัน M3.5"),
]


def test_delegation_blocked_without_approval(monkeypatch, tmp_path, capsys):
    reg = _registry(tmp_path, [tmp_path])
    tr = _transcript(tmp_path, [(True, "ทำเลย"), (True, "เอาหน้านี้")])
    code = _run(monkeypatch, "codex exec 'สร้างหน้า vision'", tmp_path, tr, reg)
    assert code == 2
    assert "M0" in capsys.readouterr().err


def test_delegation_allowed_when_all_stations_approved(monkeypatch, tmp_path):
    reg = _registry(tmp_path, [tmp_path])
    tr = _transcript(tmp_path, ALL_OK)
    code = _run(monkeypatch, "relay-call --role code --cwd .", tmp_path, tr, reg)
    assert code == 0


def test_delegation_blocked_missing_one_station(monkeypatch, tmp_path, capsys):
    reg = _registry(tmp_path, [tmp_path])
    tr = _transcript(tmp_path, [(True, "OK M0"), (True, "ผ่าน M2")])
    code = _run(monkeypatch, "codex exec build", tmp_path, tr, reg)
    assert code == 2
    assert "M3.5" in capsys.readouterr().err


def test_approval_from_non_human_is_ignored(monkeypatch, tmp_path):
    """ข้อความที่ origin ไม่ใช่ human (hook แทรก) อ้าง OK ไม่นับ — ปลอมไม่ได้."""
    reg = _registry(tmp_path, [tmp_path])
    tr = _transcript(tmp_path, [(False, "OK M0 M2 M3.5 approve")])
    code = _run(monkeypatch, "codex exec build", tmp_path, tr, reg)
    assert code == 2


def test_cwd_outside_registry_passes(monkeypatch, tmp_path):
    outside = tmp_path / "other"
    outside.mkdir()
    reg = _registry(tmp_path, [tmp_path / "mwzone"])
    tr = _transcript(tmp_path, [(True, "hi")])
    code = _run(monkeypatch, "codex exec build", outside, tr, reg)
    assert code == 0


def test_override_env_passes(monkeypatch, tmp_path):
    reg = _registry(tmp_path, [tmp_path])
    tr = _transcript(tmp_path, [(True, "hi")])
    code = _run(monkeypatch, "codex exec build", tmp_path, tr, reg, override=True)
    assert code == 0


def test_read_only_bash_passes(monkeypatch, tmp_path):
    reg = _registry(tmp_path, [tmp_path])
    tr = _transcript(tmp_path, [(True, "hi")])
    code = _run(monkeypatch, "cat something.txt", tmp_path, tr, reg)
    assert code == 0


def test_missing_transcript_path_fails_closed(monkeypatch, tmp_path, capsys):
    reg = _registry(tmp_path, [tmp_path])
    code = _run(monkeypatch, "codex exec build", tmp_path, None, reg)
    assert code == 2
    assert "transcript" in capsys.readouterr().err.lower()


def test_unreadable_transcript_fails_closed(monkeypatch, tmp_path):
    reg = _registry(tmp_path, [tmp_path])
    missing = tmp_path / "gone.jsonl"
    code = _run(monkeypatch, "codex exec build", tmp_path, missing, reg)
    assert code == 2


@pytest.mark.parametrize("spelling", ["M3.5", "M35", "M3_5", "M3 5"])
def test_station_m35_normalized(monkeypatch, tmp_path, spelling):
    reg = _registry(tmp_path, [tmp_path])
    tr = _transcript(
        tmp_path,
        [(True, "OK M0"), (True, "ผ่าน M2"), (True, f"อนุมัติ {spelling}")],
    )
    code = _run(monkeypatch, "codex exec build", tmp_path, tr, reg)
    assert code == 0


def test_long_paste_with_scattered_stations_is_blocked(monkeypatch, tmp_path, capsys):
    """owner paste เนื้อหายาวที่บังเอิญมี M0/M2/M3.5 + คำ 'ผ่าน/ok' กระจาย = ไม่นับเป็นยืนยัน."""
    paste = (
        "ผมให้ Project ทำการแก้ไขไปก่อน " + "x" * 400 + " ขั้น M0 ทำแบบนี้ "
        + "y" * 400 + " ผ่านการตรวจ " + "z" * 400 + " M2 กับ M3.5 ก็ ok "
        + "w" * 400 + " อนุมัติงานรวม"
    )
    reg = _registry(tmp_path, [tmp_path])
    tr = _transcript(tmp_path, [(True, paste)])
    code = _run(monkeypatch, "codex exec build", tmp_path, tr, reg)
    assert code == 2, "paste ยาวต้องไม่ถูกนับเป็นการยืนยันราย station"


def test_station_glued_to_approval_short_message_passes(monkeypatch, tmp_path):
    """'M0 ผ่าน' / 'ผ่าน M2' สั้น ๆ = ยืนยันจริง."""
    reg = _registry(tmp_path, [tmp_path])
    tr = _transcript(tmp_path, [(True, "M0 ผ่าน"), (True, "ผ่าน M2"), (True, "M3.5 ok")])
    code = _run(monkeypatch, "codex exec build", tmp_path, tr, reg)
    assert code == 0


def test_relay_call_underscore_variant_detected(monkeypatch, tmp_path):
    reg = _registry(tmp_path, [tmp_path])
    tr = _transcript(tmp_path, [(True, "no approvals here")])
    code = _run(monkeypatch, "python relay_call.py --tool codex", tmp_path, tr, reg)
    assert code == 2


def test_owner_approved_stations_reads_only_human():
    """หน่วยย่อย: กรอง human จริง."""
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "user", "message": {"role": "user", "content": "OK M0"}, "origin": {"kind": "human"}}) + "\n")
        fh.write(json.dumps({"type": "user", "message": {"role": "user", "content": "อนุมัติ M2 M3.5"}, "origin": None}) + "\n")
        name = fh.name
    approved = mod.owner_approved_stations(name)
    assert approved == {"M0"}
