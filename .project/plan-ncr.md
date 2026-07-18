# NCR — New Chat + Worktree + Direct App Enforcement

> plan_id: NCR · owner approved: 2026-07-15 · task: NCR-P0-I1
> worktree: `/Users/rattanasak/Documents/Worktrees/hermes-agent/nat/NCR-P0-I1-new-chat-relay-enforcement`
> branch: `task/nat/NCR-P0-I1-new-chat-relay-enforcement`
> ปิดรอบ 2026-07-19: **ARCHIVE_ONLY — ห้ามรวมทั้งกิ่งเข้า `main`**

## คำตัดสินปัจจุบัน

แนวทางที่ให้ `Use New Chat` สร้าง Worktree อัตโนมัติถูกแทนที่แล้วด้วยกติกา
`CURRENT_WORKSPACE_ONLY` บน `main` ผ่าน PR #68 และ #70 ดังนั้นกิ่งนี้เก็บไว้เป็น
หลักฐานกู้คืนเท่านั้น ไม่ใช่งานรอรวม โค้ดหรือเทสต์ที่ยังมีประโยชน์ต้องคัดเป็น
งานเล็กจาก `main` ล่าสุด ห้ามนำทั้งกิ่งเก่ากลับเข้าไป

งาน AI Portal แบบเต็มระบบเป็นงานแยก ต้องมี Portal URL และกุญแจที่กำหนดก่อน
เดินเส้นจริง ส่วนการทำงานรอบนี้ใช้โหมดแอปหลักเขียนและผู้ตรวจข้ามตามคำสั่งเจ้าของ
โดยไม่เปลี่ยนนโยบาย Shortcut กลับไปสร้าง Worktree อัตโนมัติ

## เป้าหมาย

ทำให้ `Use New Chat` เปิด task worktree แล้วให้ Codex App, Claude Code App, Cursor และ Hermes Agent เขียนตรงในขอบเขตที่อนุมัติได้ โดยใช้กติกากลางเดียวกันบน Notebook และ VPS · `Use AI Relay` เป็นทางเลือกเมื่อเจ้าของเรียกใช้เท่านั้น · ห้ามพึ่งความจำ AI และห้ามเขียนบน canonical repo ที่ใช้ร่วมกัน

## สถานะเฟส

| เฟส | เป้าหมาย | สถานะ | หลักฐาน |
|---|---|---:|---|
| NCR-P0 | Worktree + tracker + baseline | 80% | WTL_READY · permit issued · baseline inspected |
| NCR-P1 | สัญญา New Chat/Worktree/Direct Write ความหมายเดียว | 0% | รอตรวจ |
| NCR-P2 | คำสั่งเปิดแชทที่สร้าง Worktree+สิทธิ์เขียนตรง | 0% | รอเขียน |
| NCR-P3 | ด่านก่อนเขียนกลาง | 0% | รอเขียน |
| NCR-P4 | สิทธิ์เจ้าของแบบจำกัดขอบเขต + resume ตลอดแชท | 0% | รอเขียน |
| NCR-P5 | ตัวติดตั้ง Notebook/VPS | 0% | รอเขียน |
| NCR-P6 | ตัวเชื่อม Claude/Codex/Cursor/Hermes | 0% | รอเขียน |
| NCR-P7 | รักษางานเดิม/ส่งต่อ | 0% | รอทดสอบ |
| NCR-P8 | ทดสอบเส้นทางปกติและเหตุการณ์เสีย 24/24 | 0% | รอทดสอบ |
| NCR-P9 | ติดตั้งจริง Notebook/VPS + คู่มือเจ้าของ | 0% | รอติดตั้ง |

## ปัญหาที่ต้องปิด

| รหัส | ปัญหา | เกณฑ์ผ่าน | สถานะ |
|---|---|---|---|
| NCR-I01 | Use New Chat เป็นเพียง prompt | คำสั่งกลางสร้าง task/worktree/session จริง | open |
| NCR-I02 | fixed workspace ขัดกับ WTL | ไม่มีข้อความขัดกันใน source/payload | open |
| NCR-I03 | New Chat, WTL และด่านเขียนอ่านคนละ state | ใช้สมุดทะเบียนและ permit ชุดเดียวกัน | open |
| NCR-I04 | ด่านใช้รายชื่อนามสกุลจน `.html` หลุด | คุมทุกการเขียนตาม role/path | open |
| NCR-I05 | แอปปัจจุบันถูกบังคับให้ส่งงานผ่าน Relay | เขียนตรงได้เมื่อ task/branch/path/permit ตรง | open |
| NCR-I06 | canonical repo เขียนได้ | prewrite gate block ก่อนแตะไฟล์ | open |
| NCR-I07 | installer หยุดก่อน Relay และไม่มี WTL | clean-home install ผ่าน | open |
| NCR-I08 | Vault/payload/version ไม่ตรง | parity + version check ผ่าน | open |
| NCR-I09 | Portal credential ขาดแล้วงานตรงถูกขวาง | Portal/Relay ล่มไม่ขวางงานตรงของแอปปัจจุบัน | open |
| NCR-I10 | VPS `.env` permission/format ผิด | mode 600 + รูปแบบถูก + rotate ค่าเสี่ยง | open |
| NCR-I11 | เปิดแชท/ย่อแชทแล้ว state หาย | status จาก state กลางกลับมาได้ | open |
| NCR-I12 | ไม่มีการพิสูจน์ข้าม Notebook/VPS | full flow + handoff + bad fixtures ผ่าน | open |

## หลักฐานบังคับก่อนปิด

- functional flow 8/8
- bad fixtures 12/12
- client surfaces 4/4
- clean-home installer 1/1
- Notebook owner 1/1
- VPS 1/1
- registered team machines: ทุกเครื่องที่ลงทะเบียนต้องมี receipt; เครื่องที่ยังไม่ลงทะเบียนห้ามนับว่าพร้อม
- secret scan 0 finding ใน diff
- localhost/VPS closeout ระบุชัด

## ข้อห้าม

- ห้ามแตะ Project ลูกค้า
- ห้ามลบหรือย้าย Worktree เดิม
- ห้ามเดา staff/task/project route
- ห้าม claim พร้อมใช้จาก prompt หรือ file presence อย่างเดียว
- ห้าม push/merge/deploy ก่อนผ่าน phase gate และเจ้าของอนุมัติ
