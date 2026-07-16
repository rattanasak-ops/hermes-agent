---
title: Use Migrate 0 — เปิดโปรเจกต์ (FW-P0)
aliases:
  - Use Migrate 0
  - use-migrate-0
  - ใช้ Migrate 0
  - เปิดโปรเจกต์ Migrate
tags:
  - prompt-shortcuts
  - migrate-web
  - flow-13
  - phase-0
status: active
version: "1.0"
updated: 2026-07-16
contract: use-migrate-phase-contract (บังคับอ่านก่อน)
station: FW-P0 · ครั้งเดียวต่อโปรเจกต์
---

# Use Migrate 0 — เปิดโปรเจกต์ (สถานี FW-P0)

> ทำ**ครั้งเดียวต่อโปรเจกต์** ก่อนเข้าลูปเมนูใด ๆ · ถ้าโปรเจกต์นี้ทำแล้ว (มี `.work/profile.yaml` ที่เจ้าของล็อก) ให้รายงานสถานะแล้วชี้ไป `Use Migrate 1` แทน — ห้ามทำซ้ำทับของเดิม

## Prompt

```text
Use Migrate 0

อ่านสัญญากลาง use-migrate-phase-contract.md ก่อน แล้วทำตามโครง 5 ส่วน

[ส่วน 1 · ด่านเข้า]
- เฟสนี้คือจุดเริ่มของทุกอย่าง จึงไม่ต้องมีไฟล์เฟสก่อนหน้า แต่ต้องตรวจ:
  (ก) อยู่ใน git repo ของโปรเจกต์ลูกค้าที่ถูกต้อง (git rev-parse + ชื่อ repo ตรงกับที่เจ้าของสั่ง)
  (ข) ถ้ามี .work/profile.yaml อยู่แล้ว = โปรเจกต์เปิดไปแล้ว → รายงาน + หยุด ชี้ไป Use Migrate 1
- ประกาศสถานีทุกคำตอบ: [Migrate เฟส 0/13 · สถานี FW-P0 · โปรเจกต์: <ชื่อ>]

[เนื้องาน 12 ข้อ — ทำตามลำดับ · ทุกข้อมีหลักฐานจริง]
P0-1 ตรวจว่า Root Admin สร้างโปรเจกต์ลูกค้ารายนี้แล้ว (query sys_site จริง) — ยัง = แจ้งเจ้าของ หยุดทั้งเฟส
P0-2 สร้างโครง .work/ + ร่าง profile.yaml (โหมดหลัก MIGRATE/REMEDIATE/BUILD · แทร็ก DATA/FORM/MINISITE/BILINGUAL · งวดเงิน/วันส่ง/ค่าปรับจาก TOR · รายชื่อทีม)
  → ค่าทุกตัวเป็น "ข้อเสนอ" — เจ้าของเป็นคนล็อก (พิสูจน์ผู้แก้จาก git log author)
  → ด่านไฟล์เข้า git จริง: git check-ignore -v .work/ ต้อง 0 hit + git ls-files เห็นไฟล์ครบ — ติด ignore = เจาะรู !.work/** ก่อน
P0-3 บัตรมาตรฐาน (.work/standards-profile.md): W3C/WCAG เวอร์ชัน+เครื่องมือ+หลักฐานส่งมอบตาม TOR · PDF · ขนาดจอ · ITA ไฟล์รายปี
P0-4 ทะเบียน REQ (.work/req-register.md): มีแล้วผูกเข้า · ยังไม่มีสร้างจาก TOR ข้อต่อข้อ + baseline + ประวัติแก้ทุกครั้ง
P0-5 ตาราง gap มาตรฐานภาครัฐ/ITA → ถามเจ้าของรายข้อ: สร้าง/ปิดไว้/ไม่ใช้ (โปรเจกต์ที่เคยเคาะแล้วห้ามถามซ้ำ — เช็คความจำก่อน)
P0-6 บัญชีคิวเมนู (.work/menu-queue.md): จัดกลุ่มตาม treatment + ลำดับความสำคัญ + เจ้าของงานรายคน
P0-7 ตารางระบบภายนอก (ThaID/e-GP/GA/SMTP/…): เข้าไม่ได้ = สถานะ BLOCKED + ชื่อเจ้าของเรื่อง + วันปลด · ห้ามข้ามเงียบ
P0-8 Elasticsearch ติดตั้ง+index ครบระดับโปรเจกต์ (curl จริง แปะผล)
P0-9 Image Source Registry (.work/image-sources.yaml): Freepik/Recraft/Topaz/Magnific + ก่อนใช้ทุกตัว smoke call จริง 1 งานเล็ก — auth ผ่านเฉย ๆ ไม่นับ
P0-10 ผูกชุดแจกความรู้ (คลัง layout 42 module / effects / QAQC) + จดเลขรุ่นใน profile
P0-11 เช็ค Module แจ้งไฟล์เสียใน engine — ยังไม่มี = ใบงาน factory backlog + จดว่าเมนูที่มีไฟล์แนบยังปิดเกตไม่ได้จนกว่าจะมี
P0-12 ที่มาระบบดีไซน์ (ด่านบังคับห้ามข้าม): DS ต้องผ่าน Use Create Design System เท่านั้น
  · มีของเก่า → อัปเกรด (audit เทียบ checklist รุ่นปัจจุบัน) · ยังไม่มี → สร้างใหม่เต็ม 5 เฟส
  · จดลง profile: ds_version / ds_standard_รุ่น / ds_origin
  · DS ต้องต่อเข้าระบบจริง 4 ข้อ: token gen เป็น ts/css · หน้า consume token ไม่ hardcode · หน้าโชว์เปิดได้ · ds-check เป็นด่าน CI
  · ขาดข้อใด = BLOCKED_DS_ORIGIN ห้ามเข้าลูปเมนู

[ส่วน 4 · ชุดคำถามบังคับ — ถามเจ้าของรอบเดียวแล้วหยุดรอ]
1. โหมดหลักของโปรเจกต์นี้: MIGRATE (ย้ายเว็บเก่า) / REMEDIATE (ซ่อมเว็บปัจจุบัน) / BUILD (สร้างใหม่จากฐานข้อมูล)?
2. แทร็กเสริมที่ต้องเปิด: DATA / FORM / MINISITE / BILINGUAL (เลือกได้หลายอัน หรือไม่มี)?
3. งวดเงิน + วันส่ง + ค่าปรับ ตาม TOR (หรือชี้ไฟล์ TOR ให้ผมถอดแล้วพี่ตรวจ)?
4. ตาราง gap มาตรฐานรัฐ/ITA ที่ผมสรุป: ข้อไหน สร้าง / ปิดไว้ / ไม่ใช้?
5. รายชื่อทีมที่จะทำโปรเจกต์นี้ (ผูกคิวเมนูรายคน)?
→ คำตอบทั้งหมดจดลง profile.yaml + ไฟล์ที่เกี่ยว · เจ้าของ commit เองหรือยืนยันให้จดแทน (จด author ชัด)

[ส่วน 5 · ตารางจบเฟส]
(ก) บัญชีของส่งมอบ — พิสูจน์ด้วย ls + git ls-files ทีละไฟล์:
  .work/profile.yaml (เจ้าของล็อก) · .work/standards-profile.md · .work/req-register.md ·
  .work/menu-queue.md · .work/image-sources.yaml · ตารางระบบภายนอก · ผล curl ES · บันทึก DS 3 ช่อง
(ข) ตาราง comply P0-1..P0-12 ครบ 12 แถว + หลักฐานต่อข้อ (✅/⚠️/❌ · มีตกต้องรายงาน % จริง)
(ค) เลขจากเครื่อง: โปรเจกต์มี flow_gate.py = แนบผล status · ไม่มี = ระบุ "เครื่องยังไม่คุม" ตรง ๆ
ปิดท้ายด้วยประโยคตายตัว: จบเฟส 0 — รอพี่ตรวจ · ถ้าผ่าน พิมพ์ `Use Migrate 1` เพื่อไปต่อ · ผมเดินต่อเองไม่ได้ (กุญแจอยู่ที่พี่)
```

## Changelog

- v1.0 (2026-07-16): เปิดใช้ (active) หลังผ่านผู้ตรวจต่างค่าย (Grok · แก้ BLOCKING 6/6) + ทดสอบเจาะเรียกข้ามลำดับ 2/2 (AI สดปฏิเสธถูกต้องทั้งคู่)

- v0.1 (2026-07-16): ร่างแรกตามแผนแยกเฟส (เจ้าของอนุมัติ 13+1) · เนื้อจาก use-migrate-web v1.2 หัวข้อ FW-P0 ครบ 12 ข้อ ไม่ตัดทอน · เพิ่มด่านเข้า/ชุดคำถาม/ตารางจบเฟสตามสัญญากลาง

## Graph Links

- สัญญากลาง: [[skills/prompt-shortcuts/references/use-migrate-phase-contract|use-migrate-phase-contract]]
- ตัวนำทาง: [[skills/prompt-shortcuts/references/use-migrate-web|use-migrate-web]]
- เฟสถัดไป: [[skills/prompt-shortcuts/references/use-migrate-1|use-migrate-1]]
