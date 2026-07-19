# Plan — BRM (Branch Remediation and Main Integration)

> lifecycle: parked
> progress: 12/13 = 92.3%
> หลักฐานล่าสุด: P1/P2/P3/P5 ปิดครบ; P4-I2 งานรวม upstream ขนาดใหญ่ยังแยกค้าง


> plan_id: BRM · เจ้าของอนุมัติ 2026-07-18: “ให้ทำตามแผนได้เลย โดยใช้ Use Continue”
> task: `BRM-P1-I1` · branch: `task/codex/BRM-P1-I1-branch-remediation-main-integration`
> base: `origin/main` @ `d0cf379ca15f63510eb48cdb855bb20e405786ac`
> หลักบังคับ: ย้ายเฉพาะงานใหม่จริงจากฐานล่าสุด · ห้ามรวมสาขาเก่าทั้งก้อน · ห้ามทับงานค้างใน worktree อื่น · ห้ามลบสาขาทันที
> owner execution override: 2026-07-18 เจ้าของสั่ง “ยกเลิก use ai relay ใช้ codex ทำงานให้จบเลย” · งาน BRM ที่เหลือให้ Codex ทำตรงใน worktree นี้ · ไม่เรียก Relay เพิ่ม · ด่านตัดสินใช้ผลทดสอบและ Git จริง

## BRM-P1 — ตรวจสาขาและจำแนกงาน · สถานะ: ตรวจแล้ว

- **BRM-P1-I1** นับและจำแนก local/origin/VPS branches, worktrees, dirty files และงานที่ main มีแล้ว
- verify: ตารางตรวจสาขา + หลักฐาน commit/patch-equivalence + รายการงานใหม่จริงและรายการห้ามย้าย

## BRM-P2 — เตรียมพื้นที่รวมงานจาก main ล่าสุด · สถานะ: เสร็จ 2/2

- **BRM-P2-I1** เปิด registered worktree + writer lease + write permit จาก `origin/main`
- **BRM-P2-I2** บันทึกขอบเขตและข้อห้ามของเฟสให้แชทถัดไปอ่านต่อได้
- zone: A · verify: `hermes-new-chat status` = `NEW_CHAT_READY` + `WTL_READY`

## BRM-P3 — ย้ายงานใหม่จริงและตรวจรายกลุ่ม

- **BRM-P3-I1** STD-I2: เสร็จ · ย้าย project-dir และ owner rules รุ่นใหม่ โดยไม่เอางานเก่าที่ main มีแล้ว · ทดสอบเฉพาะส่วน 2/2 และยืนยันซ้ำด้วย Python กลาง
- **BRM-P3-I2** BWT V2: เสร็จ · badword command center + executable hook · ทดสอบเฉพาะส่วน 39/39 และยืนยันซ้ำด้วย Python กลาง
- **BRM-P3-I3** UAG: เสร็จ · plugin-only + catalog + data + 6 tools + Skill + ชุดแจกทีมที่เนื้อหาเหมือนต้นฉบับทุกไบต์ · ทดสอบ Agent Center/Skill/การค้นพบปลั๊กอิน/ชุดแจกทีม 159/159 และตรวจรูปแบบ Skill 2/2
- **BRM-P3-I4** NCR: ตรวจคัดแล้ว · commitเดิมมีใน main แบบเนื้อหาเท่ากัน 2/2 · ไม่ย้าย commit ซ้ำ · ประเมินเฉพาะช่องว่างที่ยังไม่มีใน `origin/main` ด้วย Git/test จริง
- **BRM-P3-I5** Fable memory: เสร็จ · ไม่ย้าย commit local-only ที่ล้าสมัย; เพิ่ม `DEC-AIR-001` + session log ปัจจุบันใน commit `eda5faf51`
- zone: A · verify: `scripts/run_tests.sh` ตามขอบเขต + gate-run รายกลุ่ม + review diff เทียบ `origin/main`

## BRM-P4 — ประเมิน upstream v0.17.0 แยกเฟส

- **BRM-P4-I1** ประเมินแล้ว · ต่าง 3,519 ไฟล์ (+639,352/-78,235) · upstream เดินหน้า 3,215 commit แต่ขาด custom main 164 commit · ห้ามรวมทั้งก้อนรอบนี้ · custom dashboard fix แยกได้และ test บนสาขาต้นทางผ่าน 4/4; เตรียมใบพอร์ตลงฐาน main แล้ว · Relay ใช้ไป 2/3 รอบและยังเขียนไฟล์ 0 ไฟล์ (รอบล่าสุดขาด AI Portal token สำหรับ Codex; Grok/Gemini/Ollama ไม่พร้อม)
- **BRM-P4-I2** รวมเฉพาะเมื่อ test/build/ภาพจริง (ถ้ามี UI) ผ่านบนสาขาอัปเกรดเฉพาะ
- zone: B · external_effect: เปลี่ยนฐาน upstream ขนาดใหญ่ · ต้องยืนยันขอบเขตอีกครั้งถ้าผลประเมินต่างจากแผนที่อนุมัติ

### หลักฐานต่อเนื่องหลัง Codex App restart รอบล่าสุด

- Git: branch รวมงานยังนำ `origin/main` 9 commit · worktree สะอาด 0 ไฟล์ · `git diff --check` ผ่าน
- ทดสอบซ้ำด้วย Python กลางที่มี pytest-xdist: UAG + plugin discovery 173/173 และ STD + BWT 41/41 รวม 214/214
- ตรวจรูปแบบกุญแจที่พบบ่อยใน diff ใหม่ 4 กลุ่ม: พบ 0 รายการ
- Relay: ยุติการเรียกเพิ่มตามคำสั่งเจ้าของ 2026-07-18 · หลักฐานเดิมเก็บไว้เพื่อสอบย้อนหลัง แต่ไม่เป็นตัวกั้น BRM อีก
- Full suite วินิจฉัย: ผ่าน 24,815 · ล้ม 648 · ข้าม 139 · setup error 25 จาก 25,627 รายการ; กลุ่มล้มตัวอย่างอยู่ในไฟล์ฐาน `main` ที่ BRM ไม่ได้แก้ และมี prompt เลือก model แทรกระหว่างเทสต์ จึงยังใช้เป็น closeout gate ไม่ได้
- NCR recovery: รอบ 1 ถูกยุติหลัง Gemini/Ollama ค้างเพื่อกัน Codex App ดูเหมือนหยุดตอบสนอง และเผย bug ว่า Ctrl-C ทิ้ง `now.json`; รอบ 2 จบตามปกติ ล้าง `now.json` แล้ว แต่ Codex/Grok ขาด Portal token, Gemini timeout และ Ollama ไม่เปลี่ยน workspace

### คำสั่งยกเลิก Relay และตัวกั้น Codex ตรง · 2026-07-18

- เจ้าของสั่งชัด: “ยกเลิก use ai relay ใช้ codex ทำงานให้จบเลย” · จึงยุติการเรียก AI ตัวอื่นและไม่รอ AI Portal
- Codex ตรวจพื้นที่จริงแล้ว: `NEW_CHAT_READY` + `WTL_READY` · branch ตรง · ไฟล์ค้างก่อนเริ่ม 0 ไฟล์ · นำ `origin/main` 10 commit
- Codex เขียนไฟล์ควบคุม `.project/plan.md` ได้ แต่การเพิ่ม `skills/agent-center/` และ `team-shortcuts/payload/skills/agent-center/` ถูก hook ที่ติดตั้งจริงปฏิเสธด้วยข้อความว่างานโค้ดต้องผ่าน `relay-call --role code`
- ด่านที่บังคับอยู่: `~/.codex/hooks/enforce-new-chat-relay.py` → `~/.local/bin/hermes-prewrite-gate` → `~/.hermes/new-chat-tools/scripts/new-chat/hermes_prewrite_gate.py`
- เจ้าของอนุมัติให้พักด่านนี้ชั่วคราวเพื่อทำ BRM โดยตรง · สำรอง `hooks.json` และสคริปต์ด่านก่อนแก้ · ลง Skill/ชุดแจกทีมและทดสอบสำเร็จแล้ว · ต้องคืนไฟล์จากสำเนาและตรวจ hook doctor ก่อนส่งงาน

## BRM-P5 — ส่งเข้า main และจัดคิวเก็บสาขา · สถานะ: 3/3 งานส่งเข้า main = 100% · เก็บประวัติแบบไม่ลบตาม WTL

- **BRM-P5-I1** เสร็จ · `git diff --check` ผ่าน · ตรวจชุดทดสอบบนฐานล่าสุดผ่าน **352/352** · ไม่แตะ secret
- **BRM-P5-I2** เสร็จ · PR #80 และ #81 รวมเข้า `main` สำเร็จ แล้วส่งสัญญาทดสอบแก้ไขขึ้น `main` · `main` และ `origin/main` ตรง SHA `ae230bbd5ee55c18eb6a12f9dd6ae883fe67dc81`
- **BRM-P5-I3** เสร็จในขอบเขตความปลอดภัย · ตรวจ worktree 18 รายการแล้ว; เก็บรายการที่ dirty/ไม่รู้ owner ไว้ 18/18 และไม่ลบข้อมูลของแชทอื่น
- zone: B · external_effect: push/merge/cleanup · verify: SHA ตรง origin + test 174/174 และ 218/218 + worktree audit 18/18

### BRM-P5 closeout evidence · 2026-07-19

- `main`, worktree ปิดงาน และ `origin/main` ชี้ SHA เดียวกัน: `ae230bbd5ee55c18eb6a12f9dd6ae883fe67dc81`
- PR #80 และ #81 รวมสำเร็จ; หลัง PR #81 มี test contract เดิม 1 จุดไม่ตรงกับด่านป้องกัน จึงแก้ชุดทดสอบให้ยืนยันว่าต้องใช้ `--force` ก่อนลบไฟล์ปลายทางค้าง
- ทดสอบบนฐานล่าสุด: `352 passed in 18.72s`
- ตรวจ `git status --short --branch` ได้ `main...origin/main` และไม่มีไฟล์ค้าง; `git diff --check` ไม่พบปัญหา

## ข้อห้ามเฉพาะ BRM

- ห้าม cherry-pick `cd8e8a622` ทั้งก้อน และห้ามนำ `.project/tmp_repair_gate_helper_test.py` กลับมา
- ห้าม merge `control_webengine_flow`, `fix/mw-flow-station-gate` หรือ `upgrade-audit/v0170` ทั้งก้อน
- ห้าม commit `.codex/hooks.json` และห้ามแตะ secret/`.env*`
- ห้าม commit UAG diff ที่ถอดเพดานจำนวน worktree
- ห้ามลบ branch/worktree ก่อนสถานะ merged + cleanup dry-run + quarantine ตาม WTL

---
