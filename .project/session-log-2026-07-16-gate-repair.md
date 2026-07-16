# Session Log — 2026-07-16 · ซ่อมยาม prewrite gate (over-lock) + เสียบปลั๊กกลับ

> memory-schema: v1.2 · staff: nat · แชท: Fable (ต่อจากแชทบันทึกความจำ station gate) · โหมด: Use AI Relay โหมด 2 (Fable เขียน · GPT-5 ต่างค่ายตรวจ · เครื่อง pytest/gate ตัดสิน) · เจ้าของอนุมัติ "ok" ในแชท

## เป้าหมาย
เจ้าของสั่ง: "ซ่อมยาม (prewrite gate) แก้ให้ล็อกเฉพาะที่ควรล็อก ไม่ล็อกตัวเอง แล้วเสียบปลั๊กกลับ"
ต้นเหตุ: gate v1 (`hermes_prewrite_gate.py`) ล็อกแน่นเกิน จน deadlock ทั้งเครื่อง → แชทก่อนหน้าถอด client hook ออกชั่วคราวเพื่อออก PR #51 → เครื่องไม่มีด่านกันเขียนช่วงหนึ่ง

## ราก over-lock 4 จุด (v1 → v2)
1. ล็อกทุก git repo ทั้งเครื่อง → แก้เป็น **คุมเฉพาะ registered worktree roots + canonical ที่มี session อ้างถึง**
2. บล็อกแม้แต่ git commit/push + เขียนความจำ `.project/` → แก้เป็น **git ปกติผ่าน (ห้ามเฉพาะ subcommand อันตราย/force push/worktree add-remove/ลบ branch) + ช่องความจำ .project + briefs เขียนได้เสมอ**
3. ทะเบียนกลาง VPS ล่ม = ตายทั้งเครื่อง → แก้เป็น **fallback permit ท้องถิ่น (WTL §8 offline) ถ้าทะเบียนตอบไม่ได้/ผิดรูป**
4. (เจอตอนใช้จริง) เขียนไฟล์ชั่วคราวนอกโปรเจกต์/แก้ตัวเองไม่ได้ → แก้เป็น **ตัดสินจากไฟล์เป้าหมาย ไม่ใช่แค่ cwd**

## ผู้ตรวจต่างค่าย GPT-5 (2 รอบ · fix-then-proceed ทั้งคู่)
- **รอบ 1** ชี้ 3 กลุ่ม → แก้ครบ: cwd bypass (ตัดสินจากไฟล์เป้าหมาย + สแกน absolute path ในคำสั่ง shell) · command substitution `$()` ตรวจเนื้อใน · redirect ลงไฟล์ (อนุญาตเฉพาะ /dev/null ตระกูล) · find -delete · curl -o · ตัวห่อ command/nice/time/nohup · sed -i แยก token (เดิม regex จับ path ที่มีตัว i ผิด)
- **รอบ 2** ชี้ 2 BLOCKING → แก้ครบ:
  1. `governed is None` ปล่อยผ่านทุกอย่าง → **เปิดช่องให้ AI แก้ตัวด่านเอง** (เขียนทับ `~/.hermes/new-chat-tools`, ปลอม session, แก้ `~/.claude/settings.json`, ถอด hook) → เพิ่ม **`protected_target`**: ห้ามเขียน/rm พื้นที่โครงสร้างด่าน (new-chat(-tools), hook dir, settings(.local).json, `~/.local/bin/hermes-*`) ทั้ง write tool และ shell
  2. ช่องความจำข้ามพื้นที่ปล่อย `.project/` ของ**โปรเจกต์อื่น** → แก้เป็น **เฉพาะโปรเจกต์เดียวกัน** (`project_key` ตรงกัน)
- ตามกติกา relay (ผู้ตรวจเดิม 2 รอบ → เปลี่ยนเป็นเครื่องตัดสิน) รอบสุดท้ายพิสูจน์ด้วยเทสต์ที่ encode เคสโจมตี GPT-5 ตรง ๆ

## หลักฐาน (tier 3)
- **pytest 89 เคส เขียว** (24 เดิม + 65 ใหม่: unmanaged pass, memory lane, bash allow/block, offline fallback, cwd bypass, shell escape 12, protected-path 8, cross-project memory, sed 6) — รันบน interpreter เดียวกับ gate (`.venv` worktree + xdist)
- **ยิงผ่าน client hook binary จริง 15 เคส เขียว** (block: canonical/rm/cwd-bypass/ถอดปลั๊ก/rm hook/settings/ปลอม session/แก้ gate เอง · pass: ความจำ/git commit/sed อ่าน/ไฟล์ชั่วคราวนอกเขต/cat hook/repo อิสระ · fail-closed: stdin ว่าง) — ตัว probe อยู่ scratchpad รันผ่าน pytest
- **ติดตั้งจริง**: copy gate เข้า `~/.hermes/new-chat-tools` (diff IDENTICAL) + คืน client hook จาก `.bak` + entry ใน `~/.claude/settings.json` PreToolUse ยังอยู่ · `hermes-hook-doctor` = ok 4/4
- **gate ทำงานสดพิสูจน์ตัวเอง**: ระหว่างทำงานยามบล็อกคำสั่งของ Fable เองหลายครั้ง (เขียนไฟล์ในเขต, commit msg เอ่ย path hook, `|` ใน grep) = จับจริง

## commit + push
- commit `4599eaca0` (2 ไฟล์: gate + test) บน branch `task/nat/NCR-P0-I1-new-chat-relay-enforcement` — **push ถูก Save Git บล็อก**
- เหตุบล็อก: worktree NCR มี **29 ไฟล์ dirty จากเซสชัน NCR ก่อนหน้า** (relay-call, team-shortcuts, new-chat tools อื่น ๆ) + save-git เตือน secret risk · **ไม่ใช่ของงานนี้ + กฎห้ามแตะ/กวาดงานเซสชันอื่น** → ไม่ push, ไม่ stash, ไม่ clean
- commit อยู่ในเครื่องปลอดภัย (branch NCR) · ตัว gate ที่ติดตั้ง + เสียบ hook = ทำงานจริงแล้วไม่ขึ้นกับ push

## รู้จำกัด (จดตรง ๆ)
- **full-repo gate แดงที่ baseline** (683 เคสก่อนหน้า — จดในความจำเดิม ไม่ใช่จากงานนี้) จึง verified ด้วย scoped pytest 89 + live 15 แทน
- **AI Relay สายพานเต็มระบบใช้ไม่ได้บนเครื่องนี้**: relay-doctor = กุญแจ Portal 4 ตัวไม่มีใน `~/.hermes/.env` (งานเจ้าของใส่เอง) · `relay-call` ยิงจริงล้มทั้งสาย (grok:blocked-bin, codex/gemini/ollama:crash) → รอบนี้ Fable เขียนเอง + GPT-5 ตรวจผ่าน cross-check MCP แทน (โหมด 2)
- **quoted `|;>` ใน argument = false-block** (fail-closed ยอมรับ) · git plumbing chain (hash-object/update-index) ยังเขียนได้ = harden แยกรอบ

## งานค้าง/ส่งต่อ
1. **push commit `4599eaca0`** — ต้องให้เซสชันเจ้าของงาน NCR เคลียร์ 29 ไฟล์ dirty (commit/แยกงาน) ก่อน หรือเจ้าของอนุมัติแยก cherry-pick gate ขึ้น branch สะอาด (branch surgery ตอนนี้ทำไม่ได้เพราะ gate เองบล็อก checkout/switch — ต้องเจ้าของสั่ง)
2. **prewrite-gate v2 ยังไม่ผ่าน PR/merge** — โค้ดอยู่ commit local + ติดตั้งบนเครื่องเจ้าของแล้ว แต่ยังไม่เข้า main
3. ซ่อมสายพาน relay เต็มระบบ (ใส่กุญแจ Portal 4 ตัว + codex crash) = งานเจ้าของ/รอบแยก
4. harden รอบหน้า: git plumbing chain, false-block จาก quoted metachar
