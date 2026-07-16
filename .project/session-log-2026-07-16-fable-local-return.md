# Session Log — 2026-07-16 · Fable 5 กลับเข้า Use AI Relay เฉพาะโน้ตบุ๊กเจ้าของ (แชท Opus)

> memory-schema: v1.2 · งานจร (--no-plan · นอกแผน QAQC/MW) · worktree `task/nat/relay-fable-guard` · เจ้าของเปิด worktree ให้เอง (ด่านห้าม AI สร้าง)

## เป้าหมายรอบนี้

เจ้าของสั่ง: ใส่ Fable กลับเข้า Use AI Relay แต่ให้ใช้ได้เฉพาะโน้ตบุ๊กเจ้าของเครื่องเดียว — พนักงาน/VPS เรียกไม่ได้ · เลือกแบบ "2 ชั้น กันแน่นถาวร"

## ผลงาน (ทุกข้อมีหลักฐาน)

| งาน | สถานะ | หลักฐาน |
|---|---|---|
| ชั้น 1: adapter fable + ป้ายบัญชี (config เครื่องเจ้าของ) | verified | `.hermes/ai-relay/adapters.yaml` + `accounts.yaml` · `git check-ignore` ยืนยันไม่เข้า git · ยิงจริงผ่าน |
| ชั้น 2: host guard ใน relay-call.py | verified | PR #54 → main `a94f36ba8` · เทสต์ 7 เคส · เครื่องไม่มีไฟล์อนุญาต = `not_allowed` exit 10 |
| แก้ crash รันซ้อน (ตัด env CLAUDECODE ให้ลูก claude) | verified | PR #55 → main `58c59ba91` · เทสต์ดัก env 1 เคส · ชุดรวม **98/98 เขียว** |
| ยิงจริงทั้งสาย | verified | `relay-call --tool fable` → `status: ok` · ป้ายรุ่นระบบ (`--output-format json` → modelUsage) = `claude-fable-5` · ledger จริง |
| ผู้ตรวจต่างค่าย | claimed บางส่วน | ollama (สายสำรอง) ให้ PASS — คุณภาพต่ำกว่าค่ายหลัก · hardening: Codex ตรวจซ้ำ |

## Changed-files

| file | เข้า git? | เปลี่ยนโดย | เหตุผล | verification | next_owner |
|---|---|---|---|---|---|
| `scripts/ai-relay/relay-call.py` | ✅ #54+#55 merged | Claude (ข้อยกเว้นไก่-ไข่ — relay เรียก coder portal ไม่ได้บนเครื่องนี้ + แก้ relay เอง) | host guard + ตัด CLAUDECODE | verified (pytest 98/98 + e2e) | — |
| `scripts/ai-relay/tests/test_fable_host_guard.py` | ✅ merged | Claude | เทสต์ 8 เคส | verified | — |
| `.hermes/ai-relay/adapters.yaml` / `accounts.yaml` | ❌ ตามออกแบบ (machine-local) | Claude | adapter fable ผ่าน Subscription | verified e2e | — |
| `~/.hermes/.fable-allowed` | ❌ (นอก repo) | รอบงานนี้ | ไฟล์อนุญาตเครื่องเจ้าของ | มีจริง (ls) | เจ้าของเก็บไว้ ห้ามแจก |

## Decision log

- **DEC-FBL-001** (ดู decisions.md): fable เฉพาะเครื่องเจ้าของ · เครื่องเจ้าของ = Subscription ไม่ใช่ Portal · ลูก claude ต้องถูกตัด env CLAUDECODE
- ทำไม Claude เขียนเองแทน coder ต่างค่าย: coder ผ่าน relay ติดทั้งหมดบนเครื่องนี้ ณ ตอนนั้น (grok/codex ถูกดันเข้า portal ที่เครื่องนี้ไม่มี token · gemini crash) — เข้าข้อยกเว้นไก่-ไข่แบบเดียวกับ QAQC-P2-I4 · ชดเชยด้วยเทสต์จริง + reviewer สำรอง + จด hardening

## Quality gate ที่รัน

- `pytest scripts/ai-relay/tests/ -q` (ฐาน main ล่าสุดหลัง rebase) → **98 passed in 3.42s** (แปะผลในแชทแล้ว)
- หมายเหตุ: ชุดเทสต์เต็ม repo ยังแดง 683 เคส (ปัญหาเดิมก่อนงานนี้ — งานซ่อมแยกรอบ ดู OverviewProgress)

## Deploy

- N/A — repo นี้ไม่มี CI auto-deploy บน GitHub (`gh run list` ว่าง) · VPS ดึงโค้ดเองตามรอบ

## งานค้าง + เจ้าของถัดไป

1. ตัว `relay-call` กลางใน PATH ยังชี้โฟลเดอร์หลัก (ค้าง branch `fix/mw-flow-station-gate` ของแชทอื่น) — ได้ด่านใหม่อัตโนมัติเมื่อโฟลเดอร์หลักกลับ main + pull · เจ้าของถัดไป: แชทที่ถือโฟลเดอร์หลัก
2. Codex ตรวจซ้ำ diff #54+#55 (hardening ไม่บล็อก) · เจ้าของถัดไป: แชทหน้าที่โควต้า/ทางเรียก Codex พร้อม
3. worktree `relay-fable-guard` ใช้จบ สะอาด — รอบเก็บกวาด WTL

## ความเสี่ยงที่เหลือ

- ollama เป็นผู้ตรวจเดียวที่รอบนี้เรียกได้ → คุณภาพรีวิวต่ำกว่าค่ายหลัก (ชดด้วยเทสต์จริง 98/98 + e2e)
- ไฟล์อนุญาต `~/.hermes/.fable-allowed` คือกุญแจชั้นเดียวต่อเครื่อง — ถ้าเผลอแจก/ก๊อปไปเครื่องอื่น ชั้น 2 จะปล่อยเครื่องนั้น (ตั้งใจออกแบบให้เจ้าของคุมเอง)

## ข้อความเปิดแชทหน้า (ก๊อปวางได้)

```
Use New Chat
งานต่อจาก session-log-2026-07-16-fable-local-return: fable ใช้ได้แล้วบนเครื่องเจ้าของ (#54+#55 merged) ·
เช็คว่าโฟลเดอร์หลักกลับ main หรือยัง (ถ้ากลับแล้ว ตัว relay-call กลางได้ด่านใหม่อัตโนมัติ — ยืนยันด้วย
grep CLAUDECODE scripts/ai-relay/relay-call.py ในโฟลเดอร์หลัก) · งานเสริม: ให้ Codex ตรวจซ้ำ diff #54+#55
```
