> memory-schema: v1.2

# Session Log — ซ่อม Shortcut กลางและตรวจแผนทั้งหมด

## เป้าหมายรอบนี้

ซ่อม Shortcut กลางไม่ให้สร้าง/สลับ Worktree หรือกิ่งเอง ไม่ผลักการกู้พื้นที่กลับให้เจ้าของ และไม่ถามอนุมัติซ้ำระหว่างเฟสที่ยังมีงานปลอดภัย จากนั้นติดตั้งบนเครื่องจริง ตรวจ `.project` ทุกแผน และบันทึก Git

## สถานะงานซ่อม Shortcut

| เฟส | ผล | % | หลักฐาน |
|---|---|---:|---|
| 1. ตรึงนโยบายพื้นที่ปัจจุบัน | verified | 100% | Shortcut ใช้ Git root ปัจจุบัน · AI Relay เป็นทางเลือก · ห้ามเปิด Worktree เอง |
| 2. กู้ detached HEAD และกันคำตอบโยนงานให้เจ้าของ | verified | 100% | `hermes-current-workspace-recover` + `enforce-workspace-response.py` |
| 3. ต่อสาย Codex/Claude Code/Cursor/Hermes | verified | 100% | doctor `workspace_response` 4/4 · `current_workspace_prewrite` 23/23 |
| 4. ห้ามถามอนุมัติซ้ำกลางเฟส | verified | 100% | `phase_autonomy` 4/4 · ข้อยกเว้นภายนอกต้องมีรหัส+หลักฐาน |
| 5. ส่งกิ่งเข้า main แล้วกระจาย VPS/ทีม | pending | 0% | รอบนี้อยู่กิ่งงานและติดตั้ง Mac แล้ว · ยังไม่ merge main/ตรวจ VPS/เครื่องพนักงาน |
| **รวม** | **ทำแล้ว 4/5 เฟส** | **80%** | ชุดติดตั้ง Mac รุ่น `2026.07.19-2` ผ่าน 33/33 |

## ตรวจแผนทั้งหมดใน `.project`

เปอร์เซ็นต์ด้านล่างนับจากงานย่อยที่มีหลักฐานหรือสถานะปิดล่าสุดบน `origin/main` และพื้นที่งาน SPEC จริง งานที่มีเนื้อหาแต่ยังรอการรับรองจะแยกหมายเหตุไว้ ไม่ยกเป็นปิดแผน

| แผน | เฟส | ความคืบหน้า | สิ่งที่เหลือ |
|---|---|---:|---|
| BRM | P1 100% · P2 100% · P3 100% · P4 50% · P5 100% | 12/13 = 92.3% | P4-I2 การรวม upstream ใหญ่ต้องทำเป็นงานแยก |
| QAQC | P1 100% งานเนื้อหาแต่รอรับรอง · P2 75% · P3 66.7% · P4 100% · P5 0% | 12/16 = 75.0% | รับรองข้ามค่ายที่ยังขาด และนำร่อง RSF+Root Admin 0/2 |
| MW | P1-P6 ปิดแล้ว | 20/20 = 100% | เหลือการใช้งานรายโปรเจกต์ ไม่ใช่งานสร้าง Shortcut กลาง |
| DSU | P1 100% · P2 100% · P3 100% · P4 75% · P5 0% | 14/16 = 87.5% | เดิน pilot P4-I3 และติดตั้งบนเครื่องพนักงาน P5 |
| SPEC | P5 100% · P6 25% · P7 0% | 2/7 = 28.6% | I1 มี commit+pytest 83/83 แล้ว · ทำ I2-I4 และ P7 ต่อ |
| UAG | P1-P5 100% · P0 แยกค้าง | แกน Agent Center 13/13 = 100% · รวม P0 = 13/14 = 92.9% | P0 ต้องคงเพดานและซ่อมการนับ ไม่ใช้แนวถอดเพดานทั้งหมด |
| WTL | P0-P6 | 71/71 = 100% | เก็บเป็นมาตรฐานอ้างอิง · ห้ามใช้ Shortcut เปิด Worktree ใหม่ |
| GRD | P1-P4 ปิดและเก็บประวัติ | 4/4 = 100% | คิว P5-P9 ยัง 0% และต้องย้ายกลับแผน active ก่อนเริ่ม |
| JARVIS v2 | P0 0% · P1 50% · P2-P7 0% | 1/28 = 3.6% | เจ้าของทดสอบเสียง P0 ก่อน แล้วปิด P1 และเดิน P2-P7 |

### ปัญหาโครงแผนที่พบ

1. `.project/plan.md` ใส่ 6 แผนต่อกัน (BRM/QAQC/MW/DSU/SPEC/UAG) แต่ตัวอ่านแผนอ่าน `plan_id` แรกเพียงตัวเดียว จึงมีโอกาสส่งงานผิดแผน
2. สถานะในหัวข้อบางแถวล้าหลังกว่าหลักฐานบน `origin/main` เช่น BRM-P5, DSU F-04/F-05 และ SPEC-P6-I1
3. งานซ่อม Shortcut รอบนี้ไม่มีรหัสแผนใน `plan.md` ทำให้ประวัติอยู่ใน Git/แชตมากกว่าแผนกลาง
4. ลำดับอ่านบน Overview ยังเรียก WTL ว่า active ทั้งที่นโยบายล่าสุดให้ Worktree เป็นเครื่องมือที่เจ้าของเรียกเอง

ทางแก้รอบถัดไปคือทำดัชนีแผนกลาง 1 ไฟล์ แล้วแยกแต่ละ plan_id เป็นไฟล์ของตัวเอง โดยมี active plan เพียงหนึ่งตัวและคำนวณเปอร์เซ็นต์จากหลักฐานล่าสุด

## Changed-files

| file | owner | changed_by | reason | verification | risk | next_owner |
|---|---|---|---|---|---|---|
| `agent/shell_hooks.py`, `hermes_cli/hooks.py` | Hermes core | Codex | รองรับผลแปลงคำตอบจาก Hook | verified · targeted tests | ต่ำ | reviewer/main |
| `scripts/new-chat/hermes_prewrite_gate.py`, `hermes_workspace_recover.py` | Shortcut runtime | Codex | กู้ detached HEAD ใน Git root เดิมและห้ามสร้างพื้นที่ใหม่ | verified · 23/23 | กลาง | reviewer/main |
| `team-shortcuts/hooks/*.py` | Team hooks | Codex | กันโยนการเปิดพื้นที่ให้เจ้าของและกันถามซ้ำกลางเฟส | verified · 4/4+4/4 | กลาง | reviewer/main |
| `team-shortcuts/install-*.py`, `install-*.sh`, `check-shortcuts.sh`, `VERSION` | Team installer | Codex | ติดตั้งพฤติกรรมเดียวกัน 4 โปรแกรม | verified · installer PASS 33/33 | กลาง | VPS/team rollout |
| `team-shortcuts/payload/**`, `shortcut-manual.html` | Shortcut docs | Codex | นโยบายพื้นที่ปัจจุบัน + Phase Autonomy | verified · distribution tests | ต่ำ | main |
| `scripts/hermes_hook_doctor.py`, `scripts/mw/mw-setup.sh` | Health checks | Codex | ตรวจ 6 ด่านและลองตรวจซ้ำเมื่อโปรเซสถูกหยุด | verified · doctor 6/6 · MW 7/7 | ต่ำ | main |
| `tests/**` ที่เกี่ยวกับงาน | Tests | Codex | กันปัญหาเดิมกลับมา | verified · 181/181 ก่อนรวมฐาน · 145/145 หลังรวมฐานกลุ่มที่ชน | ต่ำ | CI |

## Decision Log

- ใช้ `CURRENT_WORKSPACE_ONLY` เป็นค่ากลาง; Shortcut ไม่มีสิทธิ์สร้างหรือสลับ Worktree/กิ่ง
- กู้ได้เฉพาะ detached HEAD จากกิ่งที่ลงทะเบียนตรง Git root และ SHA เดิม
- หลังอนุมัติเป้าหมาย/เฟส งานปลอดภัยมีงบคำถาม 0 ครั้งจนปิดเฟส
- ข้อยกเว้นที่ต้องถามเจ้าของต้องใช้ `OWNER_INPUT_REQUIRED` พร้อมรหัสและหลักฐานจากเครื่อง
- ไม่ลบ Worktree หรือไฟล์ค้างใดในรอบนี้

## Quality Gate

- targeted pytest ก่อนรวมฐาน: 181/181 ผ่าน
- หลังรวม `origin/main`: กลุ่ม Shortcut/New Chat/installer 145/145 ผ่าน; ชุดแก้ conflict ซ้ำ 48/48 ผ่าน
- `ruff check`: ผ่าน
- `git diff --check`: ผ่าน
- ติดตั้งจริง Mac: Shortcut 33/33 · Hook 6/6 · MW 7/7
- doctor: plain language/independent review/evidence 3/3 · workspace 4/4 · phase autonomy 4/4 · prewrite 23/23
- ชุดทดสอบทั้ง repo เคยมีความล้มเหลวเดิมจำนวนมากและรอบนี้ไม่ได้รันจนจบ จึงไม่อ้างว่าทั้ง repo ผ่าน

## Deploy

N/A — ยังไม่ merge เข้า `main` และยังไม่กระจายรุ่นนี้ไป VPS/เครื่องพนักงาน

## งานค้างและความเสี่ยง

- ส่งกิ่งงานขึ้น remote และเปิด PR หลัง Save Git ผ่าน
- merge เข้า `main` โดยเจ้าของ แล้วติดตั้งเฉพาะโฟลเดอร์กลางบน VPS และเครื่องทีม
- ทำแผนกลางใหม่เพื่อแยก 6 plan_id ออกจากไฟล์เดียว และอัปสถานะเก่าที่ไม่ตรงของจริง
- SPEC-P6 ในอีกพื้นที่มีไฟล์ค้างนอก commit; ห้ามแตะจากงานนี้

## ข้อความเปิดแชทหน้า

```text
Use New Chat
Use Continue

ทำงานต่อจาก .project/session-log-2026-07-19-shortcut-central-close.md
เป้าหมายเดียว: ปิดงาน Shortcut กลางรุ่น 2026.07.19-2 ให้ถึง main แล้วกระจาย VPS/เครื่องทีม พร้อมทำสถานะแผนกลางให้ตรงของจริง

กติกา:
- ใช้ workspace และกิ่งที่เปิดอยู่เท่านั้น ห้ามสร้าง/สลับ Worktree หรือกิ่ง
- ไม่ใช้ AI Relay เว้นแต่ผมสั่งตรง
- งานปลอดภัยในเฟสเดิมทำต่อจนจบ ห้ามถามอนุมัติซ้ำ
- ห้ามลบ Worktree ห้าม reset ห้ามทิ้งไฟล์ค้างของงานอื่น

หลักฐานตั้งต้น:
- รุ่น 2026.07.19-2 ติดตั้ง Mac ผ่าน Shortcut 33/33, Hook 6/6, MW 7/7
- doctor: workspace 4/4, phase autonomy 4/4, current workspace 23/23
- pytest ก่อนรวมฐาน 181/181; หลังรวมฐานกลุ่มที่เกี่ยว 145/145

ทำต่อเป็นเฟสใหญ่:
1. ตรวจ Save Git receipt และสถานะ PR/branch ล่าสุด
2. ส่งเข้า main ตามด่าน Git ที่เจ้าของอนุมัติ
3. ติดตั้งและตรวจ VPS + เครื่องทีมโดยไม่ยกทั้ง vault
4. แยกดัชนีแผนกลางออกจาก 6 plan_id และอัปเปอร์เซ็นต์จากหลักฐานจริง
5. ปิดด้วย Use Save Git + Use Close Chat ครั้งเดียว
```

## Evidence Footer

- timestamp: 2026-07-19 10:11:09 +0700
- host: `Rattanasaks-MacBook-Pro.local`
- cwd: `/Users/rattanasak/Documents/Worktrees/hermes-agent/nat/SHORTCUT-P1-I1-team-rollout-hardening-team-rollout-hardening`
- branch: `task/nat/SHORTCUT-P1-I1-team-rollout-hardening-team-rollout-hardening`
- code HEAD before close-memory commit: `c6e7fcf381c12f1c0ff824f26fe4c9651fe6091e`
- commands: pytest scoped, ruff, `git diff --check`, `install-shortcuts.sh --force`, `hermes-hook-doctor`, `git merge origin/main`
