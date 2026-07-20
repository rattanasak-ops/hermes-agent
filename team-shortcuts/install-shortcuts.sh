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
MANIFEST_FILE="$SCRIPT_DIR/BUNDLE-MANIFEST.json"
BUNDLE_VERIFY_SRC="$SCRIPT_DIR/verify-bundle.py"
DEST_ROOT="${HERMES_SHORTCUTS_DEST:-$HOME/ObsidianVault/HermesAgent}"
REGISTRY="$DEST_ROOT/ai-context/prompt-shortcut-registry.md"
SKILL_SRC="$DEST_ROOT/skills/prompt-shortcuts"
AGENT_CENTER_SRC="$DEST_ROOT/skills/agent-center"
WRITE_PERMIT_SRC="$SCRIPT_DIR/../scripts/hermes_write_permit.py"
WRITE_PERMIT_BIN="$HOME/.local/bin/hermes-write-permit"
HOOK_DOCTOR_SRC="$SCRIPT_DIR/team-hook-doctor.py"
HOOK_DOCTOR_BIN="$HOME/.local/bin/hermes-hook-doctor"
INSTALLED_VERSION="$DEST_ROOT/.shortcut-version"
INSTALLED_MANIFEST="$DEST_ROOT/.shortcut-manifest.json"
BUNDLE_VERIFY_BIN="$HOME/.local/bin/hermes-shortcut-verify"
TEAM_HOOK_INSTALLER="$SCRIPT_DIR/install-team-hooks.py"
ALLOW_DOWNGRADE="${HERMES_SHORTCUT_ALLOW_DOWNGRADE:-0}"
BACKUP_ROOT="${HERMES_SHORTCUT_BACKUP_ROOT:-$HOME/.hermes/backups/shortcuts}"
BACKUP_QUARANTINE="$HOME/.hermes/quarantine/shortcut-backups"

# --- ที่อยู่เดิมที่ไฟล์ตัวเชื่อมทุกตัวในโปรเจกต์ชี้ถึง (ใช้ทำทางลัดชดเชยให้ Cursor) ---
OWNER_PATH="/Users/rattanasak/ObsidianVault/HermesAgent"

say() { printf '%s\n' "$*"; }

version_key() {
  printf '%s\n' "$1" | awk -F '[.-]' '{ printf "%04d%02d%02d%04d\n", $1, $2, $3, $4 }'
}

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

detect_newer_destination_conflicts() {
  CONFLICTS=()

  add_conflict_if_newer \
    "$PAYLOAD/ai-context/prompt-shortcut-registry.md" \
    "$REGISTRY" \
    "ai-context/prompt-shortcut-registry.md"

  while IFS= read -r -d '' src; do
    local rel="${src#"$PAYLOAD"/}"
    add_conflict_if_newer "$src" "$DEST_ROOT/$rel" "$rel"
  done < <(find \
    "$PAYLOAD/skills/prompt-shortcuts" "$PAYLOAD/skills/agent-center" \
    -type f ! -name '.DS_Store' ! -name '._*' -print0)
}

shortcuts_payload_differs() {
  if [ ! -f "$REGISTRY" ] || ! cmp -s "$PAYLOAD/ai-context/prompt-shortcut-registry.md" "$REGISTRY"; then
    return 0
  fi

  if ! diff -qr --exclude='.DS_Store' --exclude='._*' \
    "$PAYLOAD/skills/prompt-shortcuts" "$SKILL_SRC" >/dev/null 2>&1; then
    return 0
  fi

  if ! diff -qr --exclude='.DS_Store' --exclude='._*' \
    "$PAYLOAD/skills/agent-center" "$AGENT_CENTER_SRC" >/dev/null 2>&1; then
    return 0
  fi

  return 1
}

prune_old_shortcuts_backups() {
  local backups=()
  local backup
  while IFS= read -r backup; do
    backups+=("$backup")
  done < <(find "$BACKUP_ROOT" -maxdepth 1 -type d -name 'backup-*' | sort)

  local count="${#backups[@]}"
  if [ "$count" -le 5 ]; then
    return 0
  fi

  local remove_count=$((count - 5))
  local i
  for ((i = 0; i < remove_count; i++)); do
    mkdir -p "$BACKUP_QUARANTINE"
    local name
    name="$(basename "${backups[$i]}")-$(date +%s)-$i"
    mv "${backups[$i]}" "$BACKUP_QUARANTINE/$name"
  done
}

migrate_legacy_shortcuts_backups() {
  local legacy
  if [ ! -d "$DEST_ROOT" ]; then
    return 0
  fi
  mkdir -p "$BACKUP_ROOT"
  while IFS= read -r legacy; do
    [ -n "$legacy" ] || continue
    local name target suffix
    name="$(basename "$legacy")"
    target="$BACKUP_ROOT/legacy-$name"
    suffix=1
    while [ -e "$target" ]; do
      target="$BACKUP_ROOT/legacy-$name-$suffix"
      suffix=$((suffix + 1))
    done
    mv "$legacy" "$target"
  done < <(find "$DEST_ROOT" -maxdepth 1 -type d -name '.backup-shortcuts-*' | sort)
}

backup_existing_shortcuts_if_needed() {
  if [ ! -d "$SKILL_SRC" ]; then
    return 0
  fi

  if ! shortcuts_payload_differs; then
    return 0
  fi

  local stamp
  stamp="$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BACKUP_ROOT"
  local backup_dir="$BACKUP_ROOT/backup-$stamp"
  local suffix=1
  while [ -e "$backup_dir" ]; do
    backup_dir="$BACKUP_ROOT/backup-$stamp-$suffix"
    suffix=$((suffix + 1))
  done

  mkdir -p "$backup_dir/ai-context" "$backup_dir/skills"
  if [ -f "$REGISTRY" ]; then
    cp "$REGISTRY" "$backup_dir/ai-context/"
  fi
  rsync -a --exclude '.DS_Store' --exclude '._*' \
    "$SKILL_SRC/" "$backup_dir/skills/prompt-shortcuts/"
  if [ -d "$AGENT_CENTER_SRC" ]; then
    rsync -a --exclude '.DS_Store' --exclude '._*' \
      "$AGENT_CENTER_SRC/" "$backup_dir/skills/agent-center/"
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
if [ ! -f "$MANIFEST_FILE" ] || [ ! -f "$BUNDLE_VERIFY_SRC" ]; then
  say "ผิดพลาด: ชุดติดตั้งขาดใบรายการแฮชหรือตัวตรวจ"
  exit 1
fi
if ! python3 "$BUNDLE_VERIFY_SRC" verify-package \
  --team-root "$SCRIPT_DIR" --manifest "$MANIFEST_FILE" >/dev/null; then
  say "ผิดพลาด: แฮชไฟล์ในชุดติดตั้งไม่ตรงกับใบรายการ จะไม่ติดตั้ง"
  python3 "$BUNDLE_VERIFY_SRC" verify-package \
    --team-root "$SCRIPT_DIR" --manifest "$MANIFEST_FILE" || true
  exit 1
fi
PACKAGE_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
if [ -f "$INSTALLED_VERSION" ]; then
  CURRENT_VERSION="$(tr -d '[:space:]' < "$INSTALLED_VERSION")"
  if [ -n "$CURRENT_VERSION" ] \
    && [[ "$(version_key "$CURRENT_VERSION")" > "$(version_key "$PACKAGE_VERSION")" ]] \
    && [ "$ALLOW_DOWNGRADE" != "1" ]; then
    say "หยุดติดตั้ง: เครื่องนี้มี Shortcut รุ่น $CURRENT_VERSION ซึ่งใหม่กว่าชุด $PACKAGE_VERSION"
    say "ชุดเก่าจะไม่ถูกนำกลับมาทับชุดใหม่ หากเจ้าของตั้งใจย้อนรุ่นจริงต้องกำหนด HERMES_SHORTCUT_ALLOW_DOWNGRADE=1"
    exit 3
  fi
fi
for required in \
  "$PAYLOAD/skills/prompt-shortcuts/references/use-agent.md" \
  "$PAYLOAD/skills/prompt-shortcuts/references/work-execution-policy.md" \
  "$PAYLOAD/skills/prompt-shortcuts/references/wrk-gov-v1.md" \
  "$PAYLOAD/skills/prompt-shortcuts/references/project-worktree-adapter.schema.json" \
  "$PAYLOAD/skills/prompt-shortcuts/references/worktree-registry-v2.schema.json" \
  "$PAYLOAD/skills/prompt-shortcuts/references/recovery-cleanup-gate.md" \
  "$PAYLOAD/skills/prompt-shortcuts/references/shortcut-worktree-contract.md" \
  "$PAYLOAD/skills/prompt-shortcuts/references/old-chat-recovery-packet.md" \
  "$PAYLOAD/skills/agent-center/SKILL.md"; do
  if [ ! -f "$required" ]; then
    say "ผิดพลาด: ชุดติดตั้งขาดไฟล์ควบคุม $required"
    exit 1
  fi
done
if ! grep -q '| `Use Agent`' "$PAYLOAD/skills/prompt-shortcuts/SKILL.md"; then
  say "ผิดพลาด: ชุดติดตั้งยังไม่ได้ลงทะเบียน Use Agent"
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
migrate_legacy_shortcuts_backups
backup_existing_shortcuts_if_needed
mkdir -p "$DEST_ROOT/ai-context" "$DEST_ROOT/skills"
cp "$PAYLOAD/ai-context/prompt-shortcut-registry.md" "$DEST_ROOT/ai-context/"
mkdir -p "$SKILL_SRC"
rsync -a --delete --exclude '.DS_Store' --exclude '._*' \
  "$PAYLOAD/skills/prompt-shortcuts/" "$SKILL_SRC/"
mkdir -p "$AGENT_CENTER_SRC"
rsync -a --delete --exclude '.DS_Store' --exclude '._*' \
  "$PAYLOAD/skills/agent-center/" "$AGENT_CENTER_SRC/"
cp "$VERSION_FILE" "$INSTALLED_VERSION"
cp "$MANIFEST_FILE" "$INSTALLED_MANIFEST"
if ! cmp -s "$PAYLOAD/ai-context/prompt-shortcut-registry.md" "$REGISTRY" \
  || ! diff -qr --exclude='.DS_Store' --exclude='._*' \
    "$PAYLOAD/skills/prompt-shortcuts" "$SKILL_SRC" >/dev/null 2>&1 \
  || ! diff -qr --exclude='.DS_Store' --exclude='._*' \
    "$PAYLOAD/skills/agent-center" "$AGENT_CENTER_SRC" >/dev/null 2>&1; then
  say "ผิดพลาด: ไฟล์ที่ติดตั้งไม่ตรงกับชุดแจก จะไม่รายงานว่าพร้อมใช้"
  exit 1
fi
REF_COUNT="$(ls -1 "$SKILL_SRC/references/"*.md 2>/dev/null | wc -l | tr -d ' ')"
say "      สำเร็จ: รุ่น $(tr -d '[:space:]' < "$VERSION_FILE") · ทะเบียน 1 ไฟล์ + prompt $REF_COUNT ไฟล์ + Agent Center 1 ชุด"

# ติดตั้งด่านล็อกงานเขียนให้ใช้ได้จากทุก project แม้ project นั้นไม่มี repo Hermes Agent
if [ ! -f "$WRITE_PERMIT_SRC" ]; then
  say "ผิดพลาด: ไม่พบด่านล็อกงานเขียนที่ $WRITE_PERMIT_SRC"
  exit 1
fi
mkdir -p "$HOME/.local/bin"
if ! cmp -s "$BUNDLE_VERIFY_SRC" "$BUNDLE_VERIFY_BIN"; then
  cp "$BUNDLE_VERIFY_SRC" "$BUNDLE_VERIFY_BIN"
fi
chmod 0755 "$BUNDLE_VERIFY_BIN"
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
if [ ! -f "$TEAM_HOOK_INSTALLER" ]; then
  say "ผิดพลาด: ไม่พบตัวติดตั้ง Hook ทีมที่ $TEAM_HOOK_INSTALLER"
  exit 1
fi
python3 "$TEAM_HOOK_INSTALLER"
# ตัวช่วยติดตั้ง Hook รุ่นเก่าอาจมีรายชื่อค้าง จึงคัดทุก Hook จากชุดที่
# ใบรายการตรวจแล้วซ้ำอีกชั้น เพื่อให้เครื่องว่างได้รับไฟล์ครบเสมอ
for hook_root in "$HOME/.claude/hooks" "$HOME/.codex/hooks"; do
  mkdir -p "$hook_root"
  for hook_src in "$SCRIPT_DIR/hooks/"*.py; do
    hook_name="$(basename "$hook_src")"
    case "$hook_name" in
      ._*|.*) continue ;;
    esac
    cp "$hook_src" "$hook_root/$hook_name"
    chmod 0755 "$hook_root/$hook_name"
  done
done
if ! "$BUNDLE_VERIFY_BIN" verify-installed \
  --root "$DEST_ROOT" \
  --hook-root "$HOME/.claude/hooks" \
  --hook-root "$HOME/.codex/hooks" \
  --manifest "$INSTALLED_MANIFEST" >/dev/null; then
  say "ผิดพลาด: ไฟล์ที่ติดตั้งหรือด่านก่อนส่งมีแฮชไม่ตรง"
  "$BUNDLE_VERIFY_BIN" verify-installed \
    --root "$DEST_ROOT" \
    --hook-root "$HOME/.claude/hooks" \
    --hook-root "$HOME/.codex/hooks" \
    --manifest "$INSTALLED_MANIFEST" || true
  exit 1
fi
if ! "$HOOK_DOCTOR_BIN" >/dev/null; then
  say "ผิดพลาด: ติดตั้ง Hook แล้วแต่ตรวจ 3 ด่านไม่ผ่าน"
  "$HOOK_DOCTOR_BIN" || true
  exit 1
fi
say "      สำเร็จ: Hook ภาษาคน/ผู้ตรวจอิสระ/หลักฐานครบ ผ่าน 3/3"

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
  printf 'เมื่อผู้ใช้เรียก Shortcut เช่น `Use Act-As`, `Use Comply`, `Use Agent`, `Use Continue`, `Review Chat` หรือชื่อย่อใกล้เคียง\n'
  printf 'ให้เปิดอ่านทะเบียนนี้ก่อนเสมอ แล้วเปิดไฟล์ prompt ที่แมปไว้ ห้ามเดาจากความจำ:\n\n'
  printf -- '- `%s`\n' "$REGISTRY"
  printf '%s\n' "$MARK_END"
} >> "$CLAUDE_MD"
say "      สำเร็จ: เพิ่มตัวชี้ทะเบียนใน $CLAUDE_MD"

# --- 3) ต่อ Codex (ทางลัด skill) ---
say "[3/4] ต่อ Codex ผ่าน ~/.codex/skills/prompt-shortcuts"
mkdir -p "$HOME/.codex/skills"
CODEX_LINK="$HOME/.codex/skills/prompt-shortcuts"
if [ -L "$CODEX_LINK" ] || [ -f "$CODEX_LINK" ]; then
  rm -f "$CODEX_LINK"
fi
if [ -e "$CODEX_LINK" ] && [ ! -L "$CODEX_LINK" ]; then
  say "      พบโฟลเดอร์เดิมที่ $CODEX_LINK — คัดให้ตรงกับชุดติดตั้งล่าสุด"
  rsync -a --delete --exclude '.DS_Store' --exclude '._*' \
    "$SKILL_SRC/" "$CODEX_LINK/"
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

say ""
say "เสร็จสิ้น. ปิดแล้วเปิดโปรแกรม AI ใหม่ 1 รอบ แล้วลองพิมพ์ Shortcut เช่น  Use Comply"

# ติดตั้งเครื่องมือ Use Migrate Web (MW) ถ้ามีใน repo — best-effort (ไม่ทำ shortcut install พัง)
MW_SETUP="$SCRIPT_DIR/../scripts/mw/mw-setup.sh"
if [ -f "$MW_SETUP" ]; then
  say ""
  say "ติดตั้งเครื่องมือ Use Migrate Web (MW)..."
  bash "$MW_SETUP" || say "  (ข้ามเครื่องมือ MW ชั่วคราว — ติดตั้งภายหลังด้วย: bash scripts/mw/mw-setup.sh)"
fi

if [ -f "$SCRIPT_DIR/check-shortcuts.sh" ]; then
  say ""
  HERMES_SHORTCUT_EXPECTED_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")" \
    HERMES_SHORTCUT_EXPECTED_MANIFEST="$MANIFEST_FILE" \
    bash "$SCRIPT_DIR/check-shortcuts.sh"
fi
