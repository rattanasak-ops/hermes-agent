---
memory-schema: v1.2
spec_id: SPEC-ANCHOR
status: building        # approved (เจ้าของเคาะ) → โค้ด+test เสร็จ · รอ merge (Zone แดง) → done
linked_plan: SPEC-CENTRAL
owner_approved: true     # เจ้าของพิมพ์ "approve" 2026-07-15
updated: 2026-07-15
---

# สเปค: ให้ plan-anchor ใส่เนื้อสเปคลงใบสั่งงาน (brief) ของ AI Relay

> รัฐธรรมนูญ = Locked Decisions Vault + CLAUDE.md · ห้ามขัด
> (สเปคทดลอง — พิสูจน์ว่าแม่แบบ _TEMPLATE.md ใช้เขียนงานจริงได้)

## 1. จะทำอะไร · ทำไม
- ทำอะไร: เพิ่มให้ `plan-anchor --emit-brief` ดึง `.project/spec/<spec_id>.md` มาผนวกในใบสั่งงาน ถ้ามี  [fact]
- ทำไม: คนเขียนโค้ด (Codex/Grok) เห็นสเปคเต็มในใบสั่ง ลดงานหลุดสเปค = ป้องกันการพลาดสะสม  [fact]

## 2. จุดที่เคลียร์แล้ว (สมองตัดสิน 2026-07-15)
- [x] ไม่มีไฟล์ spec → ทำงานเดิม (เฟส+ข้อห้ามจาก plan.md) เฉย ๆ · ยืนยันด้วย test A3 (ของเก่าไม่พัง)  [fact]
- [x] convention: ไฟล์สเปคหลักของแผน = `.project/spec/<plan_id>.md` (derive อัตโนมัติ · override ด้วย `--spec` ได้)  [fact]

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
| A1 | โค้ดอ่าน spec ถ้ามี ผนวกใน brief | `scripts/ai-relay/plan-anchor.py` `read_spec()` + `brief_lines()` | ✅ |
| A2 | test เคส "มี spec → brief มีเนื้อ" | `test_plan_anchor.py::test_emit_brief_includes_spec_when_present` | ✅ |
| A3 | test เคส "ไม่มี spec → ไม่พัง" | `test_plan_anchor.py::test_emit_brief_without_spec_unchanged` | ✅ |

> gate: `venv/bin/python -m pytest scripts/ai-relay/tests/test_plan_anchor.py -q` → **11 passed** (2026-07-15)

## 6. ส่งต่อ AI Relay
- status = draft → ยังห้ามเขียนโค้ด (รอเจ้าของอนุมัติ + เคลียร์จุดข้อ 2)
- verified = แถว gate-run (test A2+A3 เขียว) เท่านั้น
