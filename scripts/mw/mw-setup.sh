#!/usr/bin/env bash
# mw-setup — ติดตั้งเครื่องมือ Use Migrate Web (MW) ให้เรียกได้จากทุกที่
#
# ใช้ได้ 2 ทาง (notebook + VPS): ทีม pull repo แล้วรันสคริปต์นี้ครั้งเดียวต่อเครื่อง
#   bash scripts/mw/mw-setup.sh
# ทำ symlink เครื่องมือ 7 ตัว + mw-spec-check เข้า ~/.local/bin (หรือ $MW_BIN_DIR)
# แล้ว "ยิงทดสอบจริง" ทุกตัว (--help ต้อง exit 0) — ไม่ใช่แค่เจอไฟล์
# (บทเรียน relay: รุ่นติดตั้ง ≠ repo · ต้องรันจริงถึงจะนับว่าใช้ได้)
#
# portable: ไม่ใช้ bash associative array (รองรับ bash 3.2 ของ macOS)
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MW_DIR="$SCRIPT_DIR"                      # scripts/mw
REPO_SCRIPTS="$(cd "$SCRIPT_DIR/.." && pwd)"  # scripts
BIN_DIR="${MW_BIN_DIR:-$HOME/.local/bin}"
PYTHON="${MW_PYTHON:-python3}"

# name:relative-path (path เทียบกับ scripts/mw)
TOOLS="
mw-work-locks:work_locks.py
mw-menu-gate:menu_gate.py
mw-page-check:page_check.py
mw-doctor:mw_doctor.py
mw-rtm-report:rtm_report.py
mw-wow-report:wow_report.py
mw-backend-check:backend_check.py
mw-spec-check:../mw-spec-check.py
"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ผิดพลาด: ไม่พบ $PYTHON — ต้องมี Python 3.9+ ก่อนติดตั้งเครื่องมือ MW" >&2
  exit 1
fi

mkdir -p "$BIN_DIR"

installed=0
failed=0
echo "== mw-setup: ติดตั้งเครื่องมือ MW เข้า $BIN_DIR =="

for pair in $TOOLS; do
  name="${pair%%:*}"
  rel="${pair##*:}"
  src="$MW_DIR/$rel"
  # normalize (../mw-spec-check.py → scripts/mw-spec-check.py)
  src="$(cd "$(dirname "$src")" && pwd)/$(basename "$src")"
  if [ ! -f "$src" ]; then
    echo "  ❌ ไม่พบไฟล์: $src"
    failed=$((failed + 1))
    continue
  fi
  chmod +x "$src" 2>/dev/null || true
  ln -sf "$src" "$BIN_DIR/$name"
  installed=$((installed + 1))
done

echo "== ยิงทดสอบจริง (--help ต้อง exit 0) =="
smoke_fail=0
for pair in $TOOLS; do
  name="${pair%%:*}"
  bin="$BIN_DIR/$name"
  [ -e "$bin" ] || continue
  if "$PYTHON" "$bin" --help >/dev/null 2>&1; then
    echo "  ✅ $name"
  else
    echo "  ❌ $name (รัน --help ไม่ผ่าน)"
    smoke_fail=$((smoke_fail + 1))
  fi
done

echo "== สรุป: symlink $installed ตัว · ทดสอบไม่ผ่าน $smoke_fail · หาไฟล์ไม่เจอ $failed =="
if [ "$smoke_fail" -ne 0 ] || [ "$failed" -ne 0 ]; then
  echo "ยังไม่พร้อม 100% — แก้รายการ ❌ ก่อน (ตรวจ Python/ไฟล์)" >&2
  exit 1
fi

case ":$PATH:" in
  *":$BIN_DIR:"*) : ;;
  *) echo "หมายเหตุ: $BIN_DIR ยังไม่อยู่ใน PATH — เพิ่มบรรทัดนี้ใน ~/.zshrc หรือ ~/.bashrc:"
     echo "  export PATH=\"$BIN_DIR:\$PATH\"" ;;
esac
echo "mw-setup เสร็จ · เครื่องมือครบ 8 (7 ตัว + mw-spec-check) เรียกได้แล้ว"
