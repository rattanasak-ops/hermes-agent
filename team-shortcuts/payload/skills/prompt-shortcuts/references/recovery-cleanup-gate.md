---
title: WRK-GOV-V1 Recovery and Cleanup Gate
status: pilot-draft-owner-approved
version: "1.0.0"
updated: 2026-07-19
---

# ด่านกู้คืนและเคลียร์ Worktree

เอกสารนี้ใช้เมื่อเจ้าของสั่งตรวจ กู้คืน ปิด หรือเคลียร์ Worktree เก่าโดยตรง การเรียก Shortcut ปกติไม่ให้สิทธิ์เปลี่ยนสภาพ Worktree

## 1. ล็อกระดับ Git repository

ก่อนเปลี่ยนสภาพ Worktree ต้องมี `repo_cleanup_lease` หนึ่งชุดต่อ Git common directory ไม่ใช่หนึ่งชุดต่อโฟลเดอร์ Worktree

```yaml
repository_id: <owner-url-hash>
git_common_dir: <absolute-realpath>
cleaner_chat_id: <chat-or-task-id>
machine_id: <machine-id>
claimed_at: <ISO-8601>
expires_at: <ISO-8601>
scope: inspect|preserve|cleanup
```

- หลาย Chat ตรวจแบบอ่านอย่างเดียวได้โดยใช้ `scope: inspect`
- `preserve` และ `cleanup` มีผู้ถือได้หนึ่ง Chat ต่อ Git repository
- ถ้าไม่รู้ `git_common_dir` หรือพบผู้ถือสิทธิ์ซ้ำ ให้คืน `WRK_GOV_BLOCKED`

## 2. ขั้นตรวจแบบไม่แก้ไข

ต้องเก็บหลักฐานอย่างน้อย:

1. `pwd`, Git root และ Git common directory
2. branch และ SHA ของทุก Worktree
3. จำนวนไฟล์ค้างและรายชื่อโดยไม่อ่านค่าความลับ
4. จำนวน commit ที่ยังไม่มีบน Git ระยะไกล
5. URL Git ระยะไกลของเจ้าของ ไม่ยึดชื่อ alias อย่างเดียว
6. process, service, port, container และฐานข้อมูลที่ยังใช้พื้นที่นั้น
7. ขนาดพื้นที่และสถานะ path ว่าปกติ เสีย หรือหาย
8. Chat/งาน/คนที่กำลังใช้ path ตามสมุดทะเบียนและ process จริง

ผลต้องจัดเป็น `PRESERVE`, `RECOVER`, `REVIEW`, `CLEANUP_PROPOSED` ห้ามข้ามไปลบ

## 3. ด่านรักษาประวัติ

ถ้าพบ commit ที่ไม่มีบน Git ระยะไกล ให้เสนอ branch ช่วยชีวิตรูปแบบ:

```text
rescue/<staff-id>/<incident-id>-<slug>
```

ต้องระบุ branch, SHA, URL ปลายทาง, คำสั่ง, ผลกระทบ และวิธีย้อนกลับ เจ้าของต้องอนุมัติชื่อ branch และการส่งขึ้น Git ก่อนลงมือ ไฟล์ที่ยังไม่ commit ไม่ถูกรวมอยู่ในการส่ง branch

## 4. ด่านลบ 6/6

Worktree หนึ่งตำแหน่งจะเข้า `CLEANUP_PROPOSED` ได้เมื่อผ่านครบ:

1. `clean_or_archived` — ไม่มีไฟล์ค้าง หรือมีแฟ้มหลักฐานที่เจ้าของยืนยัน
2. `pushed_or_archived` — ไม่มี commit ค้าง หรือเก็บสำเนากู้คืนแล้ว
3. `no_writer_or_runtime` — ไม่มีสิทธิ์เขียน process service port container หรือฐานข้อมูลใช้พื้นที่
4. `merged_or_owner_abandoned` — branch รวมแล้ว หรือเจ้าของยืนยันเลิกงาน
5. `recovery_evidence` — มี URL, branch และ SHA ที่กู้กลับได้
6. `dry_run_recorded` — รายงานจำลองแสดง path ขนาด branch เหตุผล และผลกระทบ

ผ่านไม่ครบ 6/6 ให้รายงานจำนวนจริง เช่น 4/6 และห้ามเรียกว่า “พร้อมลบ”

## 5. การกักพักและเอาออก

```text
CLEANUP_PROPOSED
→ เจ้าของอนุมัติเป้าหมาย
→ QUARANTINED อย่างน้อย 72 ชั่วโมง
→ ตรวจ 6/6 ซ้ำ
→ Worktree Manager เอาพื้นที่ออก
→ ตรวจ Worktree อื่นใน repository เดียวกัน
→ ARCHIVED
```

ข้อห้าม:

- ห้าม `rm -rf`
- ห้าม `git worktree prune` แบบกว้างโดยไม่แสดงรายการ
- ห้ามลบ local branch หรือ remote branch พร้อม Worktree ในคำสั่งเดียว
- ห้ามลบ Worktree ที่ process ใช้อยู่ แม้ Git จะรายงานว่า clean
- ห้ามใช้ “เก่า”, “ชื่อแปลก” หรือ “น่าจะรวมแล้ว” เป็นหลักฐาน

## 6. หลักฐานปิดด่าน

รายงานปิดต้องมี:

```yaml
project_id: <project>
repository_url: <owner-url>
git_common_dir: <path>
worktree_path: <path>
branch: <branch-or-detached>
sha_before: <sha>
sha_after: <sha-or-null>
gates_passed: <N>/6
manager_result: <decision-token>
other_worktrees_rechecked: <N>/<M>
recovery_evidence:
  - <remote-url + branch + sha>
```

หากการเอาออกไม่เกิดขึ้น ให้ใช้ `WRK_GOV_CLEANUP_PROPOSED` หรือ `WRK_GOV_BLOCKED` เท่านั้น ห้ามใช้ `WRK_GOV_ARCHIVED`
