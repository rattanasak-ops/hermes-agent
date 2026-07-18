#!/usr/bin/env python3
"""ด่านเขียนกลางแบบ CURRENT_WORKSPACE_ONLY.

Shortcut และ AI ใช้เฉพาะ Git root/branch ที่แอปเปิดอยู่ ไม่ต้องมี New Chat
session และไม่ต้องผ่าน AI Relay แต่ยังขวางกิ่งร่วม ไฟล์ลับ การเขียนข้าม
พื้นที่ การแก้ตัวด่าน และคำสั่งอันตราย
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


WRITE_TOOLS = {
    "edit", "write", "multiedit", "notebookedit", "applypatch", "apply_patch",
    "write_file", "patch",
}
PATCH_PATH = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\n|\|")
SUBSTITUTION = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")
ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
FD_DUP = re.compile(r"[0-9]*>&[0-9]+")
REDIRECT_TARGET = re.compile(r"[0-9]*>{1,2}\s*([^\s;|&]+)")
ABS_PATH_TOKEN = re.compile(r"(?:~/|/)[^\s'\";|&<>()]+")
SED_WRITE_CMD = re.compile(r"(?:^|;)\s*[wW]\s")

PROTECTED_BRANCHES = {"main", "master", "develop", "development", "production", "prod"}
SECRET_PARTS = {
    ".hermes", ".grok", ".git", "secret", "secrets", "credential", "credentials",
    "token", "tokens", "private-key", "private-keys", "private_key", "private_keys",
}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks"}
SECRET_FILENAMES = {"id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"}
SAFE_REDIRECT_TARGETS = {"/dev/null", "/dev/stdout", "/dev/stderr"}
READ_ONLY_BINS = {
    "rg", "grep", "find", "ls", "pwd", "test", "head", "tail", "cat", "sed", "awk",
    "wc", "stat", "du", "df", "ps", "which", "diff", "sort", "uniq", "date", "jq",
    "basename", "dirname", "realpath", "file", "gh", "curl", "env", "printenv",
}
NEUTRAL_BINS = {"export", "cd", "echo", "printf", "true", ":", "set", "unset"}
BLOCKED_BINS = {
    "rm", "rmdir", "shred", "dd", "mkfs", "truncate", "tee", "chmod", "chown", "sudo",
    "su", "kill", "pkill", "killall", "launchctl", "systemctl", "service", "reboot",
    "shutdown", "kubectl", "helm", "terraform", "ansible", "rsync",
}
FIND_WRITE_FLAGS = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprintf", "-fls"}
CURL_WRITE_FLAGS = {"-o", "-O", "--output", "--remote-name", "--output-dir", "-J", "--remote-header-name"}
GIT_BLOCKED_SUBCOMMANDS = {
    "apply", "checkout", "switch", "reset", "clean", "stash", "rebase", "cherry-pick",
    "filter-branch", "update-ref", "reflog",
}
GIT_PROTECTED_MUTATIONS = {"add", "commit", "push", "merge", "tag"}
PACKAGE_WRITE_ACTIONS = {
    "add", "install", "i", "remove", "rm", "uninstall", "update", "upgrade", "publish",
    "link", "unlink", "import", "patch", "deploy", "exec", "dlx", "create", "init",
}
HERMES_WORKSPACE_MUTATIONS = {
    "accept", "abandon", "archive", "cleanup", "close", "handoff", "open", "remove",
}


def block(reason: str) -> int:
    print(f"[Hermes Current Workspace Gate] BLOCKED: {reason}", file=sys.stderr)
    return 2


def resolve_loose(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except OSError:
        return path.expanduser().absolute()


def git_root(cwd: Path) -> Path | None:
    if not cwd.is_dir():
        return None
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=cwd, text=True, capture_output=True
    )
    return resolve_loose(Path(proc.stdout.strip())) if proc.returncode == 0 else None


def current_branch(root: Path) -> str:
    proc = subprocess.run(
        ["git", "branch", "--show-current"], cwd=root, text=True, capture_output=True
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def protected_paths() -> list[Path]:
    home = Path.home()
    hermes = Path(os.environ.get("HERMES_HOME", home / ".hermes"))
    return [
        hermes / "new-chat",
        hermes / "new-chat-tools",
        home / ".claude" / "hooks",
        home / ".claude" / "settings.json",
        home / ".claude" / "settings.local.json",
        home / ".codex" / "hooks",
        home / ".codex" / "hooks.json",
        home / ".cursor" / "hooks",
    ]


def protected_target(path: Path) -> bool:
    resolved = resolve_loose(path)
    for base in protected_paths():
        base_resolved = resolve_loose(base)
        if resolved == base_resolved or base_resolved in resolved.parents:
            return True
    local_bin = resolve_loose(Path.home() / ".local" / "bin")
    return resolved.parent == local_bin and (
        resolved.name.startswith("hermes-")
        or resolved.name in {"relay-call", "gate-run", "relay-portal"}
    )


def secret_target(path: Path, root: Path) -> bool:
    resolved = resolve_loose(path)
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        relative = resolved
    lowered = [part.lower() for part in relative.parts]
    name = resolved.name.lower()
    return (
        any(part == ".env" or part.startswith(".env.") for part in lowered)
        or any(part in SECRET_PARTS for part in lowered)
        or name in SECRET_FILENAMES
        or resolved.suffix.lower() in SECRET_SUFFIXES
    )


def inside(path: Path, root: Path) -> bool:
    resolved = resolve_loose(path)
    return resolved == root or root in resolved.parents


def redirects_safe(segment: str) -> bool:
    cleaned = FD_DUP.sub("", segment)
    if ">" not in cleaned:
        return True
    targets = REDIRECT_TARGET.findall(cleaned)
    stripped = REDIRECT_TARGET.sub("", cleaned)
    return ">" not in stripped and bool(targets) and all(t in SAFE_REDIRECT_TARGETS for t in targets)


def _unwrap(tokens: list[str]) -> list[str]:
    while tokens and ENV_ASSIGN.match(tokens[0]):
        tokens = tokens[1:]
    while tokens and Path(tokens[0]).name in {"command", "nice", "time", "nohup"}:
        tokens = tokens[1:]
    return tokens


def git_segment_ok(tokens: list[str], branch: str) -> bool:
    args = tokens[1:]
    sub = next((item for item in args if not item.startswith("-")), "")
    if not sub or sub in GIT_BLOCKED_SUBCOMMANDS:
        return False
    if sub == "push" and any(item in {"--force", "-f", "--force-with-lease"} for item in args):
        return False
    if sub == "worktree":
        return len(args) > 1 and args[1] in {"list"}
    if sub == "branch":
        allowed = {"--show-current", "--list", "-l", "-a", "--all", "-r", "--remotes", "-v", "-vv"}
        return all(item.startswith("-") and item in allowed for item in args[1:])
    if branch in PROTECTED_BRANCHES and sub in GIT_PROTECTED_MUTATIONS:
        return False
    return True


def hermes_workspace_segment_ok(tokens: list[str]) -> bool:
    first = Path(tokens[0]).name
    args = tokens[1:]
    if first == "hermes-new-chat":
        return not args or args[0] != "open"
    if first == "hermes-worktree":
        return not args or args[0] not in HERMES_WORKSPACE_MUTATIONS
    if first == "hermes" and len(args) >= 2 and args[0] == "worktree":
        return args[1] not in HERMES_WORKSPACE_MUTATIONS
    return True


def package_segment_ok(tokens: list[str]) -> bool:
    args = [item for item in tokens[1:] if not item.startswith("-")]
    if not args:
        return True
    return args[0].lower() not in PACKAGE_WRITE_ACTIONS


def segment_ok(segment: str, branch: str) -> bool:
    segment = segment.strip()
    if not segment:
        return True

    def check_substitution(match: re.Match) -> str:
        inner = match.group(1) or match.group(2) or ""
        return "__SUBST_OK__" if bash_allowed(inner, branch) else "__SUBST_BAD__"

    flattened = SUBSTITUTION.sub(check_substitution, segment)
    if "__SUBST_BAD__" in flattened or "$(" in flattened or "`" in flattened:
        return False
    if not redirects_safe(flattened):
        return False
    try:
        tokens = _unwrap(shlex.split(flattened))
    except ValueError:
        return False
    if not tokens:
        return True
    first = Path(tokens[0]).name
    if first in BLOCKED_BINS:
        return False
    if first in NEUTRAL_BINS:
        return True
    if first in {"hermes", "hermes-new-chat", "hermes-worktree"}:
        return hermes_workspace_segment_ok(tokens)
    if first == "git":
        return git_segment_ok(tokens, branch)
    if first in {"pnpm", "npm", "yarn", "bun"}:
        return package_segment_ok(tokens)
    if first in {"pip", "pip3", "uv"} and any(item in PACKAGE_WRITE_ACTIONS for item in tokens[1:]):
        return False
    if first == "find":
        return not any(item in FIND_WRITE_FLAGS for item in tokens)
    if first == "curl":
        return not any(item in CURL_WRITE_FLAGS for item in tokens)
    if first == "sed":
        for item in tokens[1:]:
            if item.startswith("--in-place"):
                return False
            if item.startswith("-") and item != "-" and not item.startswith("--") and "i" in item[1:]:
                return False
            if SED_WRITE_CMD.search(item):
                return False
        return True
    if first in READ_ONLY_BINS:
        return True
    if first.startswith("python") and "-c" in tokens:
        return False
    return True


def bash_allowed(command: str, branch: str = "") -> bool:
    return all(segment_ok(part, branch) for part in SEGMENT_SPLIT.split(command))


def bash_hits_protected(command: str) -> bool:
    return any(protected_target(Path(token)) for token in ABS_PATH_TOKEN.findall(command))


def extract_targets(tool: str, tool_input: dict, cwd: Path) -> list[Path]:
    values: list[str] = []
    value = tool_input.get("file_path") or tool_input.get("path")
    if isinstance(value, str) and value.strip():
        values.append(value)
    if tool in {"applypatch", "apply_patch"}:
        patch_text = str(
            tool_input.get("patch") or tool_input.get("input") or tool_input.get("command") or ""
        )
        values.extend(PATCH_PATH.findall(patch_text))
    targets = []
    for value in values:
        path = Path(value).expanduser()
        targets.append(path if path.is_absolute() else cwd / path)
    return targets


def run(payload: dict) -> int:
    raw_tool = str(payload.get("tool_name") or "")
    tool = re.split(r"[.:/]", raw_tool)[-1].lower()
    if tool in {"exec_command", "run_shell_command", "terminal", "shell"}:
        tool = "bash"
    if tool not in WRITE_TOOLS | {"bash"}:
        return 0
    raw = payload.get("tool_input")
    tool_input = raw if isinstance(raw, dict) else {}
    cwd = resolve_loose(Path(str(payload.get("cwd") or Path.cwd())))
    root = git_root(cwd)
    branch = current_branch(root) if root else ""

    if tool == "bash":
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        if bash_hits_protected(command) and not bash_allowed(command, branch):
            return block("คำสั่งพยายามแก้พื้นที่ Hook/Settings/เครื่องมือ Hermes")
        if not bash_allowed(command, branch):
            return block("คำสั่งสร้าง/สลับพื้นที่ ติดตั้งของ ลบไฟล์ เขียนผ่าน shell หรือเป็นคำสั่งอันตราย")
        return 0

    targets = extract_targets(tool, tool_input, cwd)
    if not targets:
        return block("คำสั่งเขียนไม่มี path ให้ตรวจ")
    workspace = root or cwd
    if root and (not branch or branch in PROTECTED_BRANCHES):
        label = "detached HEAD" if not branch else f"กิ่ง {branch}"
        return block(f"พื้นที่ปัจจุบันอยู่บน {label}; เจ้าของต้องเปิดกิ่งงานก่อนเขียน")
    for target in targets:
        if protected_target(target):
            return block("ห้ามเขียนทับ Hook, Settings, session หรือเครื่องมือ Hermes")
        if not inside(target, workspace):
            return block("ไฟล์เป้าหมายอยู่นอกพื้นที่ปัจจุบัน; ห้ามเขียนข้าม Git root")
        if secret_target(target, workspace):
            return block("ไฟล์เป้าหมายเป็นไฟล์ลับหรือพื้นที่ควบคุมที่ห้ามแก้")
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError) as exc:
        return block(f"อ่านข้อมูล Hook ไม่ได้: {exc}")
    return run(payload) if isinstance(payload, dict) else block("ข้อมูล Hook ต้องเป็น JSON object")


if __name__ == "__main__":
    raise SystemExit(main())
