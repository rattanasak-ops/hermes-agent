---
title: WRK-GOV-V1 Shortcut Worktree Contract
status: pilot-draft-owner-approved
version: "1.0.0"
updated: 2026-07-19
shortcut_family_count: 33
---

# สัญญา Worktree สำหรับ Shortcut 33 กลุ่ม

Shortcut ทุกกลุ่มรับกฎนี้ผ่าน `SKILL.md` ก่อนอ่าน Prompt เฉพาะตัว จึงไม่ต้องคัดกฎยาวซ้ำลงทุกไฟล์

## 1. ลำดับอ่านบังคับ

ทุก Shortcut:

1. อ่าน `next-action-contract.md`
2. อ่าน `work-execution-policy.md`
3. อ่าน Prompt ของ Shortcut ที่เจ้าของเรียก
4. ถ้าเจ้าของสั่งตรวจ ส่งต่อ ปิด หรือเคลียร์ Worktree ให้โหลดเพิ่ม:
   - `wrk-gov-v1.md`
   - `shortcut-worktree-contract.md`
   - `worktree-lifecycle-contract.md`
   - `recovery-cleanup-gate.md`
   - Project Adapter ของโครงการ

## 2. กฎร่วม 33/33

- ใช้ Git root และ branch ที่แอปเปิดอยู่
- ตรวจ path, Git root, common directory, branch, SHA และไฟล์ค้างก่อนเขียน
- ห้ามสร้าง ลบ ย้าย หรือสลับ Worktree เอง
- ห้ามสร้างหรือสลับ branch จากชื่อที่ AI คิดเอง
- ห้ามให้ Chat เก่าหรือ AI ผู้ตรวจมีสิทธิ์เขียนโดยปริยาย
- ห้ามใช้ Git ระยะไกลจากชื่อ alias อย่างเดียว ต้องเทียบ URL เจ้าของ
- ห้ามลบ Worktree เพราะ Git test ตก ไฟล์ค้าง หรือพื้นที่ใกล้เต็ม
- ถ้าเป็นงาน Worktree ของ Git repository เดียวกัน ให้มีผู้เคลียร์หนึ่ง Chat
- ผู้ตรวจหลาย Chat ใช้ SHA เดียวกันและเป็น read-only

## 3. พฤติกรรมตามกลุ่มงาน

| กลุ่ม | ทำได้ | ห้าม |
|---|---|---|
| เริ่ม/ทำต่อ/ปิด Chat | ตรวจสถานะและส่งต่องาน | เปิดหรือเอา Worktree ออก |
| วางแผน/ตรวจ/สรุป | อ่านหลายโครงการตามขอบเขต | เปลี่ยน branch หรือ Worktree |
| เขียน/แก้/ย้ายไฟล์ | ทำในพื้นที่ปัจจุบันที่ผ่านด่าน | เขียนข้าม Git root |
| Save Git/ขึ้นระบบ | ตรวจและทำตามอนุมัติเฉพาะงาน | ใช้การส่ง Git เป็นเหตุลบ Worktree |
| AI หลายตัว | แบ่งผลิตและตรวจตาม task/SHA | ให้ผู้ตรวจเขียนหรือถือสิทธิ์ซ้ำ |
| Move Folder | จัดการโฟลเดอร์ที่ไม่ใช่ข้อมูล Git ตามทะเบียนของมัน | ย้าย `.git` หรือ Worktree นอก Manager |

## 4. Chat เก่า

Chat เก่าต้องรับ `old-chat-recovery-packet.md` ที่กรอก project, machine, Git root และ task id แล้ว จึงเริ่มตรวจได้ ความจำเดิมใช้เป็นเบาะแสเท่านั้นและต้องตรวจสดทุกข้อ

Chat เก่าคนละโครงการทำพร้อมกันได้ Chat เก่าของ Git repository เดียวกันตรวจพร้อมกันได้เฉพาะ read-only ส่วนการรักษา branch หรือเคลียร์ Worktree ต้องใช้ผู้ถือ `repo_cleanup_lease` คนเดียว

## 5. ตัวตรวจขั้นต่ำ

ตัวตรวจ WRK-GOV-V1 ต้องยืนยัน:

1. ตาราง Shortcut มี 33/33 กลุ่ม
2. Prompt ที่ลงทะเบียนทุกไฟล์มีอยู่จริง
3. `SKILL.md` บังคับอ่าน Work Execution Policy ทุกครั้ง
4. คำขอจัดการ Worktree บังคับอ่าน WRK-GOV-V1 และ Recovery/Cleanup Gate
5. Project Adapter ของ Pilot อ่านได้และอ้างเครื่องที่มีอยู่จริง
6. การตรวจ Pilot ไม่สร้าง branch ไม่แก้ไฟล์ และไม่ลบ Worktree

ก่อนผ่านครบ 6/6 สถานะเป็น `WRK_GOV_BLOCKED` หรือ `WRK_GOV_READ_ONLY` เท่านั้น
