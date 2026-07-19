# Plan — SHORTCUT · ปิด Shortcut กลางรุ่น 2026.07.19

> memory-schema: v1.2 · **plan_id: SHORTCUT**
> lifecycle: active
> progress: 28/29 = 96.6%
> รุ่นส่งมอบ: `2026.07.19-5` สืบต่อจากงานรุ่น `2026.07.19-2` เพราะ `main` มีรุ่น `-4` อยู่ก่อนงานแก้ต้นเหตุ

## เป้าหมาย

ปิด Shortcut กลางให้ผ่านด่านรวมโค้ดจริง เข้า `main` ติดตั้งบน Mac และ VPS โดยไม่คัดลอกทั้ง Obsidian vault พร้อมกำจัดต้นเหตุที่ทำให้ AI พยายามสร้าง Worktree และทำให้ระบบแผนกลางอ่านได้เพียงแผนเดียวต่อไฟล์

## กติกาเหล็ก

1. ใช้ Git root และกิ่งที่เปิดอยู่เท่านั้น
2. AI ห้ามสร้าง สลับ ย้าย หรือลบ Worktree/กิ่งเอง
3. ห้ามลดเพดานด่านรวมโค้ดเพื่อให้ผ่าน
4. AI Relay ใช้ได้เมื่อเจ้าของสั่งตรงเท่านั้น
5. สถานะและเปอร์เซ็นต์ต้องอ้างหลักฐานจากเครื่อง, GitHub หรือไฟล์แผนที่ตรวจได้

## SHORTCUT-P1 — หาต้นเหตุ BLOCKED_DO_NOT_MERGE · 6/6 = 100%

- **SHORTCUT-P1-I1** ยืนยันว่ากิ่งเดิมถูกใช้ซ้ำหลัง squash merge 4 รอบ ทำให้ commit เก่าถูกนับซ้ำ
- **SHORTCUT-P1-I2** ยืนยันว่าด่านเดิมนับ `merge-base..HEAD` ดิบ จึงรวม merge/sync และงานที่เข้า main แบบ squash แล้ว
- **SHORTCUT-P1-I3** ยืนยันว่า Close Chat ก่อน rollout เพิ่มไฟล์ความจำ 4 ไฟล์ ทำให้ 27 ไฟล์กลายเป็น 31 เกินเพดาน 30
- **SHORTCUT-P1-I4** พบคำสั่งขัดนโยบายสร้าง Worktree โดยตรง 9 จุดใน Shortcut กลาง
- **SHORTCUT-P1-I5** พบตัวตรวจเดิมเห็นเพียง 18 ไฟล์และ 3 วลี จึงรายงานเขียวลวงทั้งที่ไฟล์อ้างอิงยังขัดกัน
- **SHORTCUT-P1-I6** พบ Hook เดิมไม่กันคำตอบว่า AI จะสร้าง Worktree และตัวติดตั้งทีมไม่ได้ติดตั้ง `save-git` จริง

## SHORTCUT-P2 — ซ่อมด่านและรวมชุดงานเดิม · 5/5 = 100%

- **SHORTCUT-P2-I1** ด่านหารอยต่อจาก PR ล่าสุดของกิ่งเดียวกัน และไม่นับ merge commit เป็นงานใหม่
- **SHORTCUT-P2-I2** ด่านคำนวณจำนวนไฟล์จากผลรวมเสมือนกับ `main` แทนผลต่างสะสมดิบ
- **SHORTCUT-P2-I3** รักษาเพดานเดิม 5 commit/30 ไฟล์ และเพิ่มชุดทดสอบกันปัญหาซ้ำ
- **SHORTCUT-P2-I4** ด่านจริงผ่าน 5/5 commit และ 29/30 ไฟล์; ชุดตรวจ 209/209 ผ่าน
- **SHORTCUT-P2-I5** PR #84 รวมแบบ merge commit เข้า `main` ที่ `36085b1f6bbfa32fc0ce2853c578599ccd2b3b16`

## SHORTCUT-P3 — แก้ต้นเหตุ Worktree ทุกทางที่โหลดจริง · 5/5 = 100%

- **SHORTCUT-P3-I1** แก้สัญญา Worktree, AI Pair, AI Relay, Viber Structure, Viber Audit, Save Git, Continue และ Close Chat ให้ยึดพื้นที่ปัจจุบัน
- **SHORTCUT-P3-I2** แก้ Skill ที่โหลดอัตโนมัติของ Codex, Claude, OpenCode และคนทำงาน Kanban ไม่ให้สร้าง Worktree
- **SHORTCUT-P3-I3** ตัวตรวจครอบ 57 ไฟล์อ้างอิง, 92 ไฟล์นโยบายใน repo และความตรงกัน 59 ไฟล์; คำสั่งสร้างอัตโนมัติ 0/33
- **SHORTCUT-P3-I4** Hook บล็อกแผนตอบว่าจะสร้าง Worktree และคำสั่งที่คัดลอกไปรันได้
- **SHORTCUT-P3-I5** ตัวติดตั้งทีมติดตั้ง `save-git` จริง; PR #85 รวมเข้า `main` ที่ `026f69682d79d2065a981dd72ddf4c90faff739f`

## SHORTCUT-P4 — ติดตั้งและตรวจ Mac · 4/4 = 100%

- **SHORTCUT-P4-I1** ติดตั้งรุ่น `2026.07.19-5` สำเร็จ
- **SHORTCUT-P4-I2** Shortcut 33/33, Hook 6/6 และ MW 7/7 ผ่าน
- **SHORTCUT-P4-I3** workspace response 4/4 และ phase autonomy 4/4 ผ่าน
- **SHORTCUT-P4-I4** current workspace prewrite 23/23 ผ่าน

## SHORTCUT-P5 — ติดตั้งและตรวจ VPS · 4/4 = 100%

- **SHORTCUT-P5-I1** ตรวจเส้นทางตาม staff id + project แล้วพบทะเบียนเส้นทาง VPS ขาดจริง จึงไม่ใช้ Worktree ของผู้อื่นแทน
- **SHORTCUT-P5-I2** ดาวน์โหลดเฉพาะ archive ของ `main` ไปโฟลเดอร์ชั่วคราวและลบเมื่อจบ
- **SHORTCUT-P5-I3** ติดตั้งเฉพาะ payload/Skill/เครื่องมือกลาง ไม่คัดลอกทั้ง vault และไม่ติดตั้ง AI Relay
- **SHORTCUT-P5-I4** VPS ผ่าน Shortcut 33/33, Hook 6/6, MW 7/7 และพบ `save-git`

## SHORTCUT-P6 — ซ่อมระบบแผนกลาง · 4/4 = 100%

- **SHORTCUT-P6-I1** แยก BRM/QAQC/MW/DSU/SPEC/UAG เป็นหนึ่ง `plan_id` ต่อหนึ่งไฟล์โดยรักษาเนื้อหาเดิม
- **SHORTCUT-P6-I2** สร้างดัชนีรวม WTL/GRD/JARVIS และกำหนด active เพียง SHORTCUT
- **SHORTCUT-P6-I3** เพิ่มด่านตรวจ active 1/1, plan_id ต่อไฟล์ และพาธที่ลงทะเบียน
- **SHORTCUT-P6-I4** อัปเปอร์เซ็นต์ทั้ง 10 แผนจากหลักฐานล่าสุด

## SHORTCUT-P7 — กระจายเครื่องทีมรายบุคคล · 0/1 = 0%

- **SHORTCUT-P7-I1** ติดตั้งและตรวจ notebook ของพนักงานแต่ละเครื่อง — `OWNER_INPUT_REQUIRED: TEAM_MACHINE_ACCESS` เพราะไม่มีรายชื่อ host/ช่องทาง SSH ที่เข้าถึงได้จากเครื่องนี้; ชุดติดตั้งบน `main` พร้อมใช้งานแล้ว

## เกณฑ์ปิดแผน

- งานกลาง, GitHub `main`, Mac และ VPS ปิดครบแล้ว
- ปิด 100% เมื่อมีหลักฐานติดตั้ง notebook ทีมตามรายการเครื่องจริง
- ระหว่างรอให้คงแผนนี้เป็น active เพียงชุดเดียว; ห้ามเปิด Worktree เพื่อแก้งานค้างนี้
