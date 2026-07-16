# ด่านเครื่องที่ได้รับอนุญาต (host guard) — fable ใช้ได้เฉพาะเครื่องที่มีไฟล์อนุญาต
# ที่มา: เจ้าของสั่ง 2026-07-16 ใส่ fable กลับเฉพาะโน้ตบุ๊กเจ้าของ · พนักงาน/VPS ต้องเรียกไม่ได้
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


relay_call = load_module("relay_call_guard", "relay-call.py")


# ---- ระดับฟังก์ชัน: restricted_tool_block_reason ----

def test_fable_blocked_when_no_marker(tmp_path):
    # เครื่องที่ไม่มีไฟล์อนุญาต (เช่น เครื่องพนักงาน/VPS) ต้องถูกบล็อก
    reason = relay_call.restricted_tool_block_reason("fable", home=tmp_path)
    assert reason is not None
    assert ".fable-allowed" in reason


def test_fable_allowed_when_marker_exists(tmp_path):
    # เครื่องเจ้าของที่วางไฟล์อนุญาตไว้ ต้องผ่านด่าน
    marker_dir = tmp_path / ".hermes"
    marker_dir.mkdir(parents=True)
    (marker_dir / ".fable-allowed").write_text("allowed\n", encoding="utf-8")
    assert relay_call.restricted_tool_block_reason("fable", home=tmp_path) is None


def test_marker_must_be_file_not_dir(tmp_path):
    # กันพลาด: มีโฟลเดอร์ชื่อเดียวกัน ไม่นับเป็นไฟล์อนุญาต
    marker_dir = tmp_path / ".hermes" / ".fable-allowed"
    marker_dir.mkdir(parents=True)
    assert relay_call.restricted_tool_block_reason("fable", home=tmp_path) is not None


def test_normal_tools_never_blocked(tmp_path):
    # เครื่องมือปกติ (opus/grok/codex/gemini/ollama) ไม่โดนด่านนี้ แม้ไม่มีไฟล์อนุญาต
    for tool in ("opus", "grok", "codex", "gemini", "ollama"):
        assert relay_call.restricted_tool_block_reason(tool, home=tmp_path) is None


def test_restricted_list_contains_fable():
    # กันแก้พลาด: fable ต้องอยู่ในบัญชีล็อกต่อเครื่องเสมอ
    assert "fable" in relay_call.RESTRICTED_TOOLS


# ---- ระดับทั้งตัว (ยิงจริงผ่านโปรเซส) — จำลองเครื่องพนักงานด้วย HOME ชั่วคราว ----

def _run_relay(tmp_home, tmp_cwd, tool):
    env = dict(os.environ)
    env["HOME"] = str(tmp_home)  # Path.home() อ่านจาก HOME → จำลองเครื่องอื่นได้จริง
    proc = subprocess.run(
        [sys.executable, str(ROOT / "relay-call.py"),
         "--tool", tool, "--task-id", "GUARD-TEST", "--no-plan",
         "--prompt-file", "ping", "--cwd", str(tmp_cwd)],
        capture_output=True, text=True, env=env, timeout=60,
    )
    return proc


def test_e2e_fable_blocked_on_machine_without_marker(tmp_path):
    # เครื่องที่ไม่มีไฟล์อนุญาต: ต้องได้ not_allowed + exit 10 และไม่แตะ ledger
    home = tmp_path / "home"; home.mkdir()
    cwd = tmp_path / "work"; cwd.mkdir()
    proc = _run_relay(home, cwd, "fable")
    assert proc.returncode == 10, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["status"] == "not_allowed"
    assert payload["ledger_written"] is False


def test_e2e_fable_passes_guard_with_marker(tmp_path):
    # เครื่องที่มีไฟล์อนุญาต: ต้องผ่านด่านนี้ (ไปตายที่ "ไม่มี adapter" แทน ไม่ใช่ not_allowed)
    home = tmp_path / "home"; (home / ".hermes").mkdir(parents=True)
    (home / ".hermes" / ".fable-allowed").write_text("allowed\n", encoding="utf-8")
    cwd = tmp_path / "work"; cwd.mkdir()
    proc = _run_relay(home, cwd, "fable")
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["status"] != "not_allowed", payload
