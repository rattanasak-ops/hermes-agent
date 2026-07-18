#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."
SOURCE="$SCRIPT_DIR/new-chat-tools"
DEST="$HOME/.hermes/new-chat-tools"
BIN="$HOME/.local/bin"

require_file() {
  if [ ! -f "$1" ]; then
    printf 'ผิดพลาด: ไม่พบไฟล์ New Chat ที่ %s\n' "$1"
    exit 1
  fi
}

require_file "$SOURCE/hermes_constants.py"
require_file "$SOURCE/scripts/new-chat/hermes_new_chat.py"
require_file "$SOURCE/scripts/new-chat/hermes_worktree.py"
require_file "$REPO_ROOT/hermes_cli/worktree_lifecycle.py"
require_file "$REPO_ROOT/scripts/new-chat/hermes_prewrite_gate.py"
require_file "$REPO_ROOT/scripts/hermes_hook_doctor.py"

mkdir -p "$DEST/scripts/new-chat" "$DEST/scripts" "$DEST/hermes_cli" "$BIN"
cp "$SOURCE/hermes_constants.py" "$DEST/hermes_constants.py"
cp "$SOURCE/scripts/new-chat/hermes_new_chat.py" "$DEST/scripts/new-chat/hermes_new_chat.py"
cp "$SOURCE/scripts/new-chat/hermes_worktree.py" "$DEST/scripts/new-chat/hermes_worktree.py"
cp "$REPO_ROOT/hermes_cli/worktree_lifecycle.py" "$DEST/hermes_cli/worktree_lifecycle.py"
printf '%s\n' '"""Portable Hermes CLI modules."""' > "$DEST/hermes_cli/__init__.py"
cp "$REPO_ROOT/scripts/new-chat/hermes_prewrite_gate.py" "$DEST/scripts/new-chat/hermes_prewrite_gate.py"
cp "$REPO_ROOT/scripts/hermes_hook_doctor.py" "$DEST/scripts/hermes_hook_doctor.py"

install_wrapper() {
  local name="$1"
  local target="$2"
  local wrapper="$BIN/$name"
  printf '%s\n' '#!/usr/bin/env bash' > "$wrapper"
  printf '%s\n' 'set -euo pipefail' >> "$wrapper"
  printf '%s\n' 'export PYTHONPATH="$HOME/.hermes/new-chat-tools${PYTHONPATH:+:$PYTHONPATH}"' >> "$wrapper"
  printf 'exec python3 "$HOME/.hermes/new-chat-tools/%s" "$@"\n' "$target" >> "$wrapper"
  chmod 0755 "$wrapper"
}

install_wrapper "hermes-prewrite-gate" "scripts/new-chat/hermes_prewrite_gate.py"
install_wrapper "hermes-new-chat" "scripts/new-chat/hermes_new_chat.py"
install_wrapper "hermes-worktree" "scripts/new-chat/hermes_worktree.py"
install_wrapper "hermes-hook-doctor" "scripts/hermes_hook_doctor.py"

printf 'ติดตั้งเครื่องมือ New Chat แบบพกพาแล้วที่ %s\n' "$DEST"
