---
title: WRK-GOV-V1
aliases:
  - Worktree Governance Standard v1
  - มาตรฐานกลาง Worktree
tags:
  - prompt-shortcuts
  - worktree
  - governance
  - multi-machine
status: pilot-draft-owner-approved
version: "1.0.0"
updated: 2026-07-19
---

# WRK-GOV-V1 · มาตรฐานกลาง Worktree ทุกโครงการ

มาตรฐานนี้ใช้กับโครงการส่วนตัวทั้งหมดของเจ้าของ รวม Notebook เจ้าของ, Notebook พนักงาน และ VPS โดยแก้ปัญหาเดิมสามเรื่องพร้อมกัน:

1. Worktree กระจายหลายที่จนไม่รู้ว่าอันใดสำคัญ
2. branch เดียวถูกเขียนจากหลายเครื่องหรือหลาย Chat
3. Shortcut แต่ละตัวตีความกฎ Worktree ไม่เหมือนกัน

สถานะ `pilot-draft-owner-approved` หมายถึงเจ้าของอนุมัติให้สร้างและทดลองแล้ว แต่ยังห้ามประกาศใช้ทั้งทีมจนกว่าด่านในหัวข้อ 10 จะผ่านครบ

## 1. หลักสูงสุด

- branch คือรหัสงานที่ใช้ข้ามเครื่อง ส่วน Worktree เป็นพื้นที่ใช้งานเฉพาะเครื่องและเอาออกได้เมื่อมีหลักฐาน
- หนึ่ง task มีสิทธิ์เขียนได้หนึ่งเครื่องในเวลาเดียวกัน
- หนึ่ง Git repository มีผู้เคลียร์ Worktree ที่เปลี่ยนสภาพได้หนึ่ง Chat ในเวลาเดียวกัน
- Chat หลายตัวตรวจแบบอ่านอย่างเดียวได้ แต่ห้าม Chat หลายตัวลบ ย้าย `prune` หรือแก้ข้อมูล Worktree ของ Git repository เดียวกันพร้อมกัน
- `main`, `master`, `develop`, `development`, `production` และ `prod` เป็น branch ป้องกัน
- Shortcut ทุกตัวใช้พื้นที่ปัจจุบันและห้ามสร้าง ลบ ย้าย หรือสลับ Worktree เอง
- ก่อนลบต้องผ่านด่าน 6/6 และกักพักอย่างน้อย 72 ชั่วโมง
- ห้ามใช้ `rm -rf` เอา Worktree ออก ต้องผ่าน Worktree Manager เท่านั้น

## 2. เอกสารบังคับ 5 ส่วน

| ส่วน | แหล่งจริง | หน้าที่ |
|---|---|---|
| 1 | `work-execution-policy.md` | คุมการเขียนในพื้นที่ปัจจุบันและ branch ป้องกัน |
| 2 | `project-worktree-adapter.schema.json` | กำหนดข้อมูลเชื่อมของแต่ละโครงการและแต่ละเครื่อง |
| 3 | `worktree-registry-v2.schema.json` | กำหนดสมุดทะเบียนที่หนึ่ง task มีหลายตำแหน่งได้ |
| 4 | `recovery-cleanup-gate.md` | คุมการรักษา กู้คืน กักพัก และเอา Worktree ออก |
| 5 | `shortcut-worktree-contract.md` | ทำให้ Shortcut 33 กลุ่มใช้กฎเดียวกัน |

เอกสารประกอบ:

- `worktree-lifecycle-contract.md` เป็นวงจรชีวิตเดิมที่ยังใช้กับ Worktree Manager รุ่นปัจจุบัน
- `old-chat-recovery-packet.md` เป็นใบมอบหมายมาตรฐานสำหรับ Chat เก่า
- `hermes-agent.worktree-adapter.example.json` เป็น Pilot แบบอ่านอย่างเดียวของ Hermes Agent

## 3. ลำดับแหล่งจริง

เมื่อข้อมูลขัดกันให้ใช้ลำดับนี้:

```text
WRK-GOV-V1
→ Work Execution Policy
→ Project Adapter
→ สมุดทะเบียนกลาง
→ Git / process / service / filesystem ที่ตรวจสด
→ ความจำโครงการ
→ ข้อความเก่าใน Chat
```

Chat เก่าช่วยอธิบายเหตุผลของงานเดิมได้ แต่ไม่ใช่หลักฐานยืนยันสถานะปัจจุบัน

## 4. บทบาทเครื่อง

| เครื่อง | บทบาทตั้งต้น | สิทธิ์เขียน |
|---|---|---|
| Notebook เจ้าของ | จุดเขียนหลักและตรวจรวม | ได้เมื่อถือสิทธิ์ของ task |
| Notebook พนักงาน | จุดเขียนของงานที่มอบหมาย | ได้เฉพาะ task และ branch ของตน |
| VPS | จุดรัน ตรวจบริการ และเผยแพร่ | อ่านเป็นหลัก เขียนได้หลังส่งต่อสิทธิ์อย่างชัดเจน |

โครงการใดจำเป็นต้องใช้บทบาทต่างจากนี้ ต้องประกาศใน Project Adapter ห้าม Chat เดาเอง

## 5. รูปแบบ branch

```text
งานปกติ:       task/<staff-id>/<task-id>-<slug>
งานช่วยชีวิต:  rescue/<staff-id>/<incident-id>-<slug>
งานเร่งด่วน:   hotfix/<staff-id>/<task-id>-<slug>
```

- `task-id` ห้ามซ้ำข้ามเครื่อง
- branch ช่วยชีวิตใช้เก็บ commit ที่ยังไม่มีบน Git ระยะไกลก่อนการเคลียร์
- ห้ามลบ branch เพราะอายุหรือชื่อเก่าเพียงอย่างเดียว
- ชื่อ Git ระยะไกล เช่น `origin` หรือ `fork` เป็นชื่อเฉพาะเครื่อง ต้องยืนยันตัวตนด้วย URL ของคลังเจ้าของ

## 6. การแบ่งงานให้หลาย Chat

| ขอบเขต | ทำพร้อมกันได้หรือไม่ | กฎ |
|---|---:|---|
| คนละ Git repository | ได้ | หนึ่งใบมอบหมายต่อหนึ่งโครงการ |
| Git repository เดียวกันและตรวจอย่างเดียว | ได้ | ทุก Chat เป็น read-only และรายงาน SHA |
| Git repository เดียวกันและเขียนโค้ดคนละ task | ได้แบบจำกัด | คนละ branch, คนละ Worktree, หนึ่งสิทธิ์เขียนต่อ task |
| Git repository เดียวกันและเคลียร์ Worktree | ไม่ได้ | ให้ Chat เดียวถือ cleanup lease ของทั้ง repository |

Chat ศูนย์กลางทำหน้าที่ออกใบมอบหมาย รวมผล ตรวจการชน และขออนุมัติแบบรวมครั้งเดียว ส่วน Chat เก่าทำหน้าที่กู้คืนเฉพาะโครงการตาม `old-chat-recovery-packet.md`

## 7. วงจรกู้คืนโครงการเก่า

```text
INVENTORY
→ FREEZE
→ PRESERVE
→ RECOVER
→ REVIEW
→ CLEANUP_PROPOSED
→ QUARANTINED
→ ARCHIVED
```

- `INVENTORY` ถึง `REVIEW` ทำแบบอ่านอย่างเดียวได้ ยกเว้นการสร้างหรือส่ง branch ช่วยชีวิตซึ่งต้องอนุมัติ
- `CLEANUP_PROPOSED` เป็นเพียงแผนพร้อมหลักฐาน ยังไม่ลบ
- `QUARANTINED` ต้องรักษาเส้นทางกู้คืนครบและรอตรวจซ้ำ
- `ARCHIVED` ใช้ได้เมื่อ Worktree ถูกเอาออกผ่าน Manager และมีประวัติย้อนกลับได้

## 8. สมุดทะเบียนรุ่น 2

รุ่น 2 เปลี่ยนจากหนึ่ง task ต่อหนึ่ง `worktree_path` เป็นหนึ่ง task ต่อหลาย `placements` หรือหลายตำแหน่ง เช่น Notebook, VPS และเครื่องพนักงาน โดยยังมี `write_lease` ได้หนึ่งชุดเท่านั้น

Worktree Manager รุ่นปัจจุบันยังใช้ `worktree-lifecycle-v1` จึงต้องทำตัวแปลงและชุดทดสอบก่อนย้ายทะเบียนจริง ห้ามเปลี่ยนไฟล์ทะเบียนใช้งานจริงด้วยมือ

## 9. Decision token

| Token | ความหมาย |
|---|---|
| `WRK_GOV_READ_ONLY` | ตรวจได้ แต่ไม่มีสิทธิ์เปลี่ยนสภาพ |
| `WRK_GOV_PRESERVE_PROPOSED` | พบสิ่งที่ควรเก็บรักษา รออนุมัติแบบระบุเป้าหมาย |
| `WRK_GOV_REPO_CLEANER_CLAIMED` | Git repository นี้มี Chat ผู้เคลียร์แล้ว |
| `WRK_GOV_CLEANUP_PROPOSED` | ด่านลบพร้อมให้เจ้าของตรวจ แต่ยังไม่ลบ |
| `WRK_GOV_BLOCKED` | หลักฐานขัดกันหรือขอบเขตไม่ปลอดภัย |
| `WRK_GOV_ARCHIVED` | เอา Worktree ออกผ่าน Manager และมีหลักฐานกู้คืน |

## 10. ด่านประกาศใช้

WRK-GOV-V1 จะเปลี่ยนเป็น `active` ได้เมื่อครบ:

1. เอกสารบังคับ 5/5 อ่านได้และเชื่อมกัน
2. Shortcut 33/33 กลุ่มรับสัญญากลางผ่าน `SKILL.md`
3. Project Adapter ของ Hermes Agent ผ่านตัวตรวจ
4. ทะเบียนรุ่น 2 มีตัวแปลงจากรุ่น 1 และทดสอบการย้อนกลับ
5. Pilot Hermes Agent ผ่าน Notebook และ VPS โดยไม่สูญเสีย commit หรือไฟล์ค้าง
6. เจ้าของตรวจผล Pilot และอนุมัติการติดตั้งให้ทีม

ก่อนครบ 6/6 ให้ใช้เฉพาะ Pilot และการตรวจแบบอ่านอย่างเดียว ห้ามนำทะเบียนรุ่น 2 ไปแทนทะเบียนจริง
