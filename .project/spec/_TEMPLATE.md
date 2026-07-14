---
memory-schema: v1.2
spec_id: <ชื่องานสั้น เช่น SPEC-ANCHOR>
status: draft            # draft | approved | building | done
linked_plan: <plan_id ใน .project/plan.md>
owner_approved: false    # true ต่อเมื่อเจ้าของพิมพ์อนุมัติ
updated: <YYYY-MM-DD>
---

# สเปค: <ชื่องาน>

> รัฐธรรมนูญโปรเจกต์ = Locked Decisions Vault + CLAUDE.md · สเปคนี้ห้ามขัด
> ไฟล์นี้เป็นแม่แบบกลาง (capability-based) · lifecycle อ่าน/เขียนผ่านจุดเชื่อมท้ายไฟล์

## 1. จะทำอะไร · ทำไม (WHAT / WHY — ห้ามพูดวิธี/เทคโนโลยี)
- ทำอะไร: <ประโยคเดียว>            [fact]
- ทำไม / ใครได้ประโยชน์: <คุณค่า>   [fact]

## 2. จุดต้องเคลียร์ก่อนเขียนโค้ด (ด่านกันเดา · DEC-040)
- [ ] <คำถามกำกวม 1> → คำตอบ: ______

## 3. ขอบเขต
- ทำ (in): ______
- ไม่ทำรอบนี้ (out): ______

## 4. เกณฑ์ผ่าน (ถ้า/เมื่อ/แล้วต้องได้ · given/when/then)
| # | given (สถานะตั้งต้น) | when (ทำอะไร) | then (ผลที่ต้องได้) |
|---|---|---|---|
| 1 | ... | ... | ... |

## 5. ตารางแม่กันหาย (นับ N/M · แบบ scripts/mw-spec-check.py)
| รหัส | สิ่งที่ต้องมี | จุดพิสูจน์ path:line | สถานะ |
|---|---|---|:---:|
| G1 | ... | ... | ☐ |

## 6. ส่งต่อ AI Relay
- ห้ามเริ่มเขียนโค้ดถ้า status ≠ approved
- verified = แถว gate-run เท่านั้น (สืบทอด Schema §3–§4)

<!-- จุดเชื่อม lifecycle (ทาง A · capability-based · ไม่แตะ schema core)
New Chat 0a: อ่าน .project/spec/ ถ้ามี · Act-As: เขียน spec ก่อน/คู่ plan.md
Comply: แตก issue อ้าง spec_id · Continue/Relay: plan-anchor --emit-brief ผนวก spec
Close: Spec Sync (แบบ Business Plan/QA-QC Sync) · Save Git: field spec_gate ใน .savegit.json -->
