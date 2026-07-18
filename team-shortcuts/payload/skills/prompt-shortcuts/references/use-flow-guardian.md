---
title: Use Flow Guardian
aliases:
  - Use Flow Guardian
  - use-flow-guardian
  - Flow Guardian
  - Safe Flow
  - ใช้ Flow Guardian
  - ใช้ Safe Flow
  - ตรวจ worktree
  - กัน AI แก้งานทับกัน
tags:
  - prompt-shortcuts
  - safe-workflow
  - workspace
status: active
version: "2.1"
updated: 2026-07-18
execution_policy: work-execution-policy >= 2.0
default_mode: CURRENT_WORKSPACE_ONLY
---

# Use Flow Guardian (v2.1 · 2026-07-18)

## Shortcut

```text
Use Flow Guardian
```

## Prompt

```text
Use Flow Guardian

เป้าหมาย: ตรวจว่าพื้นที่และกิ่งที่เจ้าของเปิดอยู่ปลอดภัยสำหรับงานนี้ โดยไม่เปลี่ยน Git ให้เจ้าของ

1. รัน `pwd`, `git rev-parse --show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`, `git status --short --branch` และ `git worktree list --porcelain` แบบอ่านอย่างเดียว
2. เทียบเป้าหมายและไฟล์ที่จะเขียนกับ Git root ปัจจุบัน
3. ตรวจว่าไม่ใช่ detached HEAD และไม่ใช่ main/master/develop/development/production/prod
4. แยกไฟล์ค้างเป็น: อยู่ในงานเดียวกัน / อยู่นอกขอบเขตแต่ไม่ทับ / ไม่ทราบเจ้าของหรือทับงาน
5. ตรวจไฟล์ลับและคำสั่งอันตรายตาม `work-execution-policy.md`
6. คืนสถานะเดียว: CURRENT_WORKSPACE_READY, CURRENT_WORKSPACE_READ_ONLY หรือ CURRENT_WORKSPACE_BLOCKED

ข้อห้าม:
- ห้ามสร้าง ลบ ย้าย หรือสลับ Worktree/กิ่ง
- ห้ามเรียก hermes-new-chat open หรือ hermes worktree open
- ห้าม stash, reset, clean, ย้าย หรือลบไฟล์ค้างเพื่อทำให้สถานะดูสะอาด
- ห้ามบังคับ AI Relay
- ห้ามแก้ไฟล์ในรอบตรวจ เว้นแต่เจ้าของสั่งแก้ไว้ชัดเจนแล้ว

รายงาน:
- Project / Current workspace / Git root
- Branch / HEAD / Dirty
- เป้าหมายและขอบเขตไฟล์
- ไฟล์ค้างที่อาจชนงาน
- ด่านไฟล์ลับและคำสั่งอันตราย
- Decision + เหตุผล + การกระทำถัดไปหนึ่งข้อ
```

## Worktree แบบสั่งตรงเท่านั้น

ถ้าเจ้าของสั่งตรวจวงจรชีวิต Worktree ที่มีอยู่ ให้โหลด `worktree-lifecycle-contract.md` เพิ่มได้ แต่ Flow Guardian ยังมีสิทธิ์อ่านและรายงานเท่านั้น

คำสั่งสั้นแยกต่างหากจากเจ้าของที่ระบุชื่อกิ่งตรง ๆ ไม่ใช่งานตรวจของ Flow Guardian และให้ทำตาม `OWNER_EXPLICIT_BRANCH_ONLY` ในกติกากลาง โดยห้ามสร้าง Worktree

## Changelog

- v2.1 (2026-07-18): ระบุว่าคำสั่งสร้างกิ่งตรงจากเจ้าของใช้กติกากลางได้ แต่ Flow Guardian เองยังอ่านอย่างเดียวและไม่เปิด Worktree
- v2.0 (2026-07-18): ตรวจพื้นที่ปัจจุบันอย่างเดียว · ไม่สร้าง/สลับ Worktree หรือกิ่ง · ไม่บังคับ AI Relay
- v1.1 (2026-06-24): เพิ่มรายงาน Git และไฟล์ค้าง

## Links

- [[skills/prompt-shortcuts/references/work-execution-policy|Work Execution Policy]]
- [[skills/prompt-shortcuts/references/use-new-chat|Use New Chat]]
