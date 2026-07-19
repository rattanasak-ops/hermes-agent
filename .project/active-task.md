---
task_id: UAG-P0-I1
goal_id: UAG-P0-I1-CODEX-20260719
status: gate_passed_git_pending
owner_decision_at: 2026-07-19
writer: codex-current-chat
external_ai_relay: disabled
worktree: /Users/rattanasak/Documents/Worktrees/hermes-agent/nat/UAG-P1-I1-agent-center-foundation
branch: task/nat/UAG-P1-I1-agent-center-foundation
base_sha: 5ac0a4a261250842759dca59cbe897c4cd098485
plan: .project/plan.md
---

# ใบล็อกเป้าหมาย — UAG-P0-I1

## เป้าหมาย

ซ่อมกติกาการเปิด Worktree ให้คงเพดาน 3 งานต่อคนและโครงการ โดยนับเฉพาะงาน `ACTIVE/PAUSED`, ไม่นับ `BLOCKED`, รองรับสิทธิ์พิเศษที่เจ้าของอนุมัติ และค้นงานเดิมแบบอ่านอย่างเดียวก่อนเปิดงานใหม่

## คำสั่งล่าสุดของเจ้าของ

- อนุมัติ UAG-P0 ทั้งเฟสและให้ทำต่อแบบ Use Continue โดยไม่ถามเรื่องย่อย
- ให้ Codex ในแชทนี้ลงมือโดยตรง; ห้ามเรียก AI Relay, Opus, Grok หรือ AI Portal
- PR #79 รวมเข้า `main` แล้ว 1/1 เมื่อ 2026-07-19 เวลา 10:49 น.

## ขอบเขตที่เขียนได้

- `hermes_cli/worktree_lifecycle.py`
- `tests/hermes_cli/test_worktree_lifecycle.py`
- `.project/active-task.md`
- `.project/plan.md`
- `.project/ledger/**`
- `.project/gate-output/**`

## ขอบเขตที่ห้ามแตะ

- แกนสนทนา Hermes Agent, Gateway, ปลั๊กอิน Agent Center และหน้าจอ
- คลัง Obsidian และความรู้ถาวร
- VPS, ระบบจริง, ความลับ และ `main`

## เกณฑ์ผ่าน

- `BLOCKED` ไม่กินเพดาน 1/1
- `ACTIVE/PAUSED` กินเพดาน 1/1
- งานที่ 4 ถูกขวาง 1/1
- `--allow-over-limit` เปิดเกินเพดานได้เมื่อได้รับสิทธิ์ 1/1
- `worktree find` ค้นงานเดิมโดยไม่แก้สมุดทะเบียน 1/1

## หลักฐานปัจจุบัน

- ชุด Worktree Lifecycle ผ่าน 31/31
- ชุดสัญญาร่วมที่เกี่ยวข้องผ่านรวม 40/40
- Ruff ผ่าน 2/2 ไฟล์
- Python compile ผ่าน 2/2 ไฟล์
- `git diff --check` ผ่าน 1/1
- `gate-run` ผ่าน 40/40 ที่ commit `bb3901c7a1a251b2c85b1869b8f69caf22d9f178` และเขียนหลักฐานครบ 1/1 แถว
- ยังไม่มีผู้ตรวจ AI คนละตัวตามข้อยกเว้นที่เจ้าของสั่ง จึงไม่อ้างว่าผ่านกฎ 2 สมอง

## ขั้นตอนถัดไปเพียงหนึ่งขั้น

บันทึกหลักฐาน Git, ผ่านด่าน `save-git`, ส่งกิ่ง และเปิด PR แยกจาก Agent Center
