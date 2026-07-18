#!/usr/bin/env bash
#
# check-shortcuts.sh — ตรวจเครื่องพนักงานว่า Prompt Shortcut ต่อครบหรือไม่
#
# ใช้ได้โดยไม่ต้องมี repo Hermes Agent:
#   curl -fsSL https://raw.githubusercontent.com/rattanasak-ops/hermes-agent/main/team-shortcuts/check-shortcuts.sh | bash
#
set -euo pipefail

ROOT="$HOME/ObsidianVault/HermesAgent"
REGISTRY="$ROOT/ai-context/prompt-shortcut-registry.md"
SKILL="$ROOT/skills/prompt-shortcuts/SKILL.md"
INDEX="$ROOT/skills/prompt-shortcuts/Prompt Shortcuts.md"
REFS="$ROOT/skills/prompt-shortcuts/references"
CODEX="$HOME/.codex/skills/prompt-shortcuts"
AGENT_SKILL="$ROOT/skills/agent-center/SKILL.md"
CODEX_AGENT="$HOME/.codex/skills/agent-center"
CLAUDE="$HOME/.claude/CLAUDE.md"
INSTALLED_VERSION="$ROOT/.shortcut-version"
HOOK_DOCTOR="$HOME/.local/bin/hermes-hook-doctor"
WRITE_PERMIT="$HOME/.local/bin/hermes-write-permit"

resolve_hermes_runtime_home() {
  if [ -n "${HERMES_HOME:-}" ]; then
    printf '%s\n' "$HERMES_HOME"
    return 0
  fi
  if command -v hermes >/dev/null 2>&1; then
    local reported
    reported="$(hermes dump 2>/dev/null | sed -n 's/^hermes_home:[[:space:]]*//p' | head -n 1)"
    case "$reported" in
      "~") printf '%s\n' "$HOME"; return 0 ;;
      "~/"*) printf '%s/%s\n' "$HOME" "${reported#\~/}"; return 0 ;;
      /*) printf '%s\n' "$reported"; return 0 ;;
    esac
  fi
  printf '%s/.hermes\n' "$HOME"
}

HERMES_RUNTIME_HOME="$(resolve_hermes_runtime_home)"
HERMES_AGENT_SKILL="$HERMES_RUNTIME_HOME/skills/agent-center/SKILL.md"
AGENT_PLUGIN="$HERMES_RUNTIME_HOME/plugins/agent-center/plugin.yaml"
HERMES_CONFIG="$HERMES_RUNTIME_HOME/config.yaml"

pass=true

count_table() {
  local path="$1"
  [ -f "$path" ] || { echo 0; return; }
  grep -c '^| `' "$path" 2>/dev/null || true
}

count_skill_map() {
  local path="$1"
  [ -f "$path" ] || { echo 0; return; }
  awk '
    /^## Shortcut Map/ { on=1; next }
    on && /^## / { on=0 }
    on && /^\| `/ { n++ }
    END { print n+0 }
  ' "$path"
}

print_check() {
  local label="$1"
  local value="$2"
  local expected="$3"
  if [ "$value" = "$expected" ]; then
    printf 'PASS %-28s %s\n' "$label" "$value"
  else
    printf 'FAIL %-28s %s (ควรเป็น %s)\n' "$label" "$value" "$expected"
    pass=false
  fi
}

match_check() {
  local label="$1"
  local left="$2"
  local right="$3"
  if [ "$left" = "$right" ]; then
    printf 'PASS %-28s %s\n' "$label" "$left"
  else
    printf 'FAIL %-28s %s ไม่ตรงกับ %s\n' "$label" "$left" "$right"
    pass=false
  fi
}

exists_check() {
  local label="$1"
  local path="$2"
  if [ -e "$path" ]; then
    printf 'PASS %-28s %s\n' "$label" "$path"
  else
    printf 'FAIL %-28s ไม่พบ %s\n' "$label" "$path"
    pass=false
  fi
}

same_tree_check() {
  local label="$1"
  local expected="$2"
  local actual="$3"
  if [ -d "$expected" ] && [ -d "$actual" ] \
    && diff -qr "$expected" "$actual" >/dev/null 2>&1; then
    printf 'PASS %-28s %s\n' "$label" "$actual"
  else
    printf 'FAIL %-28s %s\n' "$label" "เนื้อหาไม่ตรงกับ $expected"
    pass=false
  fi
}

echo "══ ตรวจ Prompt Shortcut บนเครื่องนี้ ══"
exists_check "registry_exists" "$REGISTRY"
exists_check "skill_exists" "$SKILL"
exists_check "index_exists" "$INDEX"
exists_check "codex_link_exists" "$CODEX"
exists_check "agent_center_skill_exists" "$AGENT_SKILL"
exists_check "codex_agent_link_exists" "$CODEX_AGENT"
exists_check "hermes_agent_skill_exists" "$HERMES_AGENT_SKILL"
exists_check "agent_center_plugin_exists" "$AGENT_PLUGIN"
same_tree_check "agent_center_codex_match" "$(dirname "$AGENT_SKILL")" "$CODEX_AGENT"
same_tree_check "agent_center_hermes_match" "$(dirname "$AGENT_SKILL")" "$(dirname "$HERMES_AGENT_SKILL")"
exists_check "hook_doctor_exists" "$HOOK_DOCTOR"
exists_check "write_permit_exists" "$WRITE_PERMIT"
exists_check "installed_version_exists" "$INSTALLED_VERSION"

if [ -f "$HERMES_CONFIG" ] && awk '
  /^plugins:[[:space:]]*$/ { in_plugins=1; in_enabled=0; next }
  in_plugins && /^[^[:space:]]/ { in_plugins=0; in_enabled=0 }
  in_plugins && /^  enabled:[[:space:]]*$/ { in_enabled=1; next }
  in_plugins && in_enabled && /^  [[:alnum:]_-]+:/ { in_enabled=0 }
  in_plugins && in_enabled && /^[[:space:]]*-[[:space:]]*agent-center([[:space:]]*(#.*)?)?$/ { found=1 }
  END { exit(found ? 0 : 1) }
' "$HERMES_CONFIG"; then
  printf 'PASS %-28s %s\n' "agent_center_enabled" "$HERMES_CONFIG"
else
  printf 'FAIL %-28s %s\n' "agent_center_enabled" "ไม่พบ agent-center ใน plugins.enabled"
  pass=false
fi

migrate_phase_count=0
for phase in $(seq 0 13); do
  migrate_phase_file="$REFS/use-migrate-$phase.md"
  exists_check "use_migrate_${phase}_exists" "$migrate_phase_file"
  if [ -f "$migrate_phase_file" ]; then
    migrate_phase_count=$((migrate_phase_count + 1))
  fi
done
print_check "use_migrate_phase_coverage" "$migrate_phase_count" "14"
exists_check "migrate_contract_exists" "$REFS/use-migrate-phase-contract.md"

if [ -f "$CLAUDE" ] && grep -q 'HERMES_SHORTCUTS_START' "$CLAUDE"; then
  printf 'PASS %-28s %s\n' "claude_bridge_exists" "$CLAUDE"
else
  printf 'FAIL %-28s ไม่พบตัวชี้ Shortcut ใน %s\n' "claude_bridge_exists" "$CLAUDE"
  pass=false
fi

if [ -x "$HOOK_DOCTOR" ] && "$HOOK_DOCTOR" >/dev/null 2>&1; then
  printf 'PASS %-28s %s\n' "hook_health" "4/4"
else
  printf 'FAIL %-28s %s\n' "hook_health" "ด่านจริงไม่ผ่าน"
  pass=false
fi

registry_count="$(count_table "$REGISTRY")"
skill_count="$(count_skill_map "$SKILL")"
index_count="$(count_table "$INDEX")"
match_check "registry_vs_skill" "$registry_count" "$skill_count"
match_check "registry_vs_index" "$registry_count" "$index_count"
prompt_count=0
if [ -d "$REFS" ]; then
  prompt_count="$(find "$REFS" -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')"
fi
if [ "$prompt_count" -ge "$registry_count" ] 2>/dev/null; then
  printf 'PASS %-28s %s (คำสั่งลัด %s)\n' "prompt_file_coverage" "$prompt_count" "$registry_count"
else
  printf 'FAIL %-28s %s น้อยกว่าคำสั่งลัด %s\n' "prompt_file_coverage" "$prompt_count" "$registry_count"
  pass=false
fi

expected_version="${HERMES_SHORTCUT_EXPECTED_VERSION:-}"
if [ -z "$expected_version" ] && command -v curl >/dev/null 2>&1; then
  # ใช้ GitHub Contents API แทน raw URL เพื่อไม่อ่านรุ่นเก่าจาก CDN cache หลังเพิ่งอัปเดต
  expected_version="$(curl -fsSL -H 'Accept: application/vnd.github.raw+json' \
    'https://api.github.com/repos/rattanasak-ops/hermes-agent/contents/team-shortcuts/VERSION?ref=main' \
    2>/dev/null | tr -d '[:space:]' || true)"
fi
installed_version=""
if [ -f "$INSTALLED_VERSION" ]; then
  installed_version="$(tr -d '[:space:]' < "$INSTALLED_VERSION")"
fi
if [ -n "$expected_version" ]; then
  print_check "shortcut_version" "$installed_version" "$expected_version"
else
  printf 'WARN %-28s ตรวจรุ่นล่าสุดจาก GitHub ไม่ได้\n' "shortcut_version"
fi

# เช็ค "กติกาสัญญา" ไม่เช็คเลขรุ่นตายตัว (บทเรียน 2026-07-15: pin 2.6 ค้างหลังไฟล์อัปเป็น 2.7
# → RESULT: FAIL แบบเงียบทุกเครื่องทีม · ความสดของรุ่นมีด่าน shortcut_version เทียบ GitHub อยู่แล้ว)
if [ -f "$REFS/use-new-chat.md" ]; then
  if grep -q 'ห้ามเรียกรอบที่ 3' "$REFS/use-new-chat.md"; then
    printf 'PASS %-28s %s\n' "new_chat_contract" "กติกาหยุด 2 รอบครบ"
  else
    printf 'FAIL %-28s %s\n' "new_chat_contract" "ไม่พบกติกาหยุด 2 รอบใน use-new-chat.md"
    pass=false
  fi
fi

echo ""
if [ "$pass" = true ]; then
  echo "RESULT: PASS"
  echo "เครื่องนี้ต่อ Prompt Shortcut พร้อมใช้ $registry_count/$registry_count · รุ่น $installed_version"
else
  echo "RESULT: FAIL"
  echo "ให้รันตัวติดตั้งใหม่:"
  echo "curl -fsSL https://raw.githubusercontent.com/rattanasak-ops/hermes-agent/main/team-shortcuts/install-from-github.sh | bash"
  exit 1
fi
