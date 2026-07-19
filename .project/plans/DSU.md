# Plan — DSU (Design System Standard Upgrade)

> lifecycle: parked
> progress: 14/16 = 87.5%
> หลักฐานล่าสุด: P1-P3 ปิดครบ; P4 75%; P5 0%; เหลือ pilot P4-I3 และเครื่องพนักงาน


> plan_id: DSU · สถานะ: **P0-P3 งานเนื้อจบครบ (2026-07-15) — เหลือเจ้าของกด merge PR** · ผลจริง: prompt v3.0 (2 สำเนา + คลัง) · เช็กลิสต์ v3.1 = 109 หัวข้อ · ds-gate.py (pytest 10/10) · Grok รีวิวรอบแรก FAIL 17 ข้อ → Codex แก้ → เครื่องตรวจยืนยันปิด 17/17 (Grok รอบยืนยันออกผลไม่จบ 2 ครั้ง → สลับเครื่องตรวจตาม DEC-MW-002)
> (เจ้าของอนุมัติในแชท 2026-07-15 "วางแผนทำงานทั้งหมดตามนี้และบันทึกในหน่วยความจำ และต้องทำให้จบเท่านั้น โดยใช้ use continue")
> เจ้าของโจทย์: มาตรฐาน DS ใช้จริงได้ ~15-20% ของระดับ Global — ให้ยกมาตรฐานกลาง ไม่ใช่ยิงกับ project ใดโปรเจกต์หนึ่ง
> กิ่งงาน: task/nat/DSU-P1-I1-ds-standard-hardening (worktree แยกจาก main · เปิดผ่าน hermes worktree open หลังพี่เคลียร์ดิสก์)
> ทีม: แชทนี้ (Fable/Opus) = วิเคราะห์+ตัดสิน · Codex = ตัวเขียน · Grok = ผู้ตรวจ (คำสั่งเจ้าของ DEC-163) · ผู้ตรวจเดิม 2 รอบไม่ผ่าน → เปลี่ยนเครื่องตรวจ/ค่าย (DEC-MW-002)
> กติกาบังคับ: ยึด v3 เดิม เพิ่มไม่รื้อ (คง alias) · เลื่อน version + changelog · commit ทันทีทุกชิ้น · งานหลายเฟส = 1 PR · ห้าม merge/push→main เอง

## ผลวินิจฉัย (หลักฐานจริง 2026-07-15)

ราก 3 ข้อที่ทำให้สนามจริงเหลือ ~15-20%:
1. **เวอร์ชันหลุดกัน**: ทะเบียนบอก shortcut = v2.5 (92 หัวข้อ + S1 + ชั้น U) แต่ไฟล์ prompt จริงทั้ง 2 สำเนา (Obsidian + team-shortcuts/payload) = v2.4 · grep "ชั้น U/S1/92/v3" = 0 ครั้ง → ทุกโปรเจกต์ได้ Flow รุ่นเก่า
2. **ไม่มีเครื่องบังคับชั้นแบรนด์**: H1 (วิสัยทัศน์/พันธกิจ) F5 (Emotion) F6 (Function) F1+C12 (บุคลิก/เสียงแบรนด์) มีในเช็กลิสต์ v3 ครบ แต่เป็นตัวหนังสือที่ AI ข้ามได้เงียบ ๆ — เครื่องตรวจมีแค่ ds-check.py (token) + contrast-audit (สี) · Mood & Tone ยังไม่เป็นหัวข้อชัด
3. **ฝั่งแอดมินบางจริง**: Core มีหัวข้อแอดมิน ~13 ข้อ เทียบ Carbon ~50 / Polaris・Ant ~60-70 + แม่แบบหน้า → ครอบคลุม ~15-25%

## DSU-P1 · ซ่อมราก + งาน 1 (แก้ Flow ที่ทำงานผิดพลาด)

- **I1 · ยก prompt เป็น v3.0**: use-create-design-system.md ทั้ง 2 สำเนา — ผูกเช็กลิสต์ v3 (92 หัวข้อ) เข้า Flow ตรง ๆ · เพิ่มชั้น U + กฎ S1 เข้าลำดับรัน H→U→F→G→A→B/C→(Packs)→D · อ้าง ds-gate.py เป็นด่านเครื่องต่อเฟส
- **I2 · กฎ F1-F4 → เช็กลิสต์ชั้น D ข้อ D14-D17** (ทุกข้อมีวิธีตรวจจริง):
  - D14 (=F1 เจ้าของ) กัน tree ชน: เช็ก `git branch --show-current` + `git status` ก่อนเขียนทุกครั้ง + commit ทันทีหลังจบ 1 ชิ้น ห้ามค้าง uncommitted ข้ามเทิร์น · วิธีตรวจ: rule (git status สะอาดหลังทุกชิ้น + commit SHA แนบ)
  - D15 (=F2) UI verify tier 4: ส่ง/เคลม URL ต้องเปิดเบราว์เซอร์ถ่ายภาพจริง ไม่ใช่ curl 200 · วิธีตรวจ: manual-evidence (ไฟล์ภาพ + คำบรรยาย 1 บรรทัด)
  - D16 (=F3) เครื่องพร้อม: งานหนักเช็กแรมว่าง + restart dev server ล้าง .next เมื่อ webpack เพี้ยน · วิธีตรวจ: rule (คำสั่งเช็กแรม/ล้าง cache ระบุใน spec)
  - D17 (=F4) เช็กข้อห้าม: อ่าน .project/decisions.md + Locked Decisions ก่อนทำตามแผน (ห้ามแตะ BOI/MOL/Master/Reveal) · วิธีตรวจ: rule (ds-gate ตรวจว่ามีบันทึก "อ่าน decisions แล้ว + รายการข้อห้ามที่เกี่ยว" ใน DesignSystem.md)
- **I3 · ds-gate.py**: เครื่องตรวจเฟสแบบ mw-spec-check.py — ตรวจว่า artifact ชั้น H/U/F มีจริงก่อนปล่อยชั้นถัดไป:
  - H: .project/DesignSystem.md มีหัวข้อ H1-H7 กรอกจริง (บัตรประจำตัว: วิสัยทัศน์/พันธกิจ ≥1 ย่อหน้า · เหตุผลสี ≥1 แถวต่อสี · ตาราง pain→ดีไซน์ ≥3 แถว)
  - U: มีบันทึกกฎ UX 7 ข้อ + ทดสอบ 5 วินาที
  - F: ตาราง Emotion 6 แกน → token ≥3 ค่าต่อแกน · Mood & Tone กรอกแล้ว
  - โหมด: `ds-gate.py --layer H|U|F|all` · exit 0 = ผ่าน · exit 1 = ขาด (บอกรายการที่ขาด) · fail-closed
- **I4 · หัวข้อใหม่ F7 · Mood & Tone**: แยกจาก F1/F5 ให้เป็นข้อชัด (โทนภาพ/เสียง/จังหวะ ต่อ touchpoint) 🔴
- จุดนับผ่าน P1: ds-gate.py จับเคส "ข้ามชั้น" ได้จริง (ทดสอบกับไฟล์ตัวอย่างขาด H) + exit 0 กับไฟล์ครบ · Grok ตรวจผ่าน · commit SHA ทุกชิ้น

## DSU-P2 · เติมหลังบ้าน (งาน 2 · เทียบ Carbon/Polaris/Ant/Cloudscape/Atlassian)

- **I1 · ขยาย B4 ตารางขั้นสูง**: + ปรับกว้าง/สลับ/ปักคอลัมน์ · จัดกลุ่มแถว · tree table · แถวขยาย · pagination ฝั่ง server · export CSV (ที่มา: Carbon/Ant/Cloudscape)
- **I2 · หัวข้อใหม่ชุดแอดมินเข้าชั้น B/C**:
  - B18 ตัวกรอง faceted + แถบ bulk action + saved views (Polaris/Cloudscape)
  - B19 Command palette (Cmd+K) + ระบบคีย์ลัด (Atlassian/Carbon)
  - B20 Drawer/side-panel (Ant/Atlassian)
  - C17 ศูนย์แจ้งเตือนผู้ใช้ + ไทม์ไลน์ audit log (Ant/Atlassian)
  - B2 ขยาย: ฟอร์มหนาแน่น — validate ในแถว · autosave · ปุ่มปิดตามสิทธิ์+tooltip เหตุผล (Polaris/Cloudscape)
  - A18/B9 ขยาย: คลังกราฟข้อมูลเต็ม — ชนิดกราฟมาตรฐาน + สถานะกราฟ (empty/loading/error) + กติกา format ตัวเลข (Carbon data-viz)
- **I3 · Pack ใหม่ "Admin-Pro"** (โหลดเฉพาะงานหลังบ้านหนัก · ไม่เปลืองบริบทงาน Front):
  - AP1 ตัวเลือกวันที่-เวลา + ช่วงวันที่ · AP2 combobox/autocomplete/multi-select · AP3 อัปโหลดไฟล์ (ลาก-วาง/คืบหน้า/ผิดพลาด) · AP4 แถบแท็บ/accordion/stepper · AP5 skeleton + progress มาตรฐาน · AP6 แม่แบบหน้า 4 แบบ (รายการ/รายละเอียด/สร้าง-แก้/ตั้งค่า) · AP7 หน้า error 403/404/500 + session หมดอายุ · AP8 กันแก้ชนกัน (optimistic UI/conflict) (ที่มา: Polaris/Ant/Cloudscape)
- กติกา: ทุกหัวข้อระบุ (ก) ที่มา ระบบไหน (ข) วิธีตรวจ rule/api/ai/manual — ห้ามป้ายเปล่า · อัปตัวเลขสรุป Core/Packs + บันทึก v3→v3.1 ในเช็กลิสต์
- จุดนับผ่าน P2: นับหัวข้อใหม่ N/M ตรงรายการนี้ครบ · Grok ตรวจผ่าน · commit SHA

## DSU-P3 · ปิดงาน

- I1 เลื่อน version: เช็กลิสต์ v3→v3.1 · prompt v2.4→v3.0 · changelog ทั้งคู่
- I2 อัปแถวทะเบียน prompt-shortcut-registry.md (Obsidian) + สถานะย่อหน้า
- I3 สำเนา payload ให้ตรง (team-shortcuts/payload) · grep รุ่นตรงกัน 3 จุด (ทะเบียน/Obsidian/payload) = 3/3
- I4 Grok ตรวจรวมรอบสุดท้าย · เปิด PR เดียว (เจ้าของกด merge) · อัป OverviewProgress + session log ผ่าน Use Close Chat
- จุดนับผ่าน P3: grep 3/3 + PR เปิดแล้ว + memory เขียนครบ

## DSU-P4 · พิสูจน์ของจริง (pilot Root Admin) + ปิดข้อบกพร่องที่พบ (เจ้าของอนุมัติ 2026-07-16 "ตรงใจ ผมเริ่ม P4 กับ Root Admin ทันที" + "ok ลงมือแก้ prompt ตาม F-01 F-02 F-03 เลย")

> เป้าหมายแม่ (DEC-DSU-001): สิ่งส่งมอบจริง = ตัว shortcut ที่แก้เสร็จ · pilot เป็นเครื่องมือพิสูจน์ · บัญชีข้อบกพร่อง = `.project/dsu-pilot-findings.md`

- **DSU-P4-I1 · เปิดสนามทดลอง Root Admin** (โปรเจกต์ newwebengine2026 · worktree แยก): กรอกชั้น H/U/F → `ds-gate` exit 0 · อัปเดตสำเนามาตรฐานในโปรเจกต์เป็น v3.1 (commit `c669a7a4`) — **จบแล้ว 2026-07-16**
- **DSU-P4-I2 · ปิด F-01/F-02/F-03 ที่ตัว prompt กลาง**: คลัง Obsidian แก้เป็น v3.1 + แถวทะเบียน (commit คลัง `e133f00` · ผ่านผู้ตรวจ GPT-5 แบบ fix-then-proceed แก้ครบ 3/3) → **sync payload ใน repo นี้ให้ตรงคลัง** (งานใน worktree นี้)
- DSU-P4-I3 · เดิน pilot ที่เหลือด้วย prompt รุ่นแก้แล้ว (ด่านสี F-03 ทางยืนยันชุดเดิม → PHASE 4 Codex เขียน Grok ตรวจ → PHASE 5 ด่านเครื่อง + ภาพจริง tier 4)
- DSU-P4-I4 · ปิด F-05: คำสั่ง ds-gate/ds-adopt ที่เป็นการตรวจอ่านอย่างเดียวผ่าน New Chat Gate ได้ พร้อม regression test 2/2
- จุดนับผ่าน P4: payload ตรงคลัง 100% (แฮชตรง) · findings ทุกข้อมีสถานะปิดหรือปักธง · PR เดียวให้เจ้าของกด

## DSU-P5 · ปิดเป้าข้อ 3 (เครื่องพนักงาน · ตามแผนที่เจ้าของรีวิว 2026-07-16)
- พนักงาน 1 คนรันตัวติดตั้งซ้ำบนเครื่องจริง เก็บ `RESULT: PASS` (ตามบทเรียน DEC-MW-007) · งานคน: เจ้าของ push คลัง→GitLab + แจ้งทีม

## ข้อจำกัด/ความเสี่ยงที่จดไว้
- grok headless ต้องมี API key (งานคนค้างเดิม) → ถ้า Grok เรียกไม่ได้ 2 รอบ ให้สลับผู้ตรวจ/เครื่องตรวจตาม DEC-MW-002 และรายงานเจ้าของ
- ไฟล์คลัง Obsidian อยู่นอก repo นี้ (commit แยกในคลัง · push ขึ้น GitLab = งานคนของเจ้าของ)
- ด่านดิสก์ 85%: เจ้าของเลือกเคลียร์พื้นที่เอง (2026-07-15) → เปิด worktree เมื่อต่ำกว่าเพดาน

---
