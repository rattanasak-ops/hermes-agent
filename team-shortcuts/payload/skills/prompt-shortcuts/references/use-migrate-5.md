---
title: Use Migrate 5 — ทิศทางภาพต่อหน้า (M2.5)
aliases: [Use Migrate 5, use-migrate-5, ใช้ Migrate 5]
tags: [prompt-shortcuts, migrate-web, flow-13, phase-5]
status: active
version: "1.0"
updated: 2026-07-16
contract: use-migrate-phase-contract (บังคับอ่านก่อน)
station: M2.5 · ต่อ 1 เมนู
---

# Use Migrate 5 — Image Direction กำหนดโทนภาพต่อหน้า (สถานี M2.5)

> ห้ามคิดคำค้นภาพเอง — ทุกคำถอดจากไฟล์วิเคราะห์แบรนด์+โจทย์+ตารางอารมณ์ เพื่อให้ภาพทั้งเว็บไปทางเดียวกัน

## Prompt

```text
Use Migrate 5

อ่านสัญญากลาง use-migrate-phase-contract.md ก่อน แล้วทำตามโครง 5 ส่วน

[ส่วน 1 · ด่านเข้า — รันจริง แปะผล]
1. .work/profile.yaml มีจริง — ไม่มี = MIGRATE_BLOCKED: ต้องทำ Use Migrate 0 ก่อน
2. ล็อกเมนูยังเป็นชื่อเรา + .work/menu-cards/<เมนู>.brief.md ปิดแล้ว (9 หัวข้อ + คำตอบเจ้าของ) — ไม่มี = BLOCKED กลับเฟส 4
3. ไฟล์ต้นทางที่ใช้ถอด (strategy master + emotion-matrix + ตาราง WOW Style — path ตามชุดแจกความรู้ใน profile) ต้องเปิดอ่านได้จริง (แปะผล ls) — ไม่มี = หยุดถามเจ้าของชี้ไฟล์ · **ห้ามถอด keyword จากของสมมติหรือจากความจำ**
- ประกาศสถานี: [Migrate เฟส 5/13 · สถานี M2.5 · เมนู: <ชื่อ> · โปรเจกต์: <ชื่อ>]

[เนื้องาน — 10 ข้อ ลงไฟล์ .work/menu-cards/<เมนู>.image-direction.md]
M2.5-1 ห้ามคิดคำค้นภาพเอง — ถอดจากไฟล์วิเคราะห์ (strategy master + brief + emotion-matrix)
M2.5-2 Emotion เป้าหมายของหน้า ← ถอดจาก strategy (อารมณ์ต่อกลุ่มผู้ใช้)
M2.5-3 Style ภาพ ← ถอดจากตาราง WOW Style Intelligence
M2.5-4 Mood & Tone (สี/แสง/องค์ประกอบ) ← จากแบรนด์ · ทุกหน้าไปทางเดียวกัน
M2.5-5 ประเภทภาพต่อ section ← คน (ไทยเท่านั้น) / วัตถุ / สภาพแวดล้อม / เวกเตอร์
M2.5-6 Keyword ค้นภาพ ← ถอดจาก emotion+style+เนื้อหา ไม่ใช่เดา
M2.5-7 ห้าม: ภาพต่างชาติ · ภาพที่ AI สร้าง (ชั้นภาพถ่าย/คน) · โทนสงสาร · ภาพซ้ำแนวเดียว
M2.5-8 ภาพต้องสื่ออารมณ์ของหน้า + ดันแบรนด์ (สอดคล้องเนื้อหา ไม่ใช่แค่สวย)
M2.5-9 ค้นภาพในเฟสถัดไปด้วย keyword จากไฟล์นี้เท่านั้น
M2.5-10 ความหลากหลาย: เพศ/วัยสมดุลระดับทั้งหน้า (ไม่บังคับรายภาพ) · ห้ามเหมารวมอาชีพ-เพศ

ใบเสนอภาพ — เตรียมโครง 5 ช่องต่อภาพ (ใช้จริงเฟส 6 · ชุดเดียวทุกไฟล์):
section ที่ใช้ / Emotion ที่สื่อ / Pain Point / ความคาดหวัง / Value+Wow
+ เลือก source ต่อภาพจาก .work/image-sources.yaml (Freepik ค้น stock · Recraft เวกเตอร์ · Topaz รีทัช · Magnific ขยาย-เติม)

[ส่วน 4 · ชุดคำถามบังคับ — รอบเดียว แล้วหยุดรอ]
ส่งร่างทิศทางภาพ (emotion/style/mood/keyword ต่อ section) แล้วถาม:
1. โทนภาพรวมของหน้านี้ตามที่ถอดมา — ตรงใจพี่ไหม ปรับตรงไหน?
2. ชุด keyword ค้นภาพต่อ section — ผ่านไหม?
→ คำตอบจดลง image-direction.md

[ส่วน 5 · ตารางจบเฟส]
(ก) ของส่งมอบ: .work/menu-cards/<เมนู>.image-direction.md — พิสูจน์ ls + git ls-files
(ข) ตาราง comply M2.5-1..M2.5-10 = 10 แถว + หลักฐาน
(ค) เลขจากเครื่อง: flow_gate.py ถ้ามี · ไม่มี = ระบุ "เครื่องยังไม่คุม"
ปิดท้าย: จบเฟส 5 — รอพี่ตรวจ · ถ้าผ่าน พิมพ์ `Use Migrate 6` · ผมเดินต่อเองไม่ได้ (กุญแจอยู่ที่พี่)

[ข้อห้ามเฉพาะเฟสนี้]
- ห้ามค้น/โหลดภาพจริง (งานเฟส 6) — เฟสนี้กำหนดทิศทางเท่านั้น
```

## Changelog

- v1.0 (2026-07-16): เปิดใช้ (active) หลังผ่านผู้ตรวจต่างค่าย (Grok · แก้ BLOCKING 6/6) + ทดสอบเจาะเรียกข้ามลำดับ 2/2 (AI สดปฏิเสธถูกต้องทั้งคู่)

- v0.1 (2026-07-16): ร่างแรก · M2.5-1..10 + ใบเสนอภาพ 5 ช่อง (I1-19) + เลือก source จาก registry + โครงสัญญากลาง

## Graph Links

- สัญญากลาง: [[skills/prompt-shortcuts/references/use-migrate-phase-contract|use-migrate-phase-contract]]
- ก่อนหน้า: [[skills/prompt-shortcuts/references/use-migrate-4|use-migrate-4]] · ถัดไป: [[skills/prompt-shortcuts/references/use-migrate-6|use-migrate-6]]
