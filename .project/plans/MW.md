# Plan — MW · Shortcut "Use Migrate Web" (เริ่ม 2026-07-14 · เจ้าของสั่งเดินในแชท Fable + Codex ตรวจคู่)

> lifecycle: closed
> progress: 20/20 = 100%
> หลักฐานล่าสุด: P1-P6 ปิดครบ; งานต่อเป็นการใช้รายโปรเจกต์ ไม่ใช่งานสร้าง Shortcut กลาง


> memory-schema: v1.2 · **plan_id: MW** · จาก Use Act-As v3.1 (รีวิวเบื้องต้นส่งแล้ว 2026-07-14 · เจ้าของตอบ 3 คำถาม + ส่งไฟล์ที่ 1 + สั่งเดิน)
> ทีม: **Fable 5 = สมองคิด/วิเคราะห์/ออกแบบ (เจ้าของสั่งตรง)** · **Codex = ผู้ตรวจคู่ทุกใบ (relay-call --role review)** · Grok = สำรองถ้า Codex เสีย (รายงานการสลับเสมอ) · เจ้าของ = ตัดสินทุก checkpoint
> branch: `control_webengine_flow` (เจ้าของเปิดให้ 2026-07-14) · งานหลายเฟส = **1 PR เดียว**
> ขอบเขต: Shortcut ใช้กับ**ทุกโปรเจกต์ที่สร้างจาก Root Admin** (เริ่มจริงที่ RoadSafeFund) · ทีม ~10 คน pull จาก dev กลาง VPS ทำบนเครื่องตัวเอง + บางคน worktree บน VPS

## กติกาเหล็กของแผนนี้ (สืบทอด GRD/QAQC ครบ + เพิ่มของเจ้าของ)

1. เลขงานขึ้นต้น `MW-` และต้องมีจริงในไฟล์นี้ · เลขที่ไม่มี = ห้ามทำ
2. **ห้ามข้าม Flow · ห้ามตัดทอนข้อมูลเจ้าของ** — ทุกไฟล์ที่วิเคราะห์ต้องมีบัญชีนับ N/M · จะตัด/จัดลำดับใหม่ต้องเสนอเจ้าของตัดสินรายข้อ
3. ทุกใบวิเคราะห์/ออกแบบต้องผ่าน Codex ตรวจก่อนสรุปให้เจ้าของ (AI Relay โหมด 2)
4. verified = แถว gate-run เท่านั้น · งานเอกสาร = manual_verified + เจ้าของยืนยัน
5. จบแต่ละเฟส: ตาราง compile % ต่อหัวข้อ + ตารางว้าว (ดีขึ้นจากเดิมกี่ % วัดด้วยอะไร)
6. ห้ามแตะ: `.hermes/**` · `.env*`/secret · repo NewWebEngine2026 = **อ่านอย่างเดียว** (งานเขียนอยู่ Hermes Agent เท่านั้น)

## MW-P1 — วิเคราะห์ไฟล์เจ้าของทีละไฟล์ · สถานะ: I1-I3 เสร็จ (I2,I3 เจ้าของอนุมัติแล้ว · I1 มี 11 จุดเคาะค้าง) · รอไฟล์ชุดถัดไปหรือคำสั่งเข้า P2

### ผลสะสม (2026-07-14 · ทุกใบผ่านผู้ตรวจต่างค่าย Codex ผ่าน cross-check MCP เพราะ relay review mode มีบั๊ก)
- **I1 FLOW-13Steps-v2.docx.md** (439 บรรทัด อ่านครบ): ของใหม่เจ้าของแทรก **23 ข้อ** + 2 ข้อความต้องเก็บคำเดิม (ชุดคำถาม M0 บรรทัด 25 + hardcode บรรทัด 249) · **11 จุดเคาะรอเจ้าของตอบรายข้อ** (เด่น: DEC-167 เลขชนกันจริงกับ decisions.md · .work vs .project/ · เลขลิสต์แม่ห้ามพิมพ์มือ—เครื่องนับจริง=81 · Sitemap 2 docx → เสนอ "บัตรประจำเมนู 1 md/เมนู") · repo ต้นทางถูกแชทอื่นแก้สด (FLOW-JOURNEY-13STEP.md หายจาก .project/ แล้ว · checklist 74→81)
- **I2 Workshop Comment (PDF 15 หน้า + md)**: ปัญหา 28 ข้อจากทีม 5 คน → Flow ครอบ ✅7 🟡21 ❌0 · **เจ้าของอนุมัติ 4 ข้อเสนอ**: DS pattern กลาง 13 ตัว · ทุก pattern มี 6 ช่องบังคับ (หน้าตา/พฤติกรรม/ข้อมูล/สถานะผิดปกติ/การเข้าถึง/หลักฐานทดสอบ) · checklist ใหม่ ~10 ข้อ · แตก 28 กลุ่ม→~40 ข้อย่อยตอนทำบัญชี N/M
- **I3 TOR 3 โปรเจกต์** (CTH 58 REQ สร้างใหม่+catalog 2 ภาษา / DRA 92 REQ เสร็จ 88% + 7 minisite + OIT O1-O43 + TWCAG 2022 / RSF migrate + GOV-GAP 9 จุด): **เจ้าของอนุมัติ 12 ข้อเพิ่ม Flow + 8 ตัวกันเสี่ยง** — เด่น: โหมดหลัก+แทร็กเสริม (MIGRATE/REMEDIATE/BUILD + DATA/FORM/MINISITE/BILINGUAL) · RTM 3 ชั้น (มีข้อกำหนด→มีเทสต์→รันผ่านจริง) · Light Loop หน้าโครงซ้ำแบบกันข้ามขั้น · บัญชีคิวเมนู+ล็อก site/module ทีม 10 คน · เลเยอร์ปิดงวดราชการ · ผูก Use QA QC
- **บั๊ก infra พบระหว่างงาน (คิวซ่อมแยก · อย่าลืม)**: relay-call role review ยัด flag เก่า (--permission-mode/--no-subagents) ใส่ grok 1.0.1 → crash 1 วิ ทุกครั้ง · อยู่ทั้งตัวติดตั้ง ~/.hermes/ai-relay-tools และ repo main (`prepare_adapter_for_role`) · Codex ผ่าน portal ก็พังบนเครื่องนี้ · ทางเลี่ยงที่ใช้: cross-check MCP ask_gpt5

- **MW-P1-I4 เสร็จ**: ค้นคลัง Obsidian (60-Design 234 ไฟล์/42 module · QAQC Q01-Q16 178 หัวข้อ · playbooks) + 4 ข้อเสนอ ก-ง ผ่าน Codex · ข้อค้นพบ: VPS มี vault sync แล้ว (auto-push-vault.sh ทุก 3 นาที → GitLab + linux-nat:~/knowledge/hermes-agent-vault/) · ไฟล์ tracked อ่อนไหว 2 ตัวตรวจแล้ว 0 token จริง · ก่อนเปิดคลังให้ทีม clone ต้องตรวจประวัติ GitLab
- **MW-P1-I5 เสร็จ (เจ้าของแก้ข้อมูล)**: source ภาพจริง 4 ตัว = **Freepik + Recraft + Topaz + Magnific (magnific.com/user/api-keys = ต่อ API)** — ไม่มี "Opus" · เพิ่ม Image Source Registry (config-driven) + Benchmark Intake Gate (ห้าม copy 100% · วิเคราะห์แตกส่วน · ถามโจทย์ · แปลงเข้า DS)
- **MW-P1-I9 เสร็จ + เจ้าของเคาะ 2026-07-14: "ตามเสนอทั้งหมด ทำเลย"** — จุดเคาะ 13 จุดอนุมัติครบตามข้อเสนอ (1 ออกเลข DEC ใหม่กฎภาพ · 2 hardcode=ข้อยกเว้นอนุมัติรายกรณี · 3 เลขเครื่องนับสด · 4 Module แจ้งไฟล์เสียที่ Root Admin+ทดสอบรายเมนู · 5 ES ด่านโปรเจกต์+รายเมนู search · 6 .work=งานลูกค้า+deliverables · .project=ความจำ AI · ทั้งคู่เข้า git · 7 Pagination เข้า checklist · 8 ภาพคั่น/วิดีโอใต้เพดาน+reduced-motion · 9 แท็บลัดผูก WCAG+SEO · 10 GV: RSF ไม่ถามซ้ำ · 11 ตรวจเครื่องมือภาพจริงก่อนใช้ · 12 Light Loop เครื่อง 100% + คนสุ่มหน้าแรกทุกแบบ+20%/กลุ่ม · 13 รับข้อเสนอ I4 ทั้ง 4) · บัญชีรวมเข้า spec = 55 กลุ่มรายการ (I1:23+2 · I2:4 · I3:12+8 · I4:4 · I5:2)
- **MW-P1-I9** สรุปรวมทุกชุด: บัญชีความต้องการรวม + ตารางจุดเคาะรวม (รวม 11 จุดค้างของ I1)

- **MW-P1-I1** ไฟล์ 1 `FLOW-13Steps-v2.docx.md` (439 บรรทัด): บัญชี delta ที่เจ้าของแทรกเพิ่มจากไฟล์ repo + จุดขัด/ทับซ้อน + ตอบคำถามรวม/แยกไฟล์ Sitemap → Codex ตรวจ → เสนอเจ้าของตัดสิน
- **MW-P1-I2..I5** เสร็จครบ (I2 Workshop · I3 TOR · I4 คลัง Obsidian · I5 เจ้าของสั่งเพิ่ม — ดูผลสะสมด้านบน)
- **MW-P1-I9** เสร็จ — เจ้าของเคาะ 13 จุด อนุมัติทั้งหมด 2026-07-14 · **จุดเคาะ 11 ข้อของ I1 ถูกรวมและปิดในตาราง 13 จุดแล้ว (ไม่มีค้าง)**
- verify: บัญชี N/M ทุกไฟล์ + Codex verdict ทุกใบ + เจ้าของอนุมัติบัญชีรวม

## MW-P2 — ออกแบบ spec Shortcut · สถานะ: กำลังทำ · draft = `.project/mw-spec-draft.md`

- **MW-P2-I1** ร่าง spec v1.0 + Codex ตรวจรอบ 1 → FIX 8 จุด (ตารางแม่/I1 หาย 5/ขัดแย้ง 6/เครื่องมือ) — เสร็จ 2026-07-14
- **MW-P2-I2 เสร็จ 2026-07-14**: v1.1 → Codex รอบ 2 = FIX 3 เรื่อง (ครบ 2 รอบผู้ตรวจเดิม) → **เปลี่ยนวิธีตรวจเป็นเครื่องตามกติกา v2.16**: แก้ v1.2 (baseline sha256 จริง 3 ไฟล์ใน `.project/mw-flow-baseline.md` · [G] ทุกแถวผูก §10-1..10-10 · โปรโตคอลล็อกกลาง 6 ข้อ · สัญญารับมอบ P3 3 ข้อ §13) + สร้าง `scripts/mw-spec-check.py` (5 ด่าน) → **รันจริง PASS: ตารางแม่ 55/55 · [G] ครบ · § ครบ · จุดเคาะ 13/13 · baseline ตรง** (เครื่องจับ 21 จุดหลวมก่อนผ่าน — พิสูจน์ว่าด่านทำงาน)
- **MW-P2-I3 เสร็จ: เจ้าของอนุมัติ spec 2026-07-14 ("อนุมัติ spec") → P2 ปิด 3/3**

- โครง 2 ชั้น (แกน Flow กลาง ↔ Project Profile ต่อเว็บ) · ด่านกันข้าม/กันโกหก (ยก G5+menu-gate) · Write Permit ต่อเมนูกันทีมชนกัน · บทบาท AI capability-based · ตาราง compile+ว้าวต่อเฟส · การเรียกใช้ VPS+notebook
- verify: Codex ตรวจ spec + เจ้าของอนุมัติก่อนเขียนไฟล์จริง

## MW-P3 — เขียนไฟล์จริง · สถานะ: **เสร็จ 2026-07-14 · merged main (PR #35+#36)** — I1 prompt ✅ · I2 เครื่องมือ **7/7** ✅ (Grok เขียน · GPT-5 ตรวจ · mw suite 252) · I3 test-id map + §13.1 COMPLETE 32/32 ✅ · I4 สัญญา §13 ครบ 3/3 ✅

- **MW-P3-I1 เสร็จ 2026-07-14**: prompt `use-migrate-web.md` v1.0 + `use-migrate-web-flow13.md` (เนื้อต้นฉบับ 439 บรรทัดตรง 100% · embedded_sha256 คุมช่วง 31-469 verify ตรง · ตาราง delta 25 + กฎลำดับความสำคัญ + ตารางจับคู่พาธเก่า→ใหม่) + แถวทะเบียน payload registry · **Codex ตรวจ 2 รอบ**: รอบ 1 FIX 6 กลุ่ม→แก้ครบ · รอบ 2 ผ่าน 4/6 เหลือ 2 บรรทัด (รอยจาก shell กลืน backtick)→แก้+verify ด้วย grep/shasum เขียวครบ · บทเรียนจดแล้ว: heredoc ต้อง quote + replace ต้องมี assert
- **MW-P3-I2 — แผนส่งมอบ (Fable เขียน 2026-07-14 · เจ้าของสลับกลับ Opus ทำต่อตามกติกา relay v2.16)**
  - **บทบาทรอบใหม่:** Opus = สมองคุมสายพาน (วางแผน/เลือก coder/เขียน brief/ตรวจ/ตัดสิน) · coder = Codex หรือ Grok (เลือกตาม catalog §7 ต่อชนิดงาน) · reviewer = คนละค่ายกับ coder เสมอ · verified = gate-run เท่านั้น
  - **งาน = เครื่องมือ 7 ตัว · 1 ตัว = 1 issue** (สเปคเต็มอยู่ SPEC §10 + ตาราง [เครื่องมือประกอบ] ใน use-migrate-web.md):
    - MW-P3-I2d `work-locks` ล็อกกลางจองเมนูข้ามเครื่อง (ทำก่อน — ปลดล็อกทีม) · เกณฑ์รับมอบ: จำลอง 2 clone จองพร้อมกัน สำเร็จ 1/2 (ผลรันแนบ)
    - MW-P3-I2a `mw-menu-gate` เครื่องตัดสินปิดเมนู portable (checklist กลาง + .work config · เลขนับสด · exit 0/1) — หลักการจากต้นแบบ menu-gate.mjs ของ NewWebEngine แต่**ห้ามแตะ repo นั้น** (อ่านอย่างเดียว)
    - MW-P3-I2b `mw-page-check` ตรวจหน้า (soft-404 ใน rendered main content · ลิงก์ · ภาษา · เพดานไฟล์ hero≤300KB/content≤150KB/vdo≤2MB · pagination · sticky ไม่บัง · related logic · วิดีโอ attr autoplay/muted/reduced-motion) config ต่อโปรเจกต์
    - MW-P3-I2f `mw-doctor` ตรวจติดตั้ง notebook/VPS + smoke call เครื่องมือภาพ 4 source (Freepik/Recraft/Topaz/Magnific — 1 งานเล็กจริง) + ยิง relay จริง 1 ครั้ง
    - MW-P3-I2c `mw-rtm-report` นับ RTM 3 ชั้น (req-register → test cases → ผลรันจริง)
    - MW-P3-I2g `mw-wow-report` รวมตัวเลขเครื่อง before/after (LH/axe/gate N-M/RTM%/ขนาดไฟล์) — AI ห้ามกรอกเอง
    - MW-P3-I2e `mw-backend-check` (ใหญ่สุด — วงจรฟอร์ม/แจ้งไฟล์เสีย/siteId/dashboard ต้องมี engine จริง) → เสนอทำคู่ P4 บน RoadSafeFund
  - **ที่วางโค้ด:** `scripts/mw/` ใน repo นี้ + เทสต์ `tests/scripts/mw/` · ทุกตัวมี pytest + gate-run pass + reviewer ต่างค่าย
  - **ข้อจำกัดเครื่องนี้ที่ Opus ต้องรู้ (พิสูจน์แล้ววันนี้):** (1) relay-call role **review** พัง 2 ชั้น — portal crash + ยัด flag เก่าใส่ grok 1.0.1 → **ใช้ role code ผ่าน `AI_RELAY_ALLOW_LOCAL_CLI=1` ได้ · งานรีวิวใช้ cross-check MCP `ask_gpt5`** (2) plan-anchor อ่าน plan_id แรกของไฟล์ (QAQC) → เลขงาน MW ใช้ `--no-plan` ไปก่อน หรือขอเจ้าของสลับไฟล์แผน (3) Codex CLI ตรงใช้ได้ (ทดสอบ PONG แล้ว) (4) `hermes-write-permit` มีบนเครื่อง (5) ผู้ตรวจเดิม+วิธีเดิมได้ 2 รอบ — รอบ 3 ต้องเปลี่ยนเป็นเครื่องตรวจ (แบบที่ทำกับ mw-spec-check สำเร็จแล้ว)
  - **ก่อนปิด P3 ทั้งก้อน:** สัญญา §13 ครบ 3 ข้อ — ตาราง test ID ทุกแถว [G] (P3-I3) + จำลอง 2 clone + mw-spec-check PASS
- **MW-P3-I3** ผูก installer + ตาราง test ID ทุก [G] (สัญญา §13 ข้อ 1)
- **MW-P3-I4** รันสัญญา §13 ครบ 3 ข้อ → ส่งเจ้าของ
- verify: mw-spec-check PASS + Codex ตรวจ + ด่าน git + สัญญา §13

## MW-P4 — ทดสอบจริงบน RoadSafeFund + ติดตั้ง 2 ทาง (VPS/notebook) · สถานะ: **จบ 2026-07-15 — backend-check รันจริงกับ RSF site 78 (อ่าน 3/3 PASS + negative 2/2 FAIL ถูกต้อง) + วงจรฟอร์มจริง submit→DB PASS (POST /api/v1/contact · ข้อมูล TEST-MW ลบเกลี้ยง เหลือ 0) · เหลืองานเจ้าของ: กดชุดทดสอบรับงาน team-shortcuts/OWNER-ACCEPTANCE-MW.md**

- verify: เดิน flow จริงอย่างน้อย 1 เมนู หลักฐาน tier 3+ + เจ้าของเห็นของจริง

## MW-P5 — ปิดงาน: 1 PR + อัปความจำ · สถานะ: **PR merged แล้ว (2 PR) · อัป OverviewProgress+plan รอบนี้ · เหลือ Use Close Chat formalize + decisions**

## MW-P6 — Flow Enforcement: บังคับ 13 ขั้นด้วยเครื่อง (เริ่ม 2026-07-15 · เจ้าของสั่ง "แก้ต้นเหตุ AI ข้าม flow" หลังเหตุการณ์จริง 2026-07-15) · สถานะ: **I1-I4 เสร็จ 2026-07-15 (เทสต์ mw 291 เขียว + demo block จริง 4 ฉาก) · เหลือ: เจ้าของรัน installer ติด hook เครื่องจริง + push/PR**  · branch `feature/mw-flow-gate`

> ปฐมเหตุ: AI ข้าม flow ทั้งที่เอกสารครบ — ตรวจแล้ว G5 มีโค้ดจริงแค่ menu-gate (ปลายทาง M8) · "ด่านก่อนเขียน" ไม่มีไฟล์ · ไม่มีสถานะต่อเมนู · Fable วิเคราะห์ + Codex ตรวจค้าน 2026-07-15 (ผลใน xc-flow-gate.md)
> หลักออกแบบ (Codex เสริม): สถานะคำนวณสดจากหลักฐานจริง ไม่เก็บไฟล์ state ให้ปลอม · กติกากลางไฟล์เดียว evaluator เดียว · ตรวจเนื้อไฟล์ไม่ใช่แค่มีไฟล์ · คำถาม owner คง 4 checkpoint เดิม ไม่เพิ่ม

- **MW-P6-I1** กติกากลาง `scripts/mw/flow-rules.yaml` (13 ขั้น: ไฟล์ output ต่อขั้น + เกณฑ์เนื้อขั้นต่ำ + confirm checkpoint) + evaluator `scripts/mw/flow_eval.py` (คำนวณขั้นปัจจุบันจากหลักฐานบนดิสก์ · fail-closed)
- **MW-P6-I2** CLI `scripts/mw/flow_gate.py` — `status <menu>` / `can-enter <step> <menu>` (exit 0/1) / `--json` · ใช้ evaluator I1
- **MW-P6-I3** hook ด่านก่อนเขียน `team-shortcuts/hooks/enforce-flow-gate.py` (PreToolUse: โปรเจกต์มี `.work/profile.yaml` → Edit/Write/shell-write ไฟล์งานเมนูต้องผ่าน can-enter + มีล็อกเมนู) + เสียบ `install-team-hooks.py`
- **MW-P6-I4** ผูกเครื่องเดิม: menu-gate เพิ่มแถวเรียก evaluator เดียวกัน + mw-doctor เช็ค hook ติดตั้ง
- **MW-P6-I5** negative tests (ข้ามขั้น/ไฟล์เปล่า/ปลอมหลักฐาน → block ทุกเคส) + live demo ให้เจ้าของเห็น block บนจอ
- verify: pytest scoped เขียว + negative ครบ + demo เจ้าของ (tier 4-5) · ผู้เขียน Codex/Grok · ผู้ตรวจต่างค่าย · verified = แถว gate-run

## งานคน (เจ้าของ)

- ส่งไฟล์ 2-5 · ตัดสินจุดขัดรายข้อ · อนุมัติ spec (จบ P2) · กด merge PR (จบ P5)

---
