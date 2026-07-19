---
task_id: SHORTCUT-P7-I1
goal_id: SHORTCUT-CENTRAL-CLOSE-20260719
status: owner_input_required_team_machine_access
writer: codex-current-task
external_ai_relay: disabled
workspace_policy: current_workspace_only
worktree: /Users/rattanasak/Documents/Worktrees/hermes-agent/nat/SHORTCUT-P1-I1-team-rollout-hardening-team-rollout-hardening
branch: task/nat/SHORTCUT-P1-I1-team-rollout-hardening-team-rollout-hardening
plan: .project/plan.md
plan_index: .project/plan-index.md
---

# ใบล็อกเป้าหมาย — SHORTCUT-P7-I1

## เป้าหมายแม่

ปิด Shortcut กลางให้เข้า `main` ติดตั้ง Mac/VPS/เครื่องทีม และทำให้ AI ทุกโปรเจกต์ยึดพื้นที่ปัจจุบันโดยไม่สร้าง Worktree เอง

## สถานะหลักฐาน

- ต้นเหตุและด่านรวมโค้ดแก้แล้ว 6/6
- PR #84 และ #85 รวมเข้า `main` แล้ว 2/2
- Mac ผ่านทุกด่านที่เกี่ยวข้อง 7 ชุด
- VPS ผ่าน Shortcut 33/33, Hook 6/6 และ MW 7/7
- แผนกลาง 10 ชุดแยกหนึ่ง `plan_id` ต่อไฟล์ และ active 1/1
- เครื่องทีมรายบุคคลยังไม่มีบัญชี host/ช่องทางเข้าถึง 0/1 งานรวม

## ขั้นตอนถัดไปเพียงหนึ่งขั้น

เมื่อเจ้าของให้บัญชีเครื่องทีมที่เข้าถึงได้ ให้รันตัวติดตั้งจาก `main` และบันทึกผลตรวจแยกต่อเครื่อง โดยไม่คัดลอกทั้ง Obsidian vault และไม่สร้าง Worktree ใหม่
