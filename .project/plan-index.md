> memory-schema: v1.2

# ดัชนีแผนกลาง — Hermes Agent

active_plan_id: SHORTCUT
updated_at: 2026-07-19

กติกา: หนึ่ง `plan_id` ต่อหนึ่งไฟล์ และมีสถานะ `active` เพียงแผนเดียว แผน `parked` เริ่มต่อได้เมื่อเจ้าของสั่ง แผน `historical` เก็บเป็นหลักฐานและไม่มีสิทธิ์เปลี่ยนนโยบายปัจจุบัน

| plan_id | file | lifecycle | progress | evidence |
|---|---|---|---:|---|
| SHORTCUT | `.project/plan.md` | active | 28/29 = 96.6% | PR #84/#85 เข้า main; Mac+VPS ผ่าน; รอ notebook ทีม |
| BRM | `.project/plans/BRM.md` | parked | 12/13 = 92.3% | P1/P2/P3/P5 ปิด; P4-I2 แยกค้าง |
| QAQC | `.project/plans/QAQC.md` | parked | 12/16 = 75.0% | รับรองข้ามค่ายและ pilot 0/2 ยังขาด |
| MW | `.project/plans/MW.md` | closed | 20/20 = 100% | P1-P6 ปิดครบ |
| DSU | `.project/plans/DSU.md` | parked | 14/16 = 87.5% | เหลือ pilot P4-I3 และเครื่องพนักงาน P5 |
| SPEC | `.project/plans/SPEC.md` | parked | 2/7 = 28.6% | P5 ปิด; P6-I1 ผ่าน 83/83; P6-I2..I4/P7 ค้าง |
| UAG | `.project/plans/UAG.md` | parked | 13/14 = 92.9% | แกน Agent Center 13/13; P0 แยกค้าง |
| WTL | `.project/plan-wtl.md` | historical | 71/71 = 100% | PR #39/#40 และ vault MR #2; นโยบายสร้าง Worktree ถูกแทนที่แล้ว |
| GRD | `.project/plan-grd.md` | historical | 4/4 = 100% | P1-P4 ปิด; คิว P5-P9 ยังไม่ active |
| jarvis-v2-phase-plan | `.project/FeatureSpec-jarvis-voice.md` | parked | 1/28 = 3.6% | P1 ทำได้ 1/2; P0/P2-P7 ยังไม่เริ่ม |

## งานถัดไปของแผน active

ติดตั้ง notebook ทีมตามบัญชีเครื่องจริงเมื่อมีช่องทางเข้าถึง แล้วบันทึกผลต่อเครื่อง ห้ามแก้ด้วยการสร้าง Worktree เพิ่ม
