---
title: Use New Chat
aliases:
  - Use New Chat
  - use-new-chat
  - Start New Chat
  - New Chat Startup
  - Initialize Hermes Agent chat
  - เริ่ม New Chat
  - เปิด New Chat
  - เริ่มแชทใหม่
  - เปิดแชทใหม่
tags:
  - prompt-shortcuts
  - new-chat
  - startup-gate
status: active
version: "4.3"
updated: 2026-07-19
schema: memory-schema-v1.2
execution_policy: work-execution-policy >= 2.0
default_mode: CURRENT_WORKSPACE_ONLY
---

# Use New Chat (v4.3 · 2026-07-19)

## Shortcut

```text
Use New Chat
```

## Prompt

[ด่าน Goal Contract] อ่าน [[skills/prompt-shortcuts/references/goal-contract|goal-contract.md]] ก่อนเริ่ม · ต้องตรวจว่าใบรับรองความจำมี `task_id/plan_id/goal_hash` ตรง `.project/active-task.json` แม้แฮชไฟล์ทุกไฟล์จะตรง · ต่างกันให้รายงาน `PROJECT_GOAL_DRIFT` และห้ามซ่อมด้วยการเขียนทับ · งานถัดไปคัดจาก `next_prompt` เพียงหนึ่งบรรทัดในรูป `Prompt ถัดไป:` หรือ `AUTO_CONTINUE:` และแสดงเป็น `Prompt ที่ควรใช้ต่อ` หลังสรุป Phase เมื่อต้องส่งต่อ

```text
Use New Chat

เป้าหมาย: เปิดแชทโดยเรียนรู้โปรเจกต์และตรวจพื้นที่ที่เจ้าของเปิดอยู่ ห้ามสร้างหรือสลับ Worktree/กิ่ง
อ่าน `work-execution-policy.md` ก่อนใช้กฎด้านล่าง

[กฎสูงสุด — CURRENT_WORKSPACE_ONLY]
- ใช้ `pwd` และ Git root ที่แอปเปิดอยู่เท่านั้น
- Shortcut นี้ห้ามเรียก `hermes-new-chat open`, `hermes worktree open`, `git worktree add/remove`, `git switch`, `git checkout` และคำสั่งสร้าง/สลับกิ่ง
- การพิมพ์ `Use New Chat` ไม่ใช่คำอนุมัติให้สร้าง Worktree หรือกิ่ง
- คำสั่งสั้นแยกต่างหากจากเจ้าของที่ระบุชื่อกิ่งตรง ๆ ใช้ `OWNER_EXPLICIT_BRANCH_ONLY`: AI สร้างกิ่งชื่อนั้นใน Git root ปัจจุบันได้หนึ่งครั้ง ห้ามสร้าง Worktree และห้ามผลักให้เจ้าของเปิด Terminal เอง
- ข้อความยาวที่วางเป็นตัวอย่าง ประวัติแชท และชื่อกิ่งที่ AI คิดเองไม่ใช่คำอนุมัติ
- Worktree ที่เปิดอยู่แล้วใช้ได้เหมือนโฟลเดอร์ Git ปกติ แต่ห้ามสร้างเพิ่ม ย้ายเข้าเอง หรือเก็บกวาดเอง
- ถ้า Git root ตรงงานแต่หลุดเป็น detached HEAD ให้รัน `hermes-current-workspace-recover --cwd <Git root> --json` ตาม `SYSTEM_REGISTERED_BRANCH_RECOVERY` ก่อนตัดสินสถานะ; ถ้าอยู่กิ่งร่วมให้คืน `PROTECTED_BRANCH_WRITE_BLOCKED` โดยไม่สลับกิ่ง
- ใช้ AI Relay เฉพาะเมื่อเจ้าของเรียก `Use AI Relay` โดยชัดเจน
- ผู้ตรวจและวิธีเดิมใช้ได้สูงสุด 2 รอบต่อปัญหา ถ้ายังไม่ผ่านให้เปลี่ยนเป็น test/lint/build หรือผู้ตรวจอื่น ห้ามเรียกรอบที่ 3

[ขั้น 1 — อ่านความจำ]
- ก่อนเชื่อไฟล์ความจำ ให้รัน `memory_receipt.py --cwd <Git root> verify` จาก Hook ที่ติดตั้ง หรือจาก `team-shortcuts/hooks/` ใน repo ชุดกระจาย
- `MEMORY_RECEIPT_OK` = อ่านชุดไฟล์ตามใบรับรองได้ แล้วเทียบ branch/SHA/dirty กับ Git จริงอีกครั้ง
- `PROJECT_MEMORY_DRIFT` = พบไฟล์คนละรอบ แฮชไม่ตรง ไฟล์ใหม่กว่าใบรับรอง หรือสายรอบวน; ห้ามเขียนทับเพื่อซ่อมเอง ให้ใช้ Git และไฟล์จริงแบบอ่านอย่างเดียว พร้อมรายงานไฟล์ที่ผิด
- `PROJECT_MEMORY_RECEIPT_MISSING` = โปรเจกต์เก่ายังไม่มีใบรับรอง; ระบุว่าเป็นสถานะยังไม่รับรอง ใช้ Git จริงเป็นหลัก และห้ามอ้างว่า memory ทั้งชุดตรงกัน
- อ่าน `.project/OverviewProgress.md` แล้วอ่านไฟล์ตามสารบัญบังคับ โดยอย่างน้อยต้องตรวจ `.project/plan.md` และ `.project/decisions.md` เมื่อมี
- อ่าน `latest-close.md` หรือ session log ล่าสุดเมื่อมี แล้วเทียบกับ Git จริง ห้ามเชื่อสถานะเก่าโดยไม่ตรวจ
- ถ้ามีสเปคที่จับคู่กับแผน `.project/spec/<plan_id>.md` ให้ตรวจ status และ owner approval; สเปค draft บล็อกเฉพาะงานโค้ดใต้แผนนั้น
- ห้ามโหลดประวัติทั้งหมดโดยไม่จำเป็น ให้ดึงเฉพาะเป้าหมาย ข้อห้าม งานค้าง และหลักฐานล่าสุด

[ขั้น 2 — ตรวจพื้นที่จริง]
รันแบบอ่านอย่างเดียว:
- `pwd`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short --branch`
- `git worktree list --porcelain` เพื่อรายงานเท่านั้น ห้ามเปลี่ยนรายการ

[ขั้น 3 — ตัดสินสถานะ]
- งานอ่านอย่างเดียว → `CURRENT_WORKSPACE_READ_ONLY`
- งานเขียนผ่านได้เมื่อ Git root ตรงพื้นที่ปัจจุบัน, ไม่ detached HEAD, กิ่งไม่ใช่ main/master/develop/development/production/prod, เป้าหมายอยู่ใน root และไฟล์ค้างไม่ชนงานอื่น → `CURRENT_WORKSPACE_READY`
- ถ้า detached HEAD → กู้จากสมุดทะเบียนใน Git root เดิมก่อน; สำเร็จแล้วตรวจซ้ำ ไม่สำเร็จให้รายงานรหัสจากเครื่อง
- ถ้าอยู่กิ่งร่วม → `PROTECTED_BRANCH_WRITE_BLOCKED`; ห้ามกู้หรือสลับกิ่งอัตโนมัติ
- ถ้าพื้นที่ผิดโครงการ → `WORKSPACE_SCOPE_MISMATCH`; ห้ามผลักให้ผู้ใช้เปิด/สร้าง/switch workspace, Worktree, folder หรือ branch
- เงื่อนไขอื่นไม่ครบ → `CURRENT_WORKSPACE_BLOCKED`; ถ้าเจ้าของสั่งสร้างกิ่งพร้อมชื่อชัดเจน ให้ AI ทำตามข้อยกเว้นกลางได้
- ถ้า dirty เป็นไฟล์ของงานเดียวกันและอยู่ในขอบเขต ให้ทำต่อได้โดยรักษาไฟล์เดิม; ถ้าไม่รู้เจ้าของหรือทับงานอื่น ให้บล็อกเฉพาะไฟล์ที่เสี่ยง

[ขั้น 4 — ด่านสุขภาพ]
- รัน `hermes-hook-doctor` เมื่อมี และตรวจว่าทั้ง Codex App, Claude Code App, Cursor และ Hermes Agent ใช้กฎเดียวกัน
- ด่านต้องยอมให้แอปปัจจุบันเขียนตรงและรัน pnpm dev/test/lint/build ได้เมื่อพื้นที่พร้อม
- ด่านต้องขวางการเขียนข้าม root, กิ่งร่วม, detached HEAD, `.env`, `.hermes`, `.grok`, secret, การแก้ Hook/Settings และคำสั่งอันตราย
- AI Relay หรือ New Chat session หายต้องไม่ทำให้พื้นที่ที่พร้อมกลายเป็น blocked

[ขั้น 5 — สรุป 3 บรรทัด]
- โปรเจกต์นี้คืออะไรและ Process อยู่ขั้นไหน
- งานล่าสุดถึงไหน โดยอ้าง branch/SHA/ไฟล์ค้างจริง
- งานถัดไปหนึ่งข้อที่ตรงกับคำสั่งเจ้าของ

[รายงานบังคับ]
Project:
Current workspace:
Git root:
Branch:
HEAD:
Dirty:
Memory/Plan/Spec:
Memory receipt: MEMORY_RECEIPT_OK / PROJECT_MEMORY_DRIFT / PROJECT_MEMORY_RECEIPT_MISSING
Hook health:
AI Relay: OPTIONAL หรือ OWNER_REQUESTED
Decision: CURRENT_WORKSPACE_READY / CURRENT_WORKSPACE_READ_ONLY / CURRENT_WORKSPACE_BLOCKED
Blocked reason:
Next action:

ห้ามตอบว่า “พร้อม” โดยไม่มีผลคำสั่งจริง ห้ามแก้ไฟล์ก่อนรายงาน เว้นแต่เจ้าของสั่งให้ทำต่อจากงานที่อนุมัติไว้ชัดเจนในแชทเดียวกัน
```

## Worktree แบบอ่านและจัดการของเดิมเท่านั้น

ถ้าเจ้าของพิมพ์คำสั่งให้ตรวจ ส่งต่อ ปิด หรือเก็บกวาด Worktree ที่มีอยู่ จึงอ่าน `worktree-lifecycle-contract.md` เพิ่ม ด่าน AI ไม่เปิด Worktree ใหม่

## Changelog

- v4.3 (2026-07-19 · SCG-P3): ตรวจ `.project/memory-receipt.json` ก่อนเชื่อความจำ · สถานะผสมคืน `PROJECT_MEMORY_DRIFT` และห้ามเขียนทับเอง
- v4.2 (2026-07-19): เพิ่มการกู้กิ่งจากสมุดทะเบียนใน Git root เดิม · ห้ามผลักการเปิดพื้นที่/กิ่งกลับไปให้ผู้ใช้
- v4.1 (2026-07-18): เพิ่ม `OWNER_EXPLICIT_BRANCH_ONLY` · AI สร้างกิ่งตามชื่อที่เจ้าของสั่งตรง ๆ ได้โดยไม่สร้าง Worktree · กันข้อความตัวอย่างยาว
- v4.0 (2026-07-18): เปลี่ยนเป็น `CURRENT_WORKSPACE_ONLY` · ยกเลิกการสร้าง/สลับ Worktree และกิ่งจาก Shortcut · AI Relay เป็นทางเลือก · ใช้สถานะกลาง 3 ค่า
- v3.0 (2026-07-18): งานอ่านไม่สร้าง Worktree · AI ในแอปเขียนตรงได้เมื่อ WTL พร้อม · AI Relay เป็นทางเลือก

## Graph Links

- [[skills/prompt-shortcuts/references/next-action-contract|Next Action Contract]]
- [[skills/prompt-shortcuts/references/work-execution-policy|Work Execution Policy]]
- [[skills/prompt-shortcuts/references/use-close-chat|Use Close Chat]]
- [[ai-context/prompt-shortcut-registry|Prompt Shortcut Registry]]
