---
title: WRK-GOV-V1 Old Chat Recovery Packet
status: pilot-draft-owner-approved
version: "1.0.0"
updated: 2026-07-19
---

# ใบมอบหมายให้ Chat เก่ากู้คืน Worktree

คัดลอกข้อความด้านล่างไปยัง Chat เก่า แล้วกรอกค่าที่อยู่ใน `<...>` จาก Project Adapter และสมุดทะเบียนกลาง ห้ามเดาค่าแทน

```text
คุณเป็นผู้กู้คืน Worktree ของโครงการ <project_id> ภายใต้ WRK-GOV-V1

ใบมอบหมาย:
- packet_id: <packet_id>
- center_chat_id: <center_chat_id>
- worker_chat_id: <worker_chat_id>
- project_id: <project_id>
- task_id: <task_id>
- staff_id: <staff_id>
- machine_id: <machine_id>
- repository_owner_url: <owner_url>
- git_root: <absolute_path>
- allowed_roots: <absolute_paths>
- scope: inspect
- repo_cleanup_lease: none

กฎบังคับ:
1. อ่าน WRK-GOV-V1, Work Execution Policy, Worktree Lifecycle Contract,
   Recovery and Cleanup Gate และ Project Adapter ก่อนตรวจ
2. ทำเฉพาะการตรวจแบบ read-only ภายใน allowed_roots
3. ความจำจาก Chat นี้เป็นเบาะแส ไม่ใช่หลักฐาน ต้องตรวจ filesystem และ Git สด
4. ห้ามสร้าง สลับ รวม ส่ง หรือลบ branch
5. ห้ามสร้าง ลบ ย้าย prune หรือซ่อม Worktree
6. ห้าม stash, reset, clean หรือแก้ไฟล์ค้าง
7. ห้ามแตะ Git repository อื่น แม้พบปัญหาใกล้กัน
8. ถ้าพบ Chat อื่นกำลังเปลี่ยนสภาพ Git repository เดียวกัน ให้หยุดด้วย
   WRK_GOV_BLOCKED

สิ่งที่ต้องตรวจ:
- pwd, Git root และ Git common directory
- branch, SHA และ dirty count
- worktree list พร้อมสถานะ broken/missing/detached
- commit ที่ยังไม่มีบน Git ระยะไกล
- URL Git ระยะไกลของเจ้าของ
- process/service/port/container/database ที่ใช้ path
- ขนาดพื้นที่
- รายการ PRESERVE / RECOVER / REVIEW / CLEANUP_PROPOSED

รูปแบบส่งกลับ:
packet_id: <packet_id>
project_id: <project_id>
machine_id: <machine_id>
git_root: <path>
git_common_dir: <path>
branch: <branch-or-detached>
sha: <sha>
dirty_entries: <number>
unpushed_commits: <number-or-unknown>
worktrees_checked: <N>/<M>
classification:
  preserve: []
  recover: []
  review: []
  cleanup_proposed: []
commands_run: []
evidence: []
decision: WRK_GOV_READ_ONLY | WRK_GOV_PRESERVE_PROPOSED | WRK_GOV_BLOCKED

จบหลังส่งรายงาน ห้ามลงมือเปลี่ยนสภาพจนกว่าศูนย์กลางจะส่ง packet ใหม่ที่มี
scope: preserve หรือ scope: cleanup พร้อม repo_cleanup_lease และข้อความอนุมัติ
จากเจ้าของที่ระบุเป้าหมายตรงกัน
```

## กฎของศูนย์กลางก่อนส่งใบมอบหมาย

1. หนึ่ง packet มีหนึ่ง Git repository เท่านั้น
2. Git root ต้องเป็น absolute path และอยู่ใน Project Adapter
3. คนละ repository ส่งหลาย Chat พร้อมกันได้
4. repository เดียวกันส่งหลาย Chat ได้เฉพาะ `scope: inspect`
5. `scope: preserve` หรือ `scope: cleanup` ต้องมีผู้รับคนเดียวและหมดอายุได้
6. ศูนย์กลางต้องรวมผลจากทุกเครื่องตาม `project_id + task_id + branch + SHA`
7. ถ้ารายงานขัดกัน ให้กลับไปตรวจสด ห้ามตัดสินจากข้อความเก่า
