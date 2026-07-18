---
task_id: UAG-P5
goal_id: UAG-P5-DIRECT-CODEX-20260718
status: pull_request_open_owner_merge_pending
owner_decision_at: 2026-07-19
writer: codex-current-chat
external_ai_relay: disabled
worktree: /Users/rattanasak/Documents/Worktrees/hermes-agent/nat/UAG-P1-I1-agent-center-foundation
branch: task/nat/UAG-P1-I1-agent-center-foundation
spec: .project/spec/UAG.md
---

# ใบล็อกเป้าหมาย — UAG-P5

## เป้าหมายแม่

สร้างศูนย์รวมทีม AI เฟสแรกใน Hermes Agent ตามสเปค UAG ที่เจ้าของอนุมัติ โดยคงขนาดแผนที่เดิม: หัวหน้าทีม 9 ตัว + ผู้เชี่ยวชาญ 37 ตัว = Agent เชิงตรรกะ 46 ตัว, ทักษะเริ่มต้น 52 รายการ และเครื่องมือ 6 ตัว

## คำสั่งล่าสุดของเจ้าของ

- ยกเลิกการใช้ `Use AI Relay` สำหรับงานนี้
- ให้ Codex ในแชทนี้เป็นผู้เขียนโดยตรง
- ห้ามเรียก Opus, Grok หรือ AI Portal
- ถ้าติดปัญหาให้หยุดและแจ้งสาเหตุจริง ห้ามลองวน
- เจ้าของอนุมัติให้คัดเฉพาะ UAG-P1..P4 กับตัวด่าน แล้ว commit/push/เปิด PR โดยกัน UAG-P0 ออก เมื่อ 2026-07-18

## ขอบเขตที่เขียนได้

- `plugins/agent_center/**`
- `tests/plugins/test_agent_center.py`
- `scripts/ai-relay/gate-run.py`
- `scripts/ai-relay/relay-call.py`
- `scripts/ai-relay/tests/test_gate_run_scoped.py`
- `.savegit.json`
- `skills/agent-center/**`
- `team-shortcuts/payload/ai-context/prompt-shortcut-registry.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/SKILL.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/Prompt Shortcuts.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-agent.md`
- `.project/active-task.md`
- `.project/plan.md`
- `.project/spec/UAG.md`
- `.project/ledger/**`
- `.project/gate-output/**`
- `/Users/rattanasak/ObsidianVault/HermesAgent/99-System/scripts/save_git_gate.py` และไฟล์ทดสอบคู่กัน ตามคำอนุมัติขยายขอบเขต 2026-07-19

## ขอบเขตที่ห้ามแตะในงานนี้

- แกน Hermes เช่น `run_agent.py`, `cli.py`, `gateway/**`, `model_tools.py`, `toolsets.py`
- หน้าจอและงานออกแบบภาพ
- AI Portal และกุญแจของผู้ให้บริการ AI
- คลัง Obsidian และความรู้ถาวร
- `hermes_cli/worktree_lifecycle.py` และ `tests/hermes_cli/test_worktree_lifecycle.py` ซึ่งเป็นงาน UAG-P0 แยกต่างหาก แม้มีการแก้ค้างอยู่ในพื้นที่นี้

## เกณฑ์ตรวจผ่าน UAG-P2

- Agent เชิงตรรกะ 46/46
- ทักษะเริ่มต้น 52/52
- เครื่องมือ 6/6
- นโยบาย `THINK_PAIR` และ `BUILD_REVIEW` มีการทดสอบ
- กติกา 4 ที่นั่งมีการทดสอบ
- การทดสอบเฉพาะ Agent Center ผ่านทั้งหมด
- ไม่มีไฟล์แกน Hermes เพิ่มในผลต่างของงาน UAG-P2

## สถานะความน่าเชื่อถือ

- Codex เป็นผู้เขียนและตรวจเบื้องต้นในแชทเดียวตามคำสั่งล่าสุด
- ผลทดสอบจากเครื่องเป็นหลักฐานหลัก
- รอบนี้ไม่มีผู้ตรวจ AI คนละตัว จึงห้ามอ้างว่าผ่านกฎ 2 สมอง

## ขั้นตอนถัดไปเพียงหนึ่งขั้น

เจ้าของตรวจและ merge PR #71 เมื่อเห็นสมควร

## จุดติดที่เคลียร์แล้วใน UAG-P3

- เคลียร์เมื่อ 2026-07-18: แอปเปิด Git root และ branch ของ UAG โดยตรงแล้ว
- เคลียร์เมื่อ 2026-07-18: กติกา `Use Continue` v5.0 ใช้ `CURRENT_WORKSPACE_ONLY` จึงไม่ต้องพึ่งสิทธิ์ Worktree สำหรับงานเขียนปกติ
- เคลียร์เมื่อ 2026-07-18: สร้าง Skill ผ่านเครื่องมือมาตรฐานในพื้นที่งานนี้ได้ 1/1 ครั้ง
- เคลียร์เมื่อ 2026-07-18: เจ้าของเปิดพื้นที่งาน UAG นี้ใน Codex แล้ว จึงไม่ต้องควบคุมแอปจากภายนอก

## ผลการซ่อมด่าน

- เจ้าของอนุมัติขยายขอบเขตให้ซ่อม `gate-run` เมื่อ 2026-07-18
- รับ `--test-path` ซ้ำได้และส่งเฉพาะพาธที่ระบุให้ pytest
- ตรวจไม่ให้ test path หนีออกนอก Git root ก่อนเริ่มคำสั่ง
- เขียนสมุดหลักฐานลง `.project/ledger/` และผลคำสั่งลง `.project/gate-output/`
- ด่าน UAG-P2 และ UAG-P3 ผ่าน 2/2 แถวด้วย exit 0
- สำเนา `gate-run` ที่ติดตั้งนอก Git root ไม่ถูกแก้ รอบนี้เรียกไฟล์ในพื้นที่งานโดยตรง

## ผลด่าน Git

- สร้าง commit เนื้องาน UAG สำเร็จที่ `be72f338f` โดยกัน UAG-P0 ออก 2/2 ไฟล์
- แก้ `relay-call.py` ให้รองรับ Python 3.9 และเพิ่มรายการไฟล์ค้างที่อนุมัติใน `.savegit.json` ที่ commit `1064068aa`
- ด่านกลางรองรับรายการไฟล์ค้างเฉพาะเมื่อเปิด `SAVE_GIT_ALLOW_DIRTY=1`; ไม่เปิดกุญแจยังบล็อกตามเดิม · การทดสอบผ่าน 3/3
- `save-git --stage local --json` คืน `SAFE_TO_MERGE` ด้วย exit 0 และตรวจไฟล์ค้างที่อนุมัติ 2/2
- push กิ่งขึ้น `origin` สำเร็จ 1/1 และเปิด PR #71 สำเร็จ 1/1: https://github.com/rattanasak-ops/hermes-agent/pull/71

## แบบ UAG-P3 ที่ลงมือแล้ว

- สร้าง `skills/agent-center/SKILL.md` และ `skills/agent-center/agents/openai.yaml` ด้วยโครงมาตรฐาน Skill Creator
- ลำดับ `Use Agent`: อ่านบริบทโปรเจกต์ → เรียกเครื่องมือ Agent Center → คืนใบรายชื่อทีม + ซองสั่งงาน → ให้ Codex ปัจจุบันลงมือในพื้นที่ที่มีสิทธิ์ → ใช้ผลทดสอบจากเครื่องเป็นหลักฐาน
- ไม่ผูกการลงมือกับ AI Relay; ช่องทางผู้ลงมือยึดคำสั่งเจ้าของและเครื่องมือที่กำลังใช้อยู่
- เชื่อม payload ทีม 4 จุด: ทะเบียนกลางใน payload, `prompt-shortcuts/SKILL.md`, `Prompt Shortcuts.md`, และ `references/use-agent.md`
- เพิ่มการทดสอบความสอดคล้องของชื่อ Shortcut, ไฟล์ prompt และจำนวนรายการ
- ยังไม่เขียน Obsidian ถาวร; หลังโค้ดและการทดสอบผ่านจึงค่อยส่งเข้าคิวรีวิวตามสเปค

## หลักฐานล่าสุดจาก Codex ในแชทนี้

- Agent เชิงตรรกะ 46/46: หัวหน้าทีม 9/9 + ผู้เชี่ยวชาญ 37/37
- ทักษะเริ่มต้น 52/52 ใน 12/12 ตระกูล
- เครื่องมือ 6/6 ลงทะเบียนผ่านปลั๊กอิน
- การทดสอบเฉพาะ Agent Center ผ่าน 105/105 จากแถว gate-run `UAG-P2-I3`
- การทดสอบ Agent Center รวมกับ payload ของ shortcut ผ่าน 125/125
- การทดสอบตัวด่านกลางผ่าน 83/83
- การทดสอบเครื่องมือ AI Relay ทั้งโฟลเดอร์ผ่าน 102/102
- แถว gate-run `UAG-P3-I2` ผ่านรวม 208/208
- ตัวอย่างคำของานออกแบบเว็บและ Web Engine ได้ใบรายชื่อทีม ซองสั่งงาน และใบเสร็จงานผ่าน 2/2
- แถว gate-run `UAG-P4-I1` ผ่านชุด UAG 125/125 พร้อมคำสั่งที่ระบุพาธทดสอบครบ 2/2
- ตัวตรวจ Skill มาตรฐานผ่าน 1/1
- การตรวจรูปแบบโค้ดผ่านทั้งหมด
- การตรวจช่องว่างและอักขระผิดรูปในผลต่างไม่พบปัญหา
- พื้นที่งานยังมีไฟล์ UAG-P0 ปนอยู่ 2 ไฟล์; ห้ามรวมไฟล์คู่นั้นในงาน UAG-P2/P3
