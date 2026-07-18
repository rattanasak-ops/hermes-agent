#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="${HERMES_NEW_CHAT_DIR:-$HOME/.hermes/new-chat-tools}"
BIN="$HOME/.local/bin"

mkdir -p "$DEST/scripts/new-chat" "$DEST/hermes_cli" "$BIN"
cp "$ROOT/scripts/new-chat/hermes_worktree.py" "$DEST/scripts/new-chat/"
cp "$ROOT/scripts/new-chat/hermes_new_chat.py" "$DEST/scripts/new-chat/"
cp "$ROOT/scripts/new-chat/hermes_prewrite_gate.py" "$DEST/scripts/new-chat/"
cp "$ROOT/hermes_cli/worktree_lifecycle.py" "$DEST/hermes_cli/"
cp "$ROOT/scripts/new-chat/hermes_constants.py" "$DEST/"
touch "$DEST/hermes_cli/__init__.py"
chmod 0755 "$DEST/scripts/new-chat/"*.py

make_wrapper() {
  local name="$1" file="$2"
  cat > "$BIN/$name" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$DEST:\${PYTHONPATH:-}"
exec python3 "$DEST/scripts/new-chat/$file" "\$@"
EOF
  chmod 0755 "$BIN/$name"
}

make_wrapper hermes-worktree hermes_worktree.py
make_wrapper hermes-new-chat hermes_new_chat.py
make_wrapper hermes-prewrite-gate hermes_prewrite_gate.py

printf 'ติดตั้ง New Chat/Worktree Gate 3 คำสั่งที่ %s\n' "$BIN"
