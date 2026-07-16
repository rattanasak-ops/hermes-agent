# Session Log — 2026-07-16 · ชุด Use Migrate 0-13 (แตก flow รายเฟส) + กระจายทุกเครื่อง

> staff: nat · แชท Fable · task: NCR-P0-I2 → MWTS-P0-I1 → CLS-20260716 · schema: memory-schema-v1.2

## เป้าหมายรอบนี้ (วิวัฒน์ตามคำสั่งเจ้าของ)
1. เปิด worktree มาตรฐาน + เก็บ 2 ไฟล์ dirty ค้างรอบปิด 15 ก.ค. → PR #49
2. วิเคราะห์ root cause "ทำไม AI ไม่ทำตาม Use Migrate Web" + สร้าง shortcut รายเฟส `Use Migrate 1..13` ที่จบเฟสด้วยตาราง comply + ถาม-ตอบบังคับ (เจ้าของอนุมัติ 13+1)
3. "ทำทุกอย่างให้พร้อมใช้" → ติดตั้ง+กระจายครบ Mac/VPS/ทีม

## ผลหลัก (verified เว้นแต่ระบุ)
- **Root cause 2 รอบ**: R1-R6 (อ่าน prompt จริง 661 บรรทัด) + R7-R11 (ตารางผลงานจริง: FW-P0 ข้ามทั้งด่าน · M5=5% hardcode · M6=10% รีวิวแทนด่าน) → ออกแบบ 6 กลไกแก้ ฝังในชุดใหม่
- **ชุดใหม่ในคลัง GitLab (`cc8a729`→`144b608`→`ef5b27d`)**: สัญญากลาง v1.1 + `use-migrate-0..13` v1.0 + `use-migrate-web` v1.4 + ทะเบียน — Grok ตรวจ (BLOCKING 6/6 แก้ครบ) + ทดสอบเจาะ AI สด 2/2 + โครง 70/70
- **กติกาโควตาเมนู** (เจ้าของอนุมัติ): ค่าเริ่มต้น 1 คน 1 เมนู · เกินได้เมื่อ owner จด `quota:` ใน menu-queue · เฟสโค้ด 8-9 ทีละเมนูต่อพื้นที่
- **กระจาย**: Mac = mw tools 7/7 (+รอดหลังลบต้นทาง) · VPS = shortcut 17/17 (rsync เฉพาะโฟลเดอร์กลาง — กระจก VPS เป็นพื้นที่ทีม ห้ามยกทั้งก้อน) · ทีม = PR #50 merged รอรัน installer
- **กู้ภัย VPS**: สมุด git แยกเล่ม + งาน rename `Use Save Git`→`Use Request Merge` (เซสชัน AI 28 มิ.ย. เจ้าของไม่รู้จัก) → กิ่ง `vps-rescue-2026-07-16` (ถึง `6500484`) · เจ้าของรับคำแนะนำ: ไม่รวม main
- **RSF ชุดพร้อมเคาะ FW-P0** (จาก TOR จริง): โหมด MIGRATE · FORM เปิด / BILINGUAL ปิด (grep = 0) · DATA/MINISITE เสนอไม่เปิด [assumption รอเคาะ] · งวด 1 ≤30 วัน 30% · งวด 2 ≤90 วัน 70% · ค่าปรับ 0.1%/วัน · W3C + WCAG 2.1 AA · OWASP Top10 + VA · ประกัน 1 ปี (ตอบ 1 ชม./เริ่มซ่อม 5 ชม./จบ 2 วันทำการ) · อบรม admin 6 ชม./5 คน + user 6 ชม./10 คน onsite · gap มาตรฐาน = DEC-155 ไม่ถามซ้ำ · เหลือเคาะ: แทร็ก + รายชื่อทีม
- **มาตรฐานเก็บไฟล์อัปโหลด (คำปรึกษา)**: โค้ดกลาง 1 ชุด config-only (`STORAGE_BASE_PATH`) · ก้อนไฟล์ = `uploads/{siteId}/{หมวด}/` นอก git · ชุดติดตั้งลูกค้า = โค้ดกลาง + ก้อน uploads/{siteId} + DB ของ site · mini-site = siteId ตัวเอง · โค้ดแก้ที่ Root Admin (แชทแยก) · RSF/DRA/CT ตามเก็บไฟล์เก่าตอนทำ — **ลำดับ: โค้ดกลางเสร็จก่อน ค่อยกวาดไฟล์เก่า**

### ใบสั่งงานแชท Root Admin (เจ้าของเอาไปวาง)
รวมทางอัปโหลดให้เหลือทางเดียว: ทุกโมดูลผ่าน StorageService → `uploads/{siteId}/{หมวด}/{timestamp-hash.ext}` · หลักฐานเดิม: ดีไซน์ถูกอยู่ที่ `storage.service.ts:79` + DB เก็บ path · แต่ของจริง `uploads/roadsafefund/*.png` วางแบน = มีทางเก่า (โมดูล media) · งาน: บัญชีทุกทางอัปโหลด → บังคับผ่านตัวเดียว → สคริปต์กลางย้ายไฟล์เก่า+อัป path (สำรอง+เทียบจำนวน ห้ามลบต้นทาง) → เทสต์กันถอยหลัง

## Changed-files table
| file | owner | changed_by | reason | verification | risk | next_owner |
|---|---|---|---|---|---|---|
| คลัง: `use-migrate-phase-contract` + `use-migrate-0..13` + `use-migrate-web` + registry (GitLab `ef5b27d`) | nat | Fable | ชุดรายเฟส + โควตาเมนู | verified (Grok 6/6 + เจาะ 2/2 + push แล้ว) | ต่ำ | ทีมใช้ |
| repo: `scripts/hermes_hook_doctor.py` + `hermes_write_permit.py` (PR #49 merged) | nat | Fable (ย้าย diff ค้าง) | เก็บของค้างรอบปิด 15 ก.ค. | verified (pytest 27 passed + byte-identical) | ต่ำ | — |
| repo: `team-shortcuts/payload/**` 23 ไฟล์ (PR #50 merged) | nat | สคริปต์ sync-from-vault | ชุดติดตั้งทีมรับ flow ใหม่ | verified (diff เทียบคลัง = 0) | ต่ำ | ทีมรัน installer |
| VPS: `ai-context/` + `skills/prompt-shortcuts/` (rsync) + สแนปช็อต commit `6500484` | nat | Fable | VPS ใช้ shortcut ครบ | verified (ssh นับ 17/17 + ไฟล์ทีม peter 8/8 ไม่ถูกแตะ) | ต่ำ | — |
| `.project/` memory 4 ไฟล์ (กิ่ง `task/nat/CLS-20260716-memory-close`) | nat | Fable | ความจำรอบนี้ | verified (check-ignore/ls-files ก่อน commit) | ต่ำ | เจ้าของ merge PR |

## Decision log
- แตกเฟส + กุญแจเจ้าของ = ทางแก้ root cause ที่เจ้าของเลือก (ตรงข้อสรุป AI 4 ตัวเรื่องบัตรอนุมัติต่อเฟส)
- `BLOCKED_TOOLING`: เฟสด่านเครื่อง (9/10/11/13) ไม่มีเครื่องมือ = จบเฟสไม่ได้ ไม่มีทางลัดภาพ+grep (กฎ R-3)
- โควตาเมนูต่อคน (ค่าเริ่มต้น 1 · owner อนุมัติเกินได้) + เฟสโค้ดทีละเมนูต่อพื้นที่
- กระจก VPS = พื้นที่ทีม → ซิงก์เฉพาะโฟลเดอร์กลาง · งานแปลกกู้ขึ้นกิ่ง rescue ก่อนเสมอ
- งาน rename `Use Request Merge` (28 มิ.ย.): ไม่รวม main — เก็บกิ่ง rescue
- มาตรฐานอัปโหลด: แก้ที่ Root Admin ครั้งเดียว · ห้ามแก้รายไซต์ · ตามเก็บข้อมูลเก่ารายโปรเจกต์

## Quality gate ที่รัน
- pytest scoped (PR #49): `test_hermes_write_permit` + `test_worktree_lifecycle` = **27 passed**
- โครงชุด shortcut: 5 ส่วน × 14 ไฟล์ = **70/70** (grep สด)
- `hermes-hook-doctor` = ok 4/4 (หลังติดตั้ง mw)
- mw-setup: 7/7 ผ่าน + regression ลบต้นทางรอด 7/7
- ชุดเทสต์เต็ม repo: ยังแดง 683 ที่ฐาน main (ของเดิม งานซ่อมแยกรอบ — ไม่ใช่ของรอบนี้)

## Deploy
- ไม่มี production deploy · PR #49/#50/#51 merged เข้า main (repo ไม่มี CI runs — `gh run list` ว่าง = N/A)

## งานค้าง + เจ้าของถัดไป
ดู `OverviewProgress.md` หัวข้อ "งานค้าง/ส่งต่อ · ใหม่ 2026-07-16" (ก-จ) — หลัก: เจ้าของเริ่ม RSF + แชท Root Admin · ตัดสินใจบรรจุข้อตรวจอัปโหลดเข้า `Use Migrate 0` · ช่องว่างเครื่องมือ WTL (close/cleanup + ธง over-limit ไม่มีจริง)

## ความเสี่ยงที่เหลือ
- ชุดรายเฟสยังไม่เคยเดินจริงครบ 13 เฟสกับเมนูจริง (ทดสอบแล้วเฉพาะด่านกันข้าม) — เมนูแรกของ RSF คือการพิสูจน์จริง
- worktree ค้าง 4 โฟลเดอร์ (2 merge แล้ว) รอเครื่องมือ cleanup — พื้นที่ยังไม่ตึง (ดิสก์ใช้ 7%)

## ข้อความเปิดแชทหน้า (ก๊อปวาง)
`Use New Chat` แล้วอ่าน `.project/OverviewProgress.md` (หัวข้อ 2026-07-16) + session log นี้ · งานแรกตามคิว: รอเจ้าของสั่งจาก "งานถัดไป" ข้อ 1
