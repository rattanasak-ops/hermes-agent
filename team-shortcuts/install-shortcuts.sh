#!/usr/bin/env bash
#
# install-shortcuts.sh — ตัวติดตั้ง Prompt Shortcut สำหรับพนักงาน (ทำครั้งเดียวต่อเครื่อง)
#
# ทำอะไร (ภาษาคน):
#   1. คัดชุด Shortcut ทั้งหมดจาก payload ไปไว้ในโฟลเดอร์บ้านของผู้ใช้คนนี้
#   2. ต่อให้ Claude Code มองเห็น Shortcut ทุกโปรเจกต์ (ผ่าน ~/.claude/CLAUDE.md)
#   3. ต่อให้ Codex มองเห็น Shortcut (ผ่านทางลัด ~/.codex/skills/prompt-shortcuts)
#   4. ต่อให้ Cursor มองเห็น Shortcut (ผ่านทางลัดชดเชยที่อยู่เดิมของเจ้าของระบบ)
#
# วิธีใช้:
#   bash install-shortcuts.sh          # ติดตั้ง Claude Code + Codex (ไม่ต้องใช้สิทธิ์ผู้ดูแล)
#   bash install-shortcuts.sh --cursor # ติดตั้งเพิ่มทางลัดให้ Cursor ด้วย (อาจขอรหัสผู้ดูแล 1 ครั้ง)
#   bash install-shortcuts.sh --force  # ยอมเขียนทับไฟล์ปลายทางที่ใหม่กว่าชุดติดตั้ง
#
# หมายเหตุสำหรับพนักงาน:
#   พนักงานไม่ต้องมี repo Hermes Agent ในเครื่อง ให้ใช้ install-from-github.sh แทน
#
set -euo pipefail

# --- ที่อยู่มาตรฐานบนเครื่องพนักงาน (อิงโฟลเดอร์บ้าน ใช้ได้ทุกชื่อบัญชี) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD="$SCRIPT_DIR/payload"
VERSION_FILE="$SCRIPT_DIR/VERSION"
DEST_ROOT="${HERMES_SHORTCUTS_DEST:-$HOME/ObsidianVault/HermesAgent}"
REGISTRY="$DEST_ROOT/ai-context/prompt-shortcut-registry.md"
SKILL_SRC="$DEST_ROOT/skills/prompt-shortcuts"
AGENT_SKILL_PAYLOAD="$PAYLOAD/skills/agent-center"
AGENT_SKILL_SRC="$DEST_ROOT/skills/agent-center"
AGENT_PLUGIN_SRC="$SCRIPT_DIR/../plugins/agent_center"
WRITE_PERMIT_SRC="$SCRIPT_DIR/../scripts/hermes_write_permit.py"
WRITE_PERMIT_BIN="$HOME/.local/bin/hermes-write-permit"
HOOK_DOCTOR_SRC="$SCRIPT_DIR/../scripts/hermes_hook_doctor.py"
HOOK_DOCTOR_BIN="$HOME/.local/bin/hermes-hook-doctor"
INSTALLED_VERSION="$DEST_ROOT/.shortcut-version"
TEAM_HOOK_INSTALLER="$SCRIPT_DIR/install-team-hooks.py"
NEW_CHAT_INSTALLER="$SCRIPT_DIR/install-new-chat-tools.sh"

resolve_hermes_runtime_home() {
  if [ -n "${HERMES_HOME:-}" ]; then
    printf '%s\n' "$HERMES_HOME"
    return 0
  fi

  if command -v hermes >/dev/null 2>&1; then
    local reported
    reported="$(hermes dump 2>/dev/null | sed -n 's/^hermes_home:[[:space:]]*//p' | head -n 1)"
    case "$reported" in
      "~")
        printf '%s\n' "$HOME"
        return 0
        ;;
      "~/"*)
        printf '%s/%s\n' "$HOME" "${reported#\~/}"
        return 0
        ;;
      /*)
        printf '%s\n' "$reported"
        return 0
        ;;
    esac
  fi

  printf '%s/.hermes\n' "$HOME"
}

HERMES_RUNTIME_HOME="$(resolve_hermes_runtime_home)"
AGENT_PLUGIN_DEST="$HERMES_RUNTIME_HOME/plugins/agent-center"
HERMES_AGENT_SKILL_DEST="$HERMES_RUNTIME_HOME/skills/agent-center"
CODEX_LINK="$HOME/.codex/skills/prompt-shortcuts"
CODEX_AGENT_LINK="$HOME/.codex/skills/agent-center"

# --- ที่อยู่เดิมที่ไฟล์ตัวเชื่อมทุกตัวในโปรเจกต์ชี้ถึง (ใช้ทำทางลัดชดเชยให้ Cursor) ---
OWNER_PATH="/Users/rattanasak/ObsidianVault/HermesAgent"

say() { printf '%s\n' "$*"; }

WANT_CURSOR=0
FORCE=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --cursor)
      WANT_CURSOR=1
      ;;
    --force)
      FORCE=1
      ;;
    *)
      say "ผิดพลาด: ไม่รู้จักตัวเลือก $1"
      say "วิธีใช้: bash install-shortcuts.sh [--cursor] [--force]"
      exit 1
      ;;
  esac
  shift
done

CONFLICTS=()

add_conflict_if_newer() {
  local src="$1"
  local dest="$2"
  local rel="$3"

  if [ -f "$dest" ] && ! cmp -s "$src" "$dest" && [ "$dest" -nt "$src" ]; then
    CONFLICTS+=("$rel")
  fi
}

is_generated_runtime_file() {
  case "$1" in
    */__pycache__/*|*.pyc|*.pyo|*/.DS_Store|.DS_Store) return 0 ;;
    *) return 1 ;;
  esac
}

add_destination_only_conflicts() {
  local src_root="$1"
  local dest_root="$2"
  local label="$3"

  [ -d "$dest_root" ] || return 0
  while IFS= read -r -d '' dest; do
    local rel="${dest#"$dest_root"/}"
    if [ ! -e "$src_root/$rel" ] && ! is_generated_runtime_file "$rel"; then
      CONFLICTS+=("$label/$rel (มีเฉพาะปลายทาง)")
    fi
  done < <(find "$dest_root" \( -type f -o -type l \) -print0)
}

detect_newer_destination_conflicts() {
  CONFLICTS=()

  add_conflict_if_newer \
    "$PAYLOAD/ai-context/prompt-shortcut-registry.md" \
    "$REGISTRY" \
    "ai-context/prompt-shortcut-registry.md"

  while IFS= read -r -d '' src; do
    local rel="${src#"$PAYLOAD"/}"
    add_conflict_if_newer "$src" "$DEST_ROOT/$rel" "$rel"
  done < <(find "$PAYLOAD/skills/prompt-shortcuts" -type f -print0)
  add_destination_only_conflicts \
    "$PAYLOAD/skills/prompt-shortcuts" \
    "$SKILL_SRC" \
    "skills/prompt-shortcuts"

  while IFS= read -r -d '' src; do
    local rel="${src#"$PAYLOAD"/}"
    add_conflict_if_newer "$src" "$DEST_ROOT/$rel" "$rel"
  done < <(find "$AGENT_SKILL_PAYLOAD" -type f -print0)
  add_destination_only_conflicts \
    "$AGENT_SKILL_PAYLOAD" \
    "$AGENT_SKILL_SRC" \
    "skills/agent-center"

  if [ -d "$CODEX_LINK" ] && [ ! -L "$CODEX_LINK" ]; then
    while IFS= read -r -d '' src; do
      local rel="${src#"$PAYLOAD/skills/prompt-shortcuts"/}"
      add_conflict_if_newer \
        "$src" \
        "$CODEX_LINK/$rel" \
        "Codex skill/prompt-shortcuts/$rel"
    done < <(find "$PAYLOAD/skills/prompt-shortcuts" -type f -print0)
    add_destination_only_conflicts \
      "$PAYLOAD/skills/prompt-shortcuts" \
      "$CODEX_LINK" \
      "Codex skill/prompt-shortcuts"
  fi

  if [ -d "$CODEX_AGENT_LINK" ] && [ ! -L "$CODEX_AGENT_LINK" ]; then
    while IFS= read -r -d '' src; do
      local rel="${src#"$AGENT_SKILL_PAYLOAD"/}"
      add_conflict_if_newer \
        "$src" \
        "$CODEX_AGENT_LINK/$rel" \
        "Codex skill/agent-center/$rel"
    done < <(find "$AGENT_SKILL_PAYLOAD" -type f -print0)
    add_destination_only_conflicts \
      "$AGENT_SKILL_PAYLOAD" \
      "$CODEX_AGENT_LINK" \
      "Codex skill/agent-center"
  fi

  while IFS= read -r -d '' src; do
    local rel="${src#"$AGENT_SKILL_PAYLOAD"/}"
    add_conflict_if_newer \
      "$src" \
      "$HERMES_AGENT_SKILL_DEST/$rel" \
      "Hermes runtime skill/agent-center/$rel"
  done < <(find "$AGENT_SKILL_PAYLOAD" -type f -print0)
  add_destination_only_conflicts \
    "$AGENT_SKILL_PAYLOAD" \
    "$HERMES_AGENT_SKILL_DEST" \
    "Hermes runtime skill/agent-center"

  while IFS= read -r -d '' src; do
    local rel="${src#"$AGENT_PLUGIN_SRC"/}"
    add_conflict_if_newer \
      "$src" \
      "$AGENT_PLUGIN_DEST/$rel" \
      "Hermes runtime plugin/agent-center/$rel"
  done < <(find "$AGENT_PLUGIN_SRC" -type f -print0)
  add_destination_only_conflicts \
    "$AGENT_PLUGIN_SRC" \
    "$AGENT_PLUGIN_DEST" \
    "Hermes runtime plugin/agent-center"
}

shortcuts_payload_differs() {
  if [ ! -f "$REGISTRY" ] || ! cmp -s "$PAYLOAD/ai-context/prompt-shortcut-registry.md" "$REGISTRY"; then
    return 0
  fi

  if ! diff -qr "$PAYLOAD/skills/prompt-shortcuts" "$SKILL_SRC" >/dev/null 2>&1; then
    return 0
  fi

  if ! diff -qr "$AGENT_SKILL_PAYLOAD" "$AGENT_SKILL_SRC" >/dev/null 2>&1; then
    return 0
  fi

  if ! diff -qr "$AGENT_SKILL_PAYLOAD" "$HERMES_AGENT_SKILL_DEST" >/dev/null 2>&1; then
    return 0
  fi

  if [ -d "$CODEX_AGENT_LINK" ] && [ ! -L "$CODEX_AGENT_LINK" ] \
    && ! diff -qr "$AGENT_SKILL_PAYLOAD" "$CODEX_AGENT_LINK" >/dev/null 2>&1; then
    return 0
  fi

  if [ -d "$CODEX_LINK" ] && [ ! -L "$CODEX_LINK" ] \
    && ! diff -qr "$PAYLOAD/skills/prompt-shortcuts" "$CODEX_LINK" >/dev/null 2>&1; then
    return 0
  fi

  if ! diff -qr "$AGENT_PLUGIN_SRC" "$AGENT_PLUGIN_DEST" >/dev/null 2>&1; then
    return 0
  fi

  return 1
}

prune_old_shortcuts_backups() {
  local backups=()
  local backup
  while IFS= read -r backup; do
    backups+=("$backup")
  done < <(find "$DEST_ROOT" -maxdepth 1 -type d -name '.backup-shortcuts-*' | sort)

  local count="${#backups[@]}"
  if [ "$count" -le 5 ]; then
    return 0
  fi

  local remove_count=$((count - 5))
  local i
  for ((i = 0; i < remove_count; i++)); do
    rm -rf -- "${backups[$i]}"
  done
}

backup_existing_shortcuts_if_needed() {
  if [ ! -d "$SKILL_SRC" ] && [ ! -d "$AGENT_SKILL_SRC" ] \
    && [ ! -d "$HERMES_AGENT_SKILL_DEST" ] && [ ! -d "$AGENT_PLUGIN_DEST" ] \
    && { [ ! -d "$CODEX_LINK" ] || [ -L "$CODEX_LINK" ]; } \
    && { [ ! -d "$CODEX_AGENT_LINK" ] || [ -L "$CODEX_AGENT_LINK" ]; }; then
    return 0
  fi

  if ! shortcuts_payload_differs; then
    return 0
  fi

  local stamp
  stamp="$(date +%Y%m%d-%H%M%S)"
  local backup_dir="$DEST_ROOT/.backup-shortcuts-$stamp"
  local suffix=1
  while [ -e "$backup_dir" ]; do
    backup_dir="$DEST_ROOT/.backup-shortcuts-$stamp-$suffix"
    suffix=$((suffix + 1))
  done

  mkdir -p "$backup_dir/ai-context" "$backup_dir/skills"
  if [ -f "$REGISTRY" ]; then
    cp "$REGISTRY" "$backup_dir/ai-context/"
  fi
  if [ -d "$SKILL_SRC" ]; then
    rsync -a "$SKILL_SRC/" "$backup_dir/skills/prompt-shortcuts/"
  fi
  if [ -d "$AGENT_SKILL_SRC" ]; then
    rsync -a "$AGENT_SKILL_SRC/" "$backup_dir/skills/agent-center/"
  fi
  if [ -d "$HERMES_AGENT_SKILL_DEST" ]; then
    rsync -a "$HERMES_AGENT_SKILL_DEST/" "$backup_dir/runtime-skills/agent-center/"
  fi
  if [ -d "$CODEX_AGENT_LINK" ] && [ ! -L "$CODEX_AGENT_LINK" ]; then
    rsync -a "$CODEX_AGENT_LINK/" "$backup_dir/codex-skills/agent-center/"
  fi
  if [ -d "$CODEX_LINK" ] && [ ! -L "$CODEX_LINK" ]; then
    rsync -a "$CODEX_LINK/" "$backup_dir/codex-skills/prompt-shortcuts/"
  fi
  if [ -d "$AGENT_PLUGIN_DEST" ]; then
    rsync -a "$AGENT_PLUGIN_DEST/" "$backup_dir/runtime-plugins/agent-center/"
  fi
  prune_old_shortcuts_backups
  say "      สำรองของเดิมไว้ที่ $backup_dir"
}

# --- ตรวจ payload ก่อน ---
if [ ! -f "$PAYLOAD/ai-context/prompt-shortcut-registry.md" ]; then
  say "ผิดพลาด: ไม่พบ payload ที่ $PAYLOAD — รันสคริปต์นี้จากในโฟลเดอร์ team-shortcuts"
  exit 1
fi
if [ ! -f "$VERSION_FILE" ]; then
  say "ผิดพลาด: ไม่พบหมายเลขชุดติดตั้งที่ $VERSION_FILE"
  exit 1
fi
if [ ! -f "$AGENT_SKILL_PAYLOAD/SKILL.md" ]; then
  say "ผิดพลาด: ไม่พบ Agent Center skill ที่ $AGENT_SKILL_PAYLOAD"
  exit 1
fi
if [ ! -f "$AGENT_PLUGIN_SRC/plugin.yaml" ]; then
  say "ผิดพลาด: ไม่พบ Agent Center plugin ที่ $AGENT_PLUGIN_SRC"
  exit 1
fi
if ! command -v hermes >/dev/null 2>&1; then
  say "ผิดพลาด: ไม่พบคำสั่ง hermes — Use Agent ต้องมี Hermes Agent ก่อนติดตั้ง"
  exit 1
fi
if ! command -v rsync >/dev/null 2>&1; then
  say "ผิดพลาด: ไม่พบ rsync — ต้องติดตั้ง rsync ก่อนเพื่อคัดชุด Shortcut ให้ตรงกัน"
  exit 1
fi
detect_newer_destination_conflicts
if [ "${#CONFLICTS[@]}" -gt 0 ] && [ "$FORCE" -eq 0 ]; then
  say "ไฟล์ปลายทางใหม่กว่าชุดติดตั้ง — จะไม่เขียนทับ"
  say "รายการไฟล์ที่เสี่ยงถูกทับ:"
  for conflict in "${CONFLICTS[@]}"; do
    say "  - $conflict"
  done
  say ""
  say "ทางเลือก:"
  say "  1. เครื่องเจ้าของระบบ: รัน team-shortcuts/sync-from-vault.sh ก่อน เพื่อดึงงานล่าสุดกลับเข้าชุดติดตั้ง"
  say "  2. เครื่องพนักงาน: ถ้าต้องการใช้ชุดติดตั้งทับจริง ให้รันซ้ำพร้อม --force"
  exit 2
fi

# --- 1) คัดชุด Shortcut เข้าโฟลเดอร์บ้าน ---
say "[1/4] คัดชุด Shortcut ไป $DEST_ROOT"
backup_existing_shortcuts_if_needed
mkdir -p "$DEST_ROOT/ai-context" "$DEST_ROOT/skills"
cp "$PAYLOAD/ai-context/prompt-shortcut-registry.md" "$DEST_ROOT/ai-context/"
mkdir -p "$SKILL_SRC"
rsync -a --delete "$PAYLOAD/skills/prompt-shortcuts/" "$SKILL_SRC/"
mkdir -p "$AGENT_SKILL_SRC" "$HERMES_AGENT_SKILL_DEST" "$AGENT_PLUGIN_DEST"
rsync -a --delete "$AGENT_SKILL_PAYLOAD/" "$AGENT_SKILL_SRC/"
rsync -a --delete "$AGENT_SKILL_PAYLOAD/" "$HERMES_AGENT_SKILL_DEST/"
rsync -a --delete --exclude='__pycache__/' "$AGENT_PLUGIN_SRC/" "$AGENT_PLUGIN_DEST/"
cp "$VERSION_FILE" "$INSTALLED_VERSION"
REF_COUNT="$(ls -1 "$SKILL_SRC/references/"*.md 2>/dev/null | wc -l | tr -d ' ')"
say "      สำเร็จ: รุ่น $(tr -d '[:space:]' < "$VERSION_FILE") · ทะเบียน 1 ไฟล์ + prompt $REF_COUNT ไฟล์"
say "      สำเร็จ: ติดตั้ง Agent Center skill และ plugin ที่ $HERMES_RUNTIME_HOME"
if ! hermes plugins enable agent-center >/dev/null; then
  say "ผิดพลาด: คัด Agent Center แล้ว แต่เปิดใช้ผ่าน Hermes Agent ไม่สำเร็จ"
  exit 1
fi
say "      สำเร็จ: เปิดใช้ Agent Center ใน Hermes Agent"

# ติดตั้งด่านล็อกงานเขียนให้ใช้ได้จากทุก project แม้ project นั้นไม่มี repo Hermes Agent
if [ ! -f "$WRITE_PERMIT_SRC" ]; then
  say "ผิดพลาด: ไม่พบด่านล็อกงานเขียนที่ $WRITE_PERMIT_SRC"
  exit 1
fi
mkdir -p "$HOME/.local/bin"
if ! cmp -s "$WRITE_PERMIT_SRC" "$WRITE_PERMIT_BIN"; then
  cp "$WRITE_PERMIT_SRC" "$WRITE_PERMIT_BIN"
fi
chmod 0755 "$WRITE_PERMIT_BIN"
say "      สำเร็จ: ติดตั้งด่านล็อกงานเขียนที่ $WRITE_PERMIT_BIN"
if [ ! -f "$HOOK_DOCTOR_SRC" ]; then
  say "ผิดพลาด: ไม่พบตัวตรวจสุขภาพ Hook ที่ $HOOK_DOCTOR_SRC"
  exit 1
fi
if ! cmp -s "$HOOK_DOCTOR_SRC" "$HOOK_DOCTOR_BIN"; then
  cp "$HOOK_DOCTOR_SRC" "$HOOK_DOCTOR_BIN"
fi
chmod 0755 "$HOOK_DOCTOR_BIN"
say "      สำเร็จ: ติดตั้งตัวตรวจสุขภาพ Hook ที่ $HOOK_DOCTOR_BIN"
if [ ! -f "$NEW_CHAT_INSTALLER" ]; then
  say "ผิดพลาด: ไม่พบตัวติดตั้ง New Chat ที่ $NEW_CHAT_INSTALLER"
  exit 1
fi
bash "$NEW_CHAT_INSTALLER"
if [ ! -f "$TEAM_HOOK_INSTALLER" ]; then
  say "ผิดพลาด: ไม่พบตัวติดตั้ง Hook ทีมที่ $TEAM_HOOK_INSTALLER"
  exit 1
fi
python3 "$TEAM_HOOK_INSTALLER"
if ! "$HOOK_DOCTOR_BIN" >/dev/null; then
  say "      ตัวตรวจ Hook รอบแรกไม่ผ่าน ลองตรวจ Hook ซ้ำอีก 1 ครั้ง"
  if ! "$HOOK_DOCTOR_BIN" >/dev/null; then
    say "ผิดพลาด: ติดตั้ง Hook แล้วแต่ตรวจ 6 ด่านไม่ผ่าน 2 รอบ"
    "$HOOK_DOCTOR_BIN" || true
    exit 1
  fi
fi
say "      สำเร็จ: Hook ภาษาคน/ผู้ตรวจอิสระ/หลักฐาน/คำตอบพื้นที่/ทำงานต่อเป็นเฟส/New Chat ผ่าน 6/6"

# --- 2) ต่อ Claude Code (ทุกโปรเจกต์ผ่าน global memory) ---
say "[2/4] ต่อ Claude Code ผ่าน ~/.claude/CLAUDE.md"
mkdir -p "$HOME/.claude"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"
touch "$CLAUDE_MD"
MARK_START="<!-- HERMES_SHORTCUTS_START -->"
MARK_END="<!-- HERMES_SHORTCUTS_END -->"
# ลบบล็อกเดิม (ถ้ามี) เพื่อให้รันซ้ำได้ไม่พัง
if grep -qF "$MARK_START" "$CLAUDE_MD"; then
  awk -v s="$MARK_START" -v e="$MARK_END" '
    $0==s{skip=1} !skip{print} $0==e{skip=0}' "$CLAUDE_MD" > "$CLAUDE_MD.tmp"
  mv "$CLAUDE_MD.tmp" "$CLAUDE_MD"
fi
{
  printf '\n%s\n' "$MARK_START"
  printf '## Prompt Shortcuts (ติดตั้งโดย install-shortcuts.sh)\n\n'
  printf 'เมื่อผู้ใช้เรียก Shortcut เช่น `Use Act-As`, `Use Comply`, `Use Continue`, `Review Chat` หรือชื่อย่อใกล้เคียง\n'
  printf 'ให้เปิดอ่านทะเบียนนี้ก่อนเสมอ แล้วเปิดไฟล์ prompt ที่แมปไว้ ห้ามเดาจากความจำ:\n\n'
  printf -- '- `%s`\n' "$REGISTRY"
  printf '%s\n' "$MARK_END"
} >> "$CLAUDE_MD"
say "      สำเร็จ: เพิ่มตัวชี้ทะเบียนใน $CLAUDE_MD"

# --- 3) ต่อ Codex (ทางลัด skill) ---
say "[3/4] ต่อ Codex ผ่าน ~/.codex/skills/prompt-shortcuts"
mkdir -p "$HOME/.codex/skills"
if [ -L "$CODEX_LINK" ] || [ -f "$CODEX_LINK" ]; then
  rm -f "$CODEX_LINK"
fi
if [ -L "$CODEX_AGENT_LINK" ] || [ -f "$CODEX_AGENT_LINK" ]; then
  rm -f "$CODEX_AGENT_LINK"
fi
if [ -e "$CODEX_AGENT_LINK" ] && [ ! -L "$CODEX_AGENT_LINK" ]; then
  say "      พบโฟลเดอร์เดิมที่ $CODEX_AGENT_LINK — คัดให้ตรงกับชุดติดตั้งล่าสุด"
  rsync -a --delete "$AGENT_SKILL_SRC/" "$CODEX_AGENT_LINK/"
else
  ln -s "$AGENT_SKILL_SRC" "$CODEX_AGENT_LINK"
  say "      สำเร็จ: $CODEX_AGENT_LINK -> $AGENT_SKILL_SRC"
fi
if [ -e "$CODEX_LINK" ] && [ ! -L "$CODEX_LINK" ]; then
  say "      พบโฟลเดอร์เดิมที่ $CODEX_LINK — คัดให้ตรงกับชุดติดตั้งล่าสุด"
  rsync -a --delete "$SKILL_SRC/" "$CODEX_LINK/"
else
  ln -s "$SKILL_SRC" "$CODEX_LINK"
  say "      สำเร็จ: $CODEX_LINK -> $SKILL_SRC"
fi

# --- 4) ต่อ Cursor (ทางลัดชดเชยที่อยู่เดิมของเจ้าของระบบ) ---
say "[4/4] ต่อ Cursor"
if [ "$WANT_CURSOR" -eq 0 ]; then
  say "      ข้าม (ไม่ได้ใส่ --cursor) — ถ้าพนักงานใช้ Cursor ให้รันตัวติดตั้งจาก GitHub พร้อม --cursor"
  say "      curl -fsSL https://raw.githubusercontent.com/rattanasak-ops/hermes-agent/main/team-shortcuts/install-from-github.sh | bash -s -- --cursor"
elif [ -e "$OWNER_PATH" ]; then
  say "      ที่อยู่ $OWNER_PATH มีอยู่แล้วบนเครื่องนี้ — ไม่ต้องทำทางลัด (น่าจะเป็นเครื่องเจ้าของระบบ)"
else
  OWNER_PARENT="$(dirname "$OWNER_PATH")"
  if mkdir -p "$OWNER_PARENT" 2>/dev/null && ln -snf "$DEST_ROOT" "$OWNER_PATH" 2>/dev/null; then
    say "      สำเร็จ: $OWNER_PATH -> $DEST_ROOT"
  else
    say "      ต้องใช้สิทธิ์ผู้ดูแล 1 ครั้ง สำหรับ Cursor — รันคำสั่งนี้:"
    say "        sudo mkdir -p \"$OWNER_PARENT\" && sudo ln -snf \"$DEST_ROOT\" \"$OWNER_PATH\""
  fi
fi

# ติดตั้งเครื่องมือ Use Migrate Web (MW) เป็นด่านบังคับของการติดตั้ง
MW_SETUP="$SCRIPT_DIR/../scripts/mw/mw-setup.sh"
if [ ! -f "$MW_SETUP" ]; then
  say "ผิดพลาด: ไม่พบตัวติดตั้งเครื่องมือ Use Migrate Web ที่ $MW_SETUP"
  exit 1
fi
say ""
say "ติดตั้งเครื่องมือ Use Migrate Web (MW)..."
if ! bash "$MW_SETUP"; then
  say "ผิดพลาด: ติดตั้งเครื่องมือ Use Migrate Web (MW) ไม่สำเร็จ"
  exit 1
fi

if [ -f "$SCRIPT_DIR/check-shortcuts.sh" ]; then
  say ""
  HERMES_SHORTCUT_EXPECTED_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")" \
    bash "$SCRIPT_DIR/check-shortcuts.sh"
fi

say ""
say "เสร็จสิ้น. ปิดแล้วเปิดโปรแกรม AI ใหม่ 1 รอบ แล้วลองพิมพ์ Shortcut เช่น  Use Comply"
