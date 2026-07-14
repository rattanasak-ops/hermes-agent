---
memory-schema: v1.2
spec_id: SPEC-ANCHOR
status: draft
linked_plan: SPEC-CENTRAL
owner_approved: false
updated: 2026-07-14
---

# สเปค: ให้ plan-anchor ใส่เนื้อสเปคลงใบสั่งงาน (brief) ของ AI Relay

> รัฐธรรมนูญ = Locked Decisions Vault + CLAUDE.md · ห้ามขัด
> (สเปคทดลอง — พิสูจน์ว่าแม่แบบ _TEMPLATE.md ใช้เขียนงานจริงได้)

## 1. จะทำอะไร · ทำไม
- ทำอะไร: เพิ่มให้ `plan-anchor --emit-brief` ดึง `.project/spec/<spec_id>.md` มาผนวกในใบสั่งงาน ถ้ามี  [fact]
- ทำไม: คนเขียนโค้ด (Codex/Grok) เห็นสเปคเต็มในใบสั่ง ลดงานหลุดสเปค = ป้องกันการพลาดสะสม  [fact]

## 2. จุดต้องเคลียร์ก่อนเขียนโค้ด
- [ ] ไม่มีไฟล์ spec → ทำงานเดิม (เฟส+ข้อห้ามจาก plan.md) เฉย ๆ ใช่ไหม → คาดว่าใช่ (ของเก่าต้องไม่พัง)  [assumption]
- [ ] spec_id มาจาก plan_id ตรง ๆ หรือ field แยกใน plan.md?  [assumption]

## 3. ขอบเขต
- ทำ (in): แก้ `plan-anchor` โหมด emit-brief + test
- ไม่ทำรอบนี้ (out): ไม่แตะ relay-call/gate-run · ไม่แตะ prompt shortcut กลาง (= Zone แดง)

## 4. เกณฑ์ผ่าน
| # | given | when | then |
|---|---|---|---|
| 1 | มี `.project/spec/SPEC-ANCHOR.md` | รัน emit-brief | brief มีเนื้อ WHAT/WHY + เกณฑ์ผ่าน |
| 2 | ไม่มีไฟล์ spec | รัน emit-brief | ทำงานเดิม ไม่ error (ของเก่าไม่พัง) |

## 5. ตารางแม่กันหาย
| รหัส | สิ่งที่ต้องมี | จุดพิสูจน์ path:line | สถานะ |
|---|---|---|:---:|
| A1 | โค้ดอ่าน spec ถ้ามี ผนวกใน brief | plan-anchor (รอ verify path) | ☐ |
| A2 | test เคส "มี spec → brief มีเนื้อ" | test file | ☐ |
| A3 | test เคส "ไม่มี spec → ไม่พัง" | test file | ☐ |

## 6. ส่งต่อ AI Relay
- status = draft → ยังห้ามเขียนโค้ด (รอเจ้าของอนุมัติ + เคลียร์จุดข้อ 2)
- verified = แถว gate-run (test A2+A3 เขียว) เท่านั้น
