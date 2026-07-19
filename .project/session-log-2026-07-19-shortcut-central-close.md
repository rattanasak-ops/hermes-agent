> memory-schema: v1.2

# Session Log — ปิด Shortcut กลางและซ่อมต้นเหตุ Worktree อัตโนมัติ

## เป้าหมายรอบนี้

ปิด Shortcut กลางรุ่น 2026.07.19 ให้ผ่านด่านจริง เข้า `main` กระจาย Mac/VPS/เครื่องทีมโดยไม่คัดลอกทั้ง vault และทำระบบแผนกลางให้สถานะตรงหลักฐาน

## ผลรวม

- ทำแล้ว 28/29 งานย่อย = 96.6%
- เหลือ 1/29 = notebook ทีมรายบุคคล เพราะไม่มีบัญชี host/ช่องทางเข้าถึงที่ผูก staff id
- รุ่นส่งมอบจริงคือ `2026.07.19-5`; เริ่มจาก `-2` แต่ `main` มี `-4` อยู่ก่อนชุดแก้ต้นเหตุ จึงขยับเลขเพื่อให้เครื่องรู้ว่าต้องอัปเดต

## Changed-files

| file/group | owner | changed_by | reason | verification | risk | next_owner |
|---|---|---|---|---|---|---|
| `skills/prompt-shortcuts/**`, registry และ payload | Shortcut กลาง | Codex | ตัดคำสั่งสร้าง Worktree และยึดพื้นที่ปัจจุบัน | checker 33/33; refs 57; parity 59 | ต่ำ | main |
| Skill Codex/Claude/OpenCode/Kanban | Hermes skills | Codex | ปิดทางสร้าง Worktree จาก Skill ที่โหลดอัตโนมัติ | repo policy scan 92 ไฟล์; auto-create 0/33 | ต่ำ | main |
| `save_git_gate.py` 2 สำเนา | Git gate | Codex | ไม่นับงานเก่าซ้ำหลัง squash/reuse branch | gate tests 4/4; mirror ตรง | กลาง | main |
| Hook/installer/team checks | Team runtime | Codex | กันคำตอบว่าจะสร้าง Worktree และติดตั้ง `save-git` จริง | focused suite 57/57; Mac/VPS check PASS | กลาง | team rollout |
| `.project/plan*`, `.project/plans/**` | Project memory | Codex | หนึ่ง plan_id ต่อไฟล์ + active 1/1 | memory-audit 5/5; plan tests 23/23 | ต่ำ | owner/team access |
| `scripts/memory-audit/**` | Memory gate | Codex | บังคับดัชนี แผน active เดียว และไฟล์ตรงรหัส | tests 12/12 ในชุดรวม 23/23 | ต่ำ | main |

## ต้นเหตุที่พิสูจน์แล้ว

1. กิ่งเดียวถูกนำกลับมาใช้หลัง squash merge 4 รอบ ทำให้ commit เก่าอยู่นอก ancestry ของ `main` และถูกนับซ้ำ
2. ด่านเดิมนับ `merge-base..HEAD` ดิบ ไม่แยก sync merge/งานที่รวมแล้ว และวัดไฟล์สะสมแทนผลหลังรวมจริง
3. Close Chat ถูกเรียกก่อน main/VPS/team เสร็จ เพิ่มไฟล์ความจำ 4 ไฟล์จน 27 กลายเป็น 31 เกินเพดาน 30
4. Shortcut กลางมีข้อความขัดกัน 9 จุด และ Skill ที่โหลดจริงอีกหลายไฟล์สั่งให้ AI เปิด Worktree
5. ตัวตรวจเดิมอ่านเพียง 18 ไฟล์กับ 3 วลี จึงรายงาน 33/33 แบบเขียวลวง
6. Hook เดิมกันเฉพาะการโยนการกู้พื้นที่ให้เจ้าของ แต่ไม่กัน AI พูดว่าจะสร้าง Worktree; ตัวติดตั้งทีมไม่ติดตั้งตัวรัน `save-git`

## Decision log

- คงเพดาน 5 commit/30 ไฟล์ ไม่ลดเพื่อให้ผ่าน
- ใช้ checkpoint จาก head SHA ของ PR ล่าสุดบนกิ่งเดิม และวัดไฟล์จากผลรวมเสมือนกับ `main`
- กิ่งที่นำกลับมาใช้ต้องรวมแบบ merge commit ไม่ใช้ squash
- AI อ่านสถานะ Worktree ได้ แต่การสร้าง/สลับ/ย้าย/ลบต้องมาจากคำสั่งตรงของเจ้าของหรือผู้จัดการพื้นที่
- แผนกลางมี active เพียงหนึ่งชุด; แผนเก่าเป็น parked/closed/historical ตามหลักฐาน
- VPS ติดตั้งจาก archive ของ GitHub `main` ในโฟลเดอร์ชั่วคราว เพราะ route `nat + hermes-agent` ขาด; ไม่ใช้พื้นที่ของผู้อื่นแทน

## Git และ Pull Request

| PR | ขอบเขต | ผล | merge SHA |
|---|---|---|---|
| #84 | ซ่อมด่านและชุด Shortcut เดิม | merged แบบ merge commit | `36085b1f6bbfa32fc0ce2853c578599ccd2b3b16` |
| #85 | แก้ต้นเหตุทุก Shortcut/Skill/Hook/installer | merged แบบ merge commit | `026f69682d79d2065a981dd72ddf4c90faff739f` |
| #86 | แยกแผนกลางและเพิ่มด่านตรวจ | merged แบบ merge commit | `165fdfcf2389748c6b321bab5d0e0ea65d710a55` |

ด่าน PR #86 ผ่าน 1/5 commit, 16/30 ไฟล์, ไม่ชน `main`, คำตัดสิน `SAFE_TO_MERGE`

## Quality Gate

- Shortcut/Hook/installer focused suite: 57/57 ผ่าน
- Scoped suite ก่อน PR #84: 209/209 ผ่าน
- Memory audit + plan anchor: 23/23 ผ่าน
- memory-audit ของ repo: schema/index/SHA/Git/เลขงาน 5/5 ผ่าน
- Ruff: ผ่าน
- `git diff --check`: ผ่าน
- Shortcut visibility: 33/33; direct integrations 18/18; reference files 57; repo policy files 92; parity files 59; auto-create 0/33

## Deploy / Rollout

- Mac: รุ่น `2026.07.19-5`; Prompt Shortcut 33/33; Hook 6/6; MW 7/7; workspace 4/4; phase autonomy 4/4; current workspace 23/23
- VPS `linux-nat`: รุ่น `2026.07.19-5`; Prompt Shortcut 33/33; Hook 6/6; MW 7/7; workspace 4/4; phase autonomy 4/4; current workspace 23/23; พบ `save-git`
- ไม่คัดลอกทั้ง Obsidian vault และไม่ติดตั้ง AI Relay
- Dashboard/service/health URL เป็น N/A เพราะรอบนี้แจกเครื่องมือ Shortcut ไม่ได้เปลี่ยนบริการเว็บ

## งานค้างและความเสี่ยง

- `SHORTCUT-P7-I1` notebook ทีม 0/1 งานรวม: ยังไม่มีบัญชีเครื่องที่ผูก staff id และช่องทาง SSH
- VPS route registry ของ `nat + hermes-agent` ยังขาด แม้การแจก Shortcut จาก archive สำเร็จ
- แผน parked อื่นยังมีงานตามเปอร์เซ็นต์ใน `plan-index.md`; ห้ามเริ่มพร้อมกันหรือทำให้ active มากกว่าหนึ่งแผน
- ชุดทดสอบทั้ง repository ไม่ได้ใช้เป็นด่านรอบนี้ เพราะฐานเดิมมีความล้มเหลวจำนวนมาก; หลักฐานที่อ้างเป็นชุดเจาะขอบเขตจริง

## Business Plan / QA-QC / Spec

- Business Plan: รอบนี้ไม่มีการเปลี่ยนด้านธุรกิจ
- QA/QC: ไม่มี `.project/qaqc-scan.md` จึง N/A
- Spec: ไม่มี `.project/spec/SHORTCUT.md` จึง N/A

## ขั้นตอนถัดไป

เจ้าของให้บัญชี notebook ทีมที่เข้าถึงได้พร้อม staff id แล้ว AI รันตัวติดตั้งจาก `main` ตรวจ 33/33 ต่อเครื่อง และอัป SHORTCUT เป็น 29/29 โดยใช้พื้นที่เดิม

## ข้อความเปิดงานครั้งถัดไป

```text
Use New Chat
Use Continue

ทำต่อจาก .project/session-log-2026-07-19-shortcut-central-close.md
งานเดียว: SHORTCUT-P7-I1 ติดตั้ง Prompt Shortcut รุ่น 2026.07.19-5 บน notebook ทีมตามบัญชีเครื่องจริง

กติกา:
- ใช้พื้นที่และกิ่งปัจจุบันเท่านั้น ห้ามสร้าง/สลับ Worktree หรือกิ่ง
- ผูก staff id + project กับเครื่องจริงก่อนติดตั้ง ห้ามเดา host
- ติดตั้งเฉพาะ payload/Skill/เครื่องมือกลาง ห้ามคัดลอกทั้ง Obsidian vault
- ตรวจ 33/33 + Hook 6/6 + current workspace 23/23 แยกต่อเครื่อง
```

## Evidence footer

- timestamp: 2026-07-19 Asia/Bangkok
- host: `Rattanasaks-MacBook-Pro.local`
- cwd: `/Users/rattanasak/Documents/Worktrees/hermes-agent/nat/SHORTCUT-P1-I1-team-rollout-hardening-team-rollout-hardening`
- branch: `task/nat/SHORTCUT-P1-I1-team-rollout-hardening-team-rollout-hardening`
- commands: save-git gate, gh PR create/view/merge, pytest scoped, ruff, memory-audit, check-shortcuts, hermes-hook-doctor, SSH linux-nat check
