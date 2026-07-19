> memory-schema: v1.2
> อ่านตามลำดับ: plan-index.md → plan.md (active: SHORTCUT) → session-log-2026-07-19-shortcut-central-close.md → decisions.md

# Overview & Progress — Hermes Agent

อัปเดตล่าสุด: 2026-07-19 · แผน active `SHORTCUT` = 28/29 (96.6%) · โค้ดและแผนกลางอยู่บน `main` ผ่าน PR #84/#85/#86 · เหลือ notebook ทีมรายบุคคล

## สถานะล่าสุด

- ต้นเหตุ Worktree อัตโนมัติแก้ครบทั้ง Shortcut, Skill ที่โหลดจริง, Hook และตัวติดตั้งทีม
- GitHub `main` หลังงานโค้ด+แผนกลาง = `165fdfcf2389748c6b321bab5d0e0ea65d710a55`; PR #84, #85 และ #86 รวมแบบ merge commit
- Mac และ VPS ใช้รุ่น `2026.07.19-5` ผ่าน Prompt Shortcut 33/33 และ Hook 6/6
- Mac/VPS ผ่าน workspace response 4/4, phase autonomy 4/4 และ current workspace 23/23
- ระบบแผนกลางมี 10 แผน แยกหนึ่ง `plan_id` ต่อไฟล์ และ active 1/1 คือ SHORTCUT
- รายละเอียดหลักฐาน: `.project/session-log-2026-07-19-shortcut-central-close.md`

## งานถัดไป

1. เมื่อตรวจพบ notebook ทีมที่เข้าถึงได้ ให้ติดตั้งจาก `main` และบันทึกผล 33/33 ต่อเครื่อง
2. หลังเครื่องทีมครบ เปลี่ยน SHORTCUT-P7-I1 เป็น 1/1 และปิดแผน SHORTCUT 29/29 = 100%
3. แผน parked อื่นเริ่มได้เฉพาะเมื่อเจ้าของสั่ง โดยเปลี่ยน `active_plan_id` และต้องคง active เพียง 1 แผน

## ข้อห้าม/กติกาล็อก

- AI ใช้ Git root/กิ่งปัจจุบันเท่านั้น ห้ามสร้าง สลับ ย้าย หรือลบ Worktree/กิ่งเอง
- ห้ามลดเพดาน 5 commit/30 ไฟล์เพื่อให้ด่านผ่าน และห้ามใช้ squash หากจะนำกิ่งเดิมกลับมาใช้
- ห้ามใช้ AI Relay เว้นแต่เจ้าของสั่งตรง
- VPS/ทีมติดตั้งเฉพาะ payload, Skill และเครื่องมือกลาง ห้ามคัดลอกทั้ง Obsidian vault
- แผน historical เป็นหลักฐาน ไม่มีสิทธิ์แทนนโยบายปัจจุบัน
- ไฟล์ความจำใหม่ต้องอยู่ใน `.project/` และต้องถูก Git ติดตามจริง

## งานค้าง/ส่งต่อ

- `SHORTCUT-P7-I1` = claimed 0/1: ไม่มีบัญชี host/ช่องทาง SSH ของ notebook พนักงานจากเครื่องนี้
- SSH ที่พบ: linux-nat, myserver, myserver-stable, proxmox, SynerryWeb2026; Tailscale ที่ online: linux-nat และ new-www-146 — ไม่มีรายการใดผูก staff id ว่าเป็น notebook ทีม จึงห้ามเดาแล้วติดตั้ง
- เส้นทาง `nat + hermes-agent` บน VPS ยังไม่อยู่ในทะเบียน route; รอบนี้จึงติดตั้งจาก archive ของ GitHub `main` ในโฟลเดอร์ชั่วคราวโดยไม่ใช้พื้นที่ของคนอื่น
- next_owner: เจ้าของให้บัญชีเครื่องทีมที่เข้าถึงได้ → AI ติดตั้ง/ตรวจต่อในพื้นที่เดิม

---

## project นี้คืออะไร (2-3 บรรทัด)
ศูนย์เครื่องมือ AI ส่วนตัวของเจ้าของ (fork จาก NousResearch/hermes-agent v0.17.0 + ของต่อเติม ~3,215 commit): สายพาน AI Relay ประหยัดเงิน · ชุด shortcut คุมวินัยงาน · มาตรฐานกลาง 30-40 โปรเจกต์ (hermes-standard) · เครื่องมือคุมคุณภาพ (violation-audit, pr-review-gate, curse tracker) · gateway ให้ทีม 15 คนใช้บน VPS [fact]

## เสร็จแล้ว (verified) + ประวัติย่อ
- 2026-07-07: PR #15 แก้ auth ปลอม relay-call merge เข้า main (`5aa135e7f`) · สอบสวนต้นตอ AI มั่ว 6 ข้อ + แผน GRD อนุมัติ [fact]
- 2026-07-06: P0-P1 แผนเก่า merged — PR #12 (`da4689a58`) · Project OS ครบ 4/4 · ความจำอยู่ `.project/` [fact]
- 2026-07-05: กู้ shortcut Project OS 3 ตัว (ถูก revert `fff10805b` เมื่อ 2026-06-28 โดยความจำยังจดว่าครบ) + ด่านไฟล์เข้า git จริงทั้งระบบ (`f079acf47`) · relay-call เพิ่มนาฬิกากันค้าง — pytest 16/16
- 2026-07-04-05: relay P3 ครบ 4/4 — PR #8, #9, #10 merged · F1 violation-audit + F2 pr-review-gate ใช้จริง (tier 3) · AI Relay ยืนยันทั้ง notebook + VPS
- 2026-06-21: ด่านกันลบโฟลเดอร์งานทั้งก้อน phase-013 (Codex เขียน · ตรวจแล้ว 38+14 เทสต์) — เข้า main ที่ `f9fb0827f`
- ก่อนหน้า: ดู decisions.md + session log ใน vault (`projects/hermes-agent-dev/`)
