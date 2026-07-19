#!/usr/bin/env python3
"""ด่านเขียนกลางแบบ CURRENT_WORKSPACE_ONLY.

Shortcut และ AI ใช้เฉพาะ Git root/branch ที่แอปเปิดอยู่ ไม่ต้องมี New Chat
session และไม่ต้องผ่าน AI Relay แต่ยังขวางกิ่งร่วม ไฟล์ลับ การเขียนข้าม
พื้นที่ การแก้ตัวด่าน และคำสั่งอันตราย
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
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
    "rg", "grep", "ls", "pwd", "test", "head", "tail", "cat",
    "wc", "stat", "du", "df", "ps", "which", "uniq", "date", "jq",
    "basename", "dirname", "realpath", "file", "env", "printenv",
    "pytest", "ruff", "tsc",
}
PYTHON_READ_ONLY_MODULES = {"pytest", "py_compile", "compileall"}
RUFF_WRITE_FLAGS = {"--fix", "--fix-only", "--add-noqa", "--unsafe-fixes"}
NEUTRAL_BINS = {"export", "cd", "echo", "printf", "true", ":", "set", "unset"}
BLOCKED_BINS = {
    "rm", "rmdir", "shred", "dd", "mkfs", "truncate", "tee", "chmod", "chown", "sudo",
    "su", "kill", "pkill", "killall", "launchctl", "systemctl", "service", "reboot",
    "shutdown", "kubectl", "helm", "terraform", "ansible", "rsync", "xargs", "eval",
}
SHELL_BINS = {"bash", "sh", "zsh", "fish"}
FIND_WRITE_FLAGS = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprintf", "-fls"}
CURL_WRITE_FLAGS = {"-o", "-O", "--output", "--remote-name", "--output-dir", "-J", "--remote-header-name"}
GIT_BLOCKED_SUBCOMMANDS = {
    "apply", "checkout", "switch", "reset", "clean", "stash", "rebase", "cherry-pick",
    "filter-branch", "update-ref", "reflog",
}
GIT_PROTECTED_MUTATIONS = {"add", "commit", "push", "merge", "tag"}
GIT_READ_SUBCOMMANDS = {
    "status", "diff", "log", "show", "rev-parse", "ls-files", "grep", "describe", "remote",
}
WORKTREE_READ_ACTIONS = {"list", "status", "doctor"}
PACKAGE_WRITE_ACTIONS = {
    "add", "install", "i", "remove", "rm", "uninstall", "update", "upgrade", "publish",
    "link", "unlink", "import", "patch", "deploy", "exec", "dlx", "create", "init",
}
SPEC_INTERVIEW_OWNER_ACTIONS = {"record-answer", "approve", "waive"}
SPEC_INTERVIEW_READ_ACTIONS = {"verify", "manifest"}
SPEC_INTERVIEW_TOOL = Path(__file__).resolve().parents[1] / "spec-interview" / "spec_interview.py"
MAX_OWNER_PROMPT_CHARS = 500
BRANCH_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
OWNER_BRANCH_NEGATION = re.compile(
    r"(?:ห้าม|อย่า|ไม่ต้อง|ไม่ให้|ไม่ควร|do\s+not|don't|never)"
    r"\s*(?:ให้\s+\S+\s*)?(?:สร้าง|เปิด|create|make|new)?\s*"
    r"(?:new\s*)?(?:branch|สาขา|กิ่ง)",
    re.IGNORECASE,
)
PASTED_EXAMPLE_MARKERS = {"ตัวอย่าง", "แชทเก่า", "เหตุการณ์เดิม", "example from", "old chat"}


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
        hermes / "owner-intents",
        hermes / "spec-evidence",
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
    while tokens:
        while tokens and ENV_ASSIGN.match(tokens[0]):
            tokens = tokens[1:]
        if not tokens:
            break
        first = Path(tokens[0]).name
        if first == "env":
            tokens = tokens[1:]
            while tokens:
                if ENV_ASSIGN.match(tokens[0]) or tokens[0] in {"-i", "--ignore-environment"}:
                    tokens = tokens[1:]
                    continue
                if tokens[0] in {"-u", "--unset", "-C", "--chdir"} and len(tokens) >= 2:
                    tokens = tokens[2:]
                    continue
                if tokens[0].startswith(("--unset=", "--chdir=")):
                    tokens = tokens[1:]
                    continue
                break
            continue
        if first in {"command", "nice", "time", "nohup"}:
            tokens = tokens[1:]
            continue
        break
    return tokens


def _content_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (_content_text(item) for item in value)))
    if isinstance(value, dict):
        for key in ("text", "content", "message"):
            if key in value:
                text = _content_text(value[key])
                if text:
                    return text
    return ""


def _entry_user_text(entry: object) -> str:
    if not isinstance(entry, dict) or entry.get("isMeta") is True:
        return ""
    message = entry.get("message")
    role = str(entry.get("role") or "").lower()
    entry_type = str(entry.get("type") or "").lower()
    if isinstance(message, dict):
        role = str(message.get("role") or role).lower()
    if role != "user" and entry_type not in {"user", "human", "user_message"}:
        return ""
    return _content_text(message if message is not None else entry.get("content"))


def _transcript_last_user(path_value: object) -> str:
    if not isinstance(path_value, str) or not path_value.strip():
        return ""
    path = Path(path_value).expanduser()
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""
    entries: list[object] = []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        for line in raw.splitlines():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    else:
        entries = parsed if isinstance(parsed, list) else [parsed]
    texts = [_entry_user_text(entry) for entry in entries]
    return next((text for text in reversed(texts) if text.strip()), "")


def latest_owner_prompt(payload: dict) -> str:
    transcript = _transcript_last_user(
        payload.get("transcript_path") or payload.get("transcript")
    )
    if transcript:
        return transcript.strip()
    for key in ("user_prompt", "last_user_message", "user_message", "prompt"):
        text = _content_text(payload.get(key))
        if text.strip():
            return text.strip()
    return ""


def valid_branch_name(name: str) -> bool:
    lowered = name.lower()
    return bool(BRANCH_NAME.fullmatch(name)) and not (
        lowered in PROTECTED_BRANCHES
        or name.startswith("-")
        or name.endswith(("/", ".", ".lock"))
        or ".." in name
        or "@{" in name
        or "//" in name
    )


def owner_requested_branch(payload: dict | None, branch_name: str) -> bool:
    if payload is None or not valid_branch_name(branch_name):
        return False
    prompt = latest_owner_prompt(payload)
    if not prompt:
        return stored_owner_branch_intent(payload, branch_name)
    if (
        len(prompt) > MAX_OWNER_PROMPT_CHARS
        or prompt.count("\n") > 8
        or any(marker in prompt.lower() for marker in PASTED_EXAMPLE_MARKERS)
        or OWNER_BRANCH_NEGATION.search(prompt)
    ):
        return False
    escaped = re.escape(branch_name)
    patterns = (
        rf"(?:สร้าง|เปิด|create|make)\s*(?:new\s*)?(?:branch|สาขา|กิ่ง)"
        rf"\s*(?:ใหม่\s*)?(?:ชื่อ|name)?\s*(?:=|:)?\s*[`'\"]?{escaped}(?![A-Za-z0-9._/-])",
        rf"git\s+(?:switch\s+-c|checkout\s+-b|branch)\s+{escaped}(?![A-Za-z0-9._/-])",
    )
    return any(re.search(pattern, prompt, re.IGNORECASE) for pattern in patterns)


def stored_owner_branch_intent(payload: dict, branch_name: str) -> bool:
    cwd = resolve_loose(Path(str(payload.get("cwd") or Path.cwd())))
    root = git_root(cwd)
    if root is None:
        return False
    key = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
    path = Path.home() / ".hermes" / "owner-intents" / f"{key}.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        expires = datetime.fromisoformat(str(record.get("expires_at") or ""))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) >= expires:
        path.unlink(missing_ok=True)
        return False
    return (
        record.get("schema") == "hermes-owner-branch-intent-v1"
        and record.get("git_root") == str(root)
        and record.get("branch") == branch_name
    )


def branch_creation_target(tokens: list[str]) -> str:
    args = tokens[1:]
    if args == ["branch"]:
        return ""
    if len(args) == 2 and args[0] == "branch":
        return args[1]
    if len(args) == 3 and args[0] == "switch" and args[1] in {"-c", "--create"}:
        return args[2]
    if len(args) == 3 and args[0] == "checkout" and args[1] == "-b":
        return args[2]
    return ""


def worktree_manager_ok(tokens: list[str]) -> bool | None:
    first = Path(tokens[0]).name
    if first in {"hermes-new-chat", "hermes-worktree"}:
        action = next((item for item in tokens[1:] if not item.startswith("-")), "")
        return not action or action in WORKTREE_READ_ACTIONS
    if first != "hermes":
        return None
    args = [item for item in tokens[1:] if not item.startswith("-")]
    if not args or args[0] not in {"worktree", "new-chat"}:
        return None
    action = args[1] if len(args) > 1 else ""
    return not action or action in WORKTREE_READ_ACTIONS


def git_segment_ok(tokens: list[str], branch: str, payload: dict | None = None) -> bool:
    args = tokens[1:]
    if any("!" in item or item.startswith("alias.") for item in args):
        return False
    if any(
        item == "-C"
        or item in {"--git-dir", "--work-tree", "--namespace"}
        or item.startswith(("--git-dir=", "--work-tree=", "--namespace="))
        for item in args
    ):
        return False
    sub = ""
    index = 0
    while index < len(args):
        item = args[index]
        if item == "-c" and index + 1 < len(args):
            index += 2
            continue
        if item.startswith("-"):
            index += 1
            continue
        sub = item
        break
    create_target = branch_creation_target(tokens)
    if create_target:
        return owner_requested_branch(payload, create_target)
    if not sub or sub in GIT_BLOCKED_SUBCOMMANDS:
        return False
    if sub == "push" and any(item in {"--force", "-f", "--force-with-lease"} for item in args):
        return False
    if sub == "worktree":
        return len(args) > 1 and args[1] in {"list"}
    if sub == "branch":
        allowed = {"--show-current", "--list", "-l", "-a", "--all", "-r", "--remotes", "-v", "-vv"}
        return all(item.startswith("-") and item in allowed for item in args[1:])
    if sub not in GIT_READ_SUBCOMMANDS:
        return False
    if branch in PROTECTED_BRANCHES and sub in GIT_PROTECTED_MUTATIONS:
        return False
    return True


def package_segment_ok(tokens: list[str]) -> bool:
    args = [item for item in tokens[1:] if not item.startswith("-")]
    if not args:
        return True
    return args[0].lower() not in PACKAGE_WRITE_ACTIONS


def shell_c_command_index(tokens: list[str], start: int = 1) -> int | None:
    """คืน index ของ command string หลัง -c / short flag cluster เช่น -lc; ไม่สับสนกับ --norc."""

    index = start
    while index < len(tokens):
        item = tokens[index]
        if item == "-c":
            return index + 1 if index + 1 < len(tokens) else None
        if item.startswith("-") and not item.startswith("--") and len(item) > 1 and "c" in item[1:]:
            return index + 1 if index + 1 < len(tokens) else None
        if item in {"--rcfile", "--init-file", "-o", "-O"} and index + 1 < len(tokens):
            index += 2
            continue
        index += 1
    return None


def shell_segment_ok(tokens: list[str], branch: str) -> bool:
    command_index = shell_c_command_index(tokens)
    return command_index is not None and bash_allowed(tokens[command_index], branch)


def shell_read_only_segment_ok(tokens: list[str], branch: str, payload: dict | None = None) -> bool:
    command_index = shell_c_command_index(tokens)
    return command_index is not None and bash_read_only_allowed(tokens[command_index], branch, payload)


def read_only_bin_ok(first: str, tokens: list[str], *, strict: bool = False) -> bool | None:
    if first in {"find", "curl", "sort", "diff"}:
        return False
    if first == "gh":
        return False
    if first == "tsc":
        return "--noEmit" in tokens
    if first == "ruff":
        return len(tokens) >= 2 and tokens[1] == "check" and not any(
            item in RUFF_WRITE_FLAGS for item in tokens[2:]
        )
    if strict and first == "pytest":
        return False
    if first in {"awk", "sed"}:
        return False
    if first in READ_ONLY_BINS:
        return True
    return None


def segment_ok(segment: str, branch: str, payload: dict | None = None) -> bool:
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
    manager_result = worktree_manager_ok(tokens)
    if manager_result is not None:
        return manager_result
    if first in BLOCKED_BINS:
        return False
    if first in SHELL_BINS:
        return shell_segment_ok(tokens, branch)
    if first in NEUTRAL_BINS:
        return True
    if first == "git":
        return git_segment_ok(tokens, branch, payload)
    if first in {"pnpm", "npm", "yarn", "bun"}:
        return package_segment_ok(tokens)
    if first in {"pip", "pip3", "uv"} and any(item in PACKAGE_WRITE_ACTIONS for item in tokens[1:]):
        return False
    if first.startswith("python"):
        if "-m" in tokens:
            index = tokens.index("-m")
            return index + 1 < len(tokens) and tokens[index + 1] in PYTHON_READ_ONLY_MODULES
        return False
    read_only_result = read_only_bin_ok(first, tokens)
    if read_only_result is not None:
        return read_only_result
    action = _spec_interview_action(tokens)
    if action in SPEC_INTERVIEW_READ_ACTIONS:
        return True
    return False


def bash_allowed(command: str, branch: str = "", payload: dict | None = None) -> bool:
    return all(segment_ok(part, branch, payload) for part in SEGMENT_SPLIT.split(command))


def bash_hits_protected(command: str) -> bool:
    return any(protected_target(Path(token)) for token in ABS_PATH_TOKEN.findall(command))


def bash_invokes_owner_intent(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return True
    return any(
        Path(token).name in {"hermes-owner-intent", "hermes_owner_intent.py"}
        for token in tokens
    )


def bash_invokes_spec_owner_record(command: str) -> bool:
    lowered = command.lower()
    if "from-hook" in lowered:
        return True
    if (
        ("spec_interview.py" in lowered or "spec-interview" in lowered)
        and any(action in lowered for action in SPEC_INTERVIEW_OWNER_ACTIONS)
    ):
        return True
    parts = [part for part in SEGMENT_SPLIT.split(command) if part.strip()]
    if len(parts) > 1:
        return any(bash_invokes_spec_owner_record(part) for part in parts)
    try:
        tokens = shlex.split(command)
    except ValueError:
        return True
    for index, token in enumerate(tokens):
        first = Path(token).name
        if first in SHELL_BINS:
            command_index = shell_c_command_index(tokens, index + 1)
            if command_index is not None and bash_invokes_spec_owner_record(tokens[command_index]):
                return True
    for index, token in enumerate(tokens):
        if Path(token).name in {"spec-interview", "spec_interview.py"}:
            tail = tokens[index + 1 :]
            tail_text = " ".join(tail)
            return (
                "--from-hook" in tail
                or any(item in SPEC_INTERVIEW_OWNER_ACTIONS for item in tail)
                or "$" in tail_text
                or "`" in tail_text
            )
    if "--from-hook" in tokens and any(item in SPEC_INTERVIEW_OWNER_ACTIONS for item in tokens):
        return True
    return False


def _spec_interview_action(tokens: list[str]) -> str:
    for index, token in enumerate(tokens):
        if Path(token).name in {"spec-interview", "spec_interview.py"}:
            return next((item for item in tokens[index + 1 :] if not item.startswith("-")), "")
        if resolve_loose(Path(token)) == resolve_loose(SPEC_INTERVIEW_TOOL):
            return next((item for item in tokens[index + 1 :] if not item.startswith("-")), "")
    return ""


def segment_read_only_ok(segment: str, branch: str, payload: dict | None = None) -> bool:
    segment = segment.strip()
    if not segment:
        return True

    def check_substitution(match: re.Match) -> str:
        inner = match.group(1) or match.group(2) or ""
        return "__SUBST_OK__" if bash_read_only_allowed(inner, branch, payload) else "__SUBST_BAD__"

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
    if first in SHELL_BINS:
        return shell_read_only_segment_ok(tokens, branch, payload)
    if first in NEUTRAL_BINS:
        return True
    read_only_result = read_only_bin_ok(first, tokens, strict=True)
    if read_only_result is not None:
        return read_only_result
    if first == "git":
        args = tokens[1:]
        sub = next((item for item in args if not item.startswith("-")), "")
        return sub in {
            "status", "diff", "log", "show", "rev-parse", "branch", "ls-files",
            "grep", "describe", "remote", "config",
        } and git_segment_ok(tokens, branch, payload)
    action = _spec_interview_action(tokens)
    if action in SPEC_INTERVIEW_READ_ACTIONS:
        return True
    return False


def bash_read_only_allowed(command: str, branch: str = "", payload: dict | None = None) -> bool:
    return all(segment_read_only_ok(part, branch, payload) for part in SEGMENT_SPLIT.split(command))


def project_plan_id(root: Path) -> str:
    plan = root / ".project" / "plan.md"
    try:
        text = plan.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""
    match = re.search(r"(?im)^\s*>?\s*plan_id\s*:\s*([A-Za-z0-9_-]+)\b", text)
    return match.group(1) if match else ""


def spec_path_for(root: Path, plan_id: str) -> Path:
    return root / ".project" / "spec" / f"{plan_id}.md"


def spec_lifecycle(root: Path) -> tuple[str, Path | None]:
    if root is None:
        return "", None
    plan_id = project_plan_id(root)
    if not plan_id:
        return "", None
    spec = spec_path_for(root, plan_id)
    return (plan_id, spec) if spec.exists() else ("", None)


def spec_write_allowed_before_approval(target: Path, root: Path) -> bool:
    resolved = resolve_loose(target)
    allowed = [
        root / ".project" / "plan.md",
        root / ".project" / "spec",
        root / ".project" / "scratchpad.md",
        root / ".project" / "scratchpad",
    ]
    for base in allowed:
        base_resolved = resolve_loose(base)
        if resolved == base_resolved or base_resolved in resolved.parents:
            return True
    return False


def spec_approved(root: Path, plan_id: str, spec: Path) -> bool:
    if not SPEC_INTERVIEW_TOOL.exists():
        return False
    proc = subprocess.run(
        [
            sys.executable,
            str(SPEC_INTERVIEW_TOOL),
            "verify",
            "--repo",
            str(root),
            "--plan-id",
            plan_id,
            "--spec",
            str(spec),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return False
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False
    return bool(data.get("ok") and data.get("approved_manifest_match"))


def spec_gate_allows_targets(root: Path | None, targets: list[Path]) -> tuple[bool, str]:
    if root is None:
        return True, ""
    plan_id, spec = spec_lifecycle(root)
    if not plan_id or spec is None:
        return True, ""
    if spec_approved(root, plan_id, spec):
        return True, ""
    blocked = [target for target in targets if not spec_write_allowed_before_approval(target, root)]
    if blocked:
        return False, f"สเปค {plan_id} ยังไม่อนุมัติ; เขียนได้เฉพาะ .project/spec, .project/plan.md หรือ scratchpad"
    return True, ""


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
        if bash_invokes_owner_intent(command):
            return block("ห้าม AI สร้างใบอนุญาตกิ่งแทนข้อความจากเจ้าของ")
        if bash_invokes_spec_owner_record(command):
            return block("ห้าม AI บันทึกคำตอบหรืออนุมัติสเปคแทนเจ้าของ")
        if bash_hits_protected(command) and not bash_read_only_allowed(command, branch, payload):
            return block("คำสั่งพยายามแก้พื้นที่ Hook/Settings/เครื่องมือ Hermes")
        if not bash_allowed(command, branch, payload):
            return block("คำสั่งสร้าง/สลับพื้นที่ ติดตั้งของ ลบไฟล์ เขียนผ่าน shell หรือเป็นคำสั่งอันตราย")
        plan_id, spec = spec_lifecycle(root)
        if plan_id and spec is not None and not spec_approved(root, plan_id, spec):
            if not bash_read_only_allowed(command, branch, payload):
                return block(
                    f"สเปค {plan_id} ยังไม่อนุมัติ; Bash ทำได้เฉพาะคำสั่งอ่านอย่างเดียวหรือ spec-interview verify/manifest"
                )
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
    ok, reason = spec_gate_allows_targets(root, targets)
    if not ok:
        return block(reason)
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError) as exc:
        return block(f"อ่านข้อมูล Hook ไม่ได้: {exc}")
    return run(payload) if isinstance(payload, dict) else block("ข้อมูล Hook ต้องเป็น JSON object")


if __name__ == "__main__":
    raise SystemExit(main())
