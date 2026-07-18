# AIR-P1 — ชุดทดสอบป้องกันปัญหา Portal-only

> สถานะ: ปรับแผนตามคำยืนยันเจ้าของ 100% · ยังไม่ได้เพิ่ม test หรือแก้ production code

## ขอบเขต

เพิ่ม test ที่รอยต่อ `relay-call → relay-portal → AI Portal` หลังสัญญา AIP-P0 ได้รับอนุมัติ โดยรักษา diff เดิมทั้งหมดและไม่เรียก AI จริงในชุด unit test

## กรณีบังคับ

1. `--tool fable` ต้องเรียกเส้น Fable ของ Portal ไม่ใช่ Grok และไม่เรียก CLI ในเครื่อง
2. ผู้ใช้ที่มีสิทธิ์ Fable ได้ผลจาก Fable; ผู้ใช้ที่ไม่มีสิทธิ์ได้ `permission_denied` โดยไม่เปลี่ยน AI
3. โมเดลที่ Portal ยังไม่เปิดได้ `model_unavailable` โดยไม่เพิ่มรอบ AI และไม่เสียค่าเรียกต้นทาง
4. เมื่อไม่มี Portal token ต้องหยุดพร้อม `portal_auth_required`; ห้ามเปลี่ยนไป Grok/Codex/Claude CLI ในเครื่อง
5. Grok เชื่อมต่อหลุดชั่วคราวต้องเป็น `connection_lost`, ลองซ้ำตามเพดาน และไม่ถูกกล่าวหาว่าไม่มีบัญชี
6. Grok token หมดอายุจริงต้องเป็น `auth` พร้อมชื่อบัญชีอ้างอิงที่บังข้อมูลแล้ว
7. Codex App ล็อกอิน slot 01 ต้องให้ Portal เลือกบัญชีทำงาน 02
8. Codex App ล็อกอิน slot 02 ต้องให้ Portal เลือกบัญชีทำงาน 01
9. ถ้าตรวจ slot ไม่ได้ ต้องหยุดพร้อม `identity_unresolved`; ห้ามเดาบัญชีและห้ามเรียก Codex
10. Cursor, Claude Code App และ Codex App ที่ใช้ผู้ใช้เดียวกันต้องได้สิทธิ์โมเดลชุดเดียวกัน
11. โปรแกรมลูกทำงานนานต้องมี heartbeat ที่ stderr โดยไม่เผย prompt, token, email หรือ user ID
12. ข้อมูล Portal ที่ไหลมาต้องขยับเวลาข้อมูลล่าสุดและไม่ถูกตัดด้วย silence timeout
13. startup timeout, silence timeout และ total timeout ต้องตั้งค่าได้และหยุด process group ครบ
14. `KeyboardInterrupt` ต้องได้ `cancelled`, ล้าง `now.json`, ปลด lock และไม่ทิ้ง child process
15. งาน Codex สั้นต้องคืน JSON สุดท้ายได้ โดย stdout ไม่มีข้อความสถานะปน
16. secret ไม่ปรากฏใน stdout, stderr, ledger, fail file หรือ heartbeat
17. ผู้เรียกเดิมที่ระบุ `grok`, `codex`, `opus` ยังใช้รูปคำสั่งเดิมได้ แต่เส้นทางภายในต้องผ่าน Portal

## ลำดับทำ test

1. เขียนตัวจำลอง Portal ที่ตรวจ header/payload และส่งข้อมูลเป็นช่วง
2. เพิ่ม test Fable + สิทธิ์ก่อน เพราะเป็นข้อกำหนดเจ้าของที่เปลี่ยนจากเอกสารเดิม
3. เพิ่ม test Codex 01↔02 และ Grok connection/auth
4. เพิ่ม test progress, timeout, cancel, cleanup และ secret
5. รัน test ใหม่ให้ล้มกับโค้ดปัจจุบัน แล้วจึงเปิด AIR-P2 สำหรับแก้ source

## เกณฑ์ผ่าน AIR-P1

- test ใหม่ครอบ 17/17 กรณี
- เห็น test ล้มจากสาเหตุเดิมก่อนแก้ source
- ไม่มีการเรียก AI จริงหรือใช้กุญแจจริงในชุด test
- ไม่มีไฟล์ production ถูกแก้ใน phase นี้
