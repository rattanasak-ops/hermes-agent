# Plan — SPEC-CENTRAL (สเปคกลาง · เริ่ม 2026-07-17 · ต่อจาก PR #57 merged)

> lifecycle: parked
> progress: 2/7 = 28.6%
> หลักฐานล่าสุด: P5 ปิด; P6-I1 มี commit และ pytest 83/83; เหลือ P6-I2..I4 และ P7


> memory-schema: v1.2 · **plan_id: SPEC** · branch งาน: `task/nat/SPEC-P5-I1-central-prompts-sync` (worktree นำร่อง) · งานหลายเฟส = **1 PR เดียว**
> เป้าหมาย: เพิ่ม "สเปคกลาง" (ไฟล์บอกโจทย์ก่อนเขียนโค้ด) เข้าระบบ shortcut ให้ AI ทุกตัวอ่านโจทย์เดียวกัน — แก้รากที่ AI แต่ละตัวเข้าใจโจทย์ไม่ตรงกัน
> ทีม: Opus = สมองวางแผน/ตรวจ · coder = grok/codex ผ่าน relay (โหมด 2) · ผู้ตรวจ = ต่างค่าย (cross-check ask_gpt5) · เจ้าของ = อนุมัติ + push คลัง + กด merge
> ล็อกเจ้าของ (2026-07-17): ห้ามข้าม flow · ทุกงานโค้ดผ่าน relay โหมด 2

## กติกาเหล็ก (สืบทอด)
1. เลขงานขึ้นต้น `SPEC-` และมีจริงในไฟล์นี้ · ไม่มี = ห้ามทำ (งานจร --no-plan)
2. verified = แถว gate-run/pytest เขียวเท่านั้น · เอกสาร/prompt = manual_verified + เจ้าของยืนยัน
3. ห้ามแตะนอก allowed_paths ของ permit

## SPEC-P5 — สเปคกลางเข้า lifecycle (Zone เขียว-เหลือง) · สถานะปัจจุบัน
- **SPEC-P5-I1** แก้ prompt กลาง 6 ตัว + ทะเบียน ทั้ง 2 สำเนา (คลัง Obsidian + payload) — **verified 2026-07-17**: คลัง 7 ไฟล์แก้แล้ว (รีวิว GPT fix-then-proceed ปิด 3/3) · payload 6 ไฟล์ = vault ทุกไบต์ (diff 7/7 สะอาด · commit `80af2c373`) · ทะเบียน payload ตรง base #58 อยู่แล้ว
  - เทสตรึงรุ่นเก่า 2 ตัวแดงค้าง**ก่อนงานนี้** (base use-new-chat=2.8 vs pin 2.7 · registry/SKILL count 32≠31) — แยกเป็น spawn task ไม่รวมใน PR สเปค
- **ค้างงานคน**: เจ้าของ push คลัง Obsidian 7 ไฟล์ขึ้น GitLab (คนละ repo — AI push ตรงไม่ได้)

## SPEC-P6 — S1 ด่านสัมภาษณ์ก่อนโค้ด (Zone แดง · งานใหญ่ · ยังไม่เริ่ม)
> ร่างออกแบบผ่านตรวจข้ามค่ายแล้ว: `ObsidianVault/HermesAgent/95-Inbox-Lab/review/s1-interview-gate-design-2026-07-15.md` (v0.3 · ปิด 11/17+1/5 · ค้าง C1-C5 ระดับโค้ด)
- **SPEC-P6-I1** เครื่องมือ `spec-interview` (ชุดเดียวกับ relay-call/gate-run): AI ส่งคำถาม เจ้าของตอบผ่านแชท **โค้ดกลางจด** record ลง `.hermes/spec-evidence/<repo>/<plan_id>/` + hash chain + manifest hash → ปิด **C1** (ช่องรับ input ปลอมไม่ได้)
- **SPEC-P6-I2** hook default-deny ครอบ Edit/Write/Bash/relay/subagent + allowlist path ตายตัว + realpath กัน symlink → ปิด **C2** (บังคับชั้น OS/สิทธิ์) + **C5** (fail-closed ด่านหาย/รุ่นไม่ตรง = ปิดเขียน)
- **SPEC-P6-I3** waiver "จอง-ใช้-เขียน" atomic + flock (ปิด **C3**) + ตรวจ-เขียนเหตุการณ์เดียว/ล็อกกันแทรกกลาง (ปิด **C4**)
- **SPEC-P6-I4** ชุดเทสครอบ 13 เคสโจมตี (§9 ของร่าง) + เทส C1-C5 · verified = pytest เขียว + adversarial review ต่างค่าย
- ล็อกงานนี้: security-critical → ต้อง adversarial verify (ผู้ตรวจต่างค่าย พยายามหักล้างทุก C) ก่อนปิด

## SPEC-P7 — S2 (TDD เทสก่อนโค้ด) + กระจาย 30-40 โปรเจกต์ (Zone แดง · ยังไม่เริ่ม)
- **SPEC-P7-I1** S2: เพิ่มด่านเทสก่อนโค้ด (หยิบแนวคิดจาก obra/superpowers · ไม่ลงทั้ง plugin)
- **SPEC-P7-I2** กระจายชุดกลาง+เลขรุ่นผ่าน `Use Hermes Structure` (safe_apply/rollout) · นำร่อง 2-3 โปรเจกต์ไม่ใช่งานลูกค้า · 3 ระยะ รายงาน→เตือน→บังคับ · ปุ่มหยุดฉุกเฉินต่อโปรเจกต์

## ข้อจำกัด/ความเสี่ยง
- S1 (SPEC-P6) เป็น security enforcement gate ที่คุมการเขียนทั้งหมด → ห้ามรีบ · ต้องเทสทุกช่องเขียน + adversarial ก่อนประกาศใช้ (บทเรียนจากด่าน prewrite เดิม)
- ไฟล์คลัง Obsidian นอก repo นี้ (เจ้าของ push เอง)
