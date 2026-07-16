---
title: Use Migrate 10 — ด่านมาตรฐาน 9 เกต + RTM + QA (M6)
aliases: [Use Migrate 10, use-migrate-10, ใช้ Migrate 10]
tags: [prompt-shortcuts, migrate-web, flow-13, phase-10]
status: active
version: "1.0"
updated: 2026-07-16
contract: use-migrate-phase-contract (บังคับอ่านก่อน)
station: M6 · ต่อ 1 เมนู
---

# Use Migrate 10 — Standards Gate 9 เกต (สถานี M6)

> เฟสของ "เครื่องตรวจ" ล้วน ๆ — การให้ AI อื่นช่วยรีวิว ≠ การรันด่าน (จุดที่เคยพัง: M6 = 10% เพราะใช้รีวิวแทนการรันจริง)

## Prompt

```text
Use Migrate 10

อ่านสัญญากลาง use-migrate-phase-contract.md ก่อน แล้วทำตามโครง 5 ส่วน

[ส่วน 1 · ด่านเข้า — รันจริง แปะผล]
1. .work/profile.yaml + บัตรมาตรฐาน .work/standards-profile.md มีจริง — ไม่มี = MIGRATE_BLOCKED
2. ล็อกเมนูยังเป็นชื่อเรา + เฟส 9 ปิดแล้ว (ผลด่านตาย backend ครบ) — ไม่มี = BLOCKED กลับเฟส 9
- ประกาศสถานี: [Migrate เฟส 10/13 · สถานี M6 · เมนู: <ชื่อ> · โปรเจกต์: <ชื่อ>]

[กฎเหล็กของเฟสนี้ — แก้เหตุ M6 เคยได้ 10%]
การให้ Grok/Codex/AI ใดรีวิว = ความเห็นประกอบ ไม่ใช่การผ่านด่าน · "ผ่าน" นับเฉพาะผลรันเครื่องมือจริงที่แปะในตาราง · ทุกเกตอ้างเวอร์ชัน+เครื่องมือตามบัตรมาตรฐาน SP ของโปรเจกต์ ห้ามใส่เลขเวอร์ชันเอง

[เนื้องาน — 9 เกต กรอกลง .work/deliverables/standards-comply-<เมนู>.md]
M6-1 W3C: 0 error · เครื่องมือตาม SP-1 (validator.w3.org)
M6-2 WCAG: เวอร์ชันตาม SP-2 (ค่าเริ่มต้น 2.1 AA · TOR สั่ง 2.2 ใช้ 2.2) · 0 violation + คีย์บอร์ด/focus + contrast
M6-3 ผู้พิการจริง (มือถือ+โปรแกรมอ่านจอ): ทำงานจบได้ด้วย SR · touch ≥44px · ≤3 คลิก (deal-breaker)
M6-4 PDF/เอกสารเข้าถึงได้: บังคับเมื่อ TOR/SP-4 กำหนด · มี text layer + tag/alt · TOR ไม่บังคับ = แนะนำ ไม่บล็อก
M6-5 Speed: Lighthouse ≥90 มือถือ · CWV ผ่าน
M6-6 Responsive: ไม่ล้น/ไม่พัง ทุกจอตาม SP-5 (ค่าเริ่มต้น 375/768/1440)
M6-7 SEO: Lighthouse SEO ≥95 + meta/schema ผ่าน
M6-8 AI Search: semantic HTML + structured data + llms.txt
M6-9 Provenance ภาพ: asset-register ครบ · ไม่มีภาพคน AI
+ RTM 3 ชั้น: มีข้อกำหนด→มีเทสต์→รันผ่านจริง (mw-rtm-report · ห้ามนับแค่มีรายการ)
+ ES ค้นจริงรายเมนูที่มี search: คำไทย/กรอง/แบ่งหน้า/กรณีไม่พบ (แปะผล query จริง)
+ เกต EN (แทร็ก BILINGUAL): EN ครบเทียบ TH ทุกส่วน
+ Dashboard (ถ้าเมนูมี): เทียบตัวเลขกับแหล่งจริง ≥3 จุด
+ เช็กลิสต์พฤติกรรม 10 ข้อ (pagination จริง/empty state/ไอคอนมีข้อความ/interactive ทำงานจริง/ตอบ journey/related ไม่ซ้ำ/sticky ไม่บัง/ข้อมูลมีแหล่ง/hover สื่อชนิด/ข้อรวมผ่านครบทุกย่อย)
+ Use QA QC เลือกหมวดตามช่วงงานของโปรเจกต์ (25%: Q13/Q01+PDPA/a11y/งบ speed/แผน backup · 50%: Q02/Q03/Q05/Q06 · 75%: Q04 เต็ม/Q08/Q09/Q11/Q12/regression · 100%: Q10 ซ้อมกู้จริง/Q15/Go-No-Go) — ผู้ตรวจต่างค่าย · ผู้แก้ห้ามตรวจงานตัวเอง
+ ทำรายงานสรุปผลตรวจ (W3C/WCAG/จอ) ให้เจ้าของรู้ทุกครั้ง — ฝังผลรันจริง

[กฎวน]
เกตตก = แก้แล้วรันใหม่จนผ่าน (ระดับ 1 วนในเมนูเดิม) · ผู้ตรวจ/วิธีเดิมไม่ผ่าน 2 รอบ = เปลี่ยนวิธี ห้ามยิงรอบ 3 · ห้ามลดเกณฑ์เองเพื่อให้ผ่าน

[ส่วน 4 · จุดถาม-ตอบ]
เฟสนี้เครื่องตัดสิน ไม่รอเจ้าของ ยกเว้น: เกตที่ตกซ้ำเกินกติกาวน หรือเกตที่ TOR กำกวม (เช่น SP-4 PDF) = สรุปทางเลือก+ผลกระทบ ถามเจ้าของก่อน

[ส่วน 5 · ตารางจบเฟส]
(ก) ของส่งมอบ: standards-comply-<เมนู>.md (9 เกต + ผลเครื่องต่อเกต) + ผล RTM + ผล ES + รายงานสรุปให้เจ้าของ
(ข) ตาราง comply: 9 เกต + RTM + ES + EN + Dashboard + เช็กลิสต์ 10 + QA QC — **ทุกแถวต้องมีผลรันเครื่องสถานะ "ผ่าน" เท่านั้นจึงจบเฟสได้** · ห้ามมีแถว "ยังไม่รัน/รอเครื่อง/ตรวจมือแทน" (นั่นคือเฟสยังไม่จบ ห้ามประกาศจบ) · เครื่องมือขาดตัวไหน = `BLOCKED_TOOLING` หยุดรายงานเจ้าของทันที
(ค) เลขจากเครื่อง (บังคับเฟสนี้): Lighthouse/axe/mw-rtm-report/mw-page-check — เลขทุกตัวจากไฟล์ผลจริง AI ห้ามกรอกเอง
ปิดท้าย: จบเฟส 10 — รอพี่ตรวจ · ถ้าผ่าน พิมพ์ `Use Migrate 11` · ผมเดินต่อเองไม่ได้ (กุญแจอยู่ที่พี่)
```

## Changelog

- v1.0 (2026-07-16): เปิดใช้ (active) หลังผ่านผู้ตรวจต่างค่าย (Grok · แก้ BLOCKING 6/6) + ทดสอบเจาะเรียกข้ามลำดับ 2/2 (AI สดปฏิเสธถูกต้องทั้งคู่)

- v0.1 (2026-07-16): ร่างแรก · M6-1..9 + RTM/ES/EN/Dashboard/เช็กลิสต์ 10/QA QC + กฎ "รีวิว ≠ ด่าน" (แก้ R11) + โครงสัญญากลาง

## Graph Links

- สัญญากลาง: [[skills/prompt-shortcuts/references/use-migrate-phase-contract|use-migrate-phase-contract]]
- ก่อนหน้า: [[skills/prompt-shortcuts/references/use-migrate-9|use-migrate-9]] · ถัดไป: [[skills/prompt-shortcuts/references/use-migrate-11|use-migrate-11]]
