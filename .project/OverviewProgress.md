> memory-schema: v1.2
> อ่านตามลำดับ: plan-wtl.md (plan_id: WTL — active · Worktree Lifecycle) → plan.md (plan_id: QAQC/MW) → plan-grd.md (แผน GRD จบแล้ว + คิว GRD-P5..P9) → decisions.md → hermes-standard/REQUIREMENTS.md (บัญชีความต้องการ 66 ข้อ)

# Overview & Progress — Hermes Agent
อัปเดตล่าสุด: 2026-07-18 (BRM รวมงานใหม่เข้า `main` แล้ว · closeout 146/146) · branch งานปัจจุบัน: `task/codex/BRM-P1-I1-branch-remediation-main-integration` · ป้าย: [fact] เว้นแต่ระบุ

## สถานะล่าสุด
- **2026-07-17 (ยามเขียนไฟล์ + ส่งต่อทีม): prewrite gate v2.2 เข้า main และสร้างกิ่ง `dev` จาก main ล่าสุด** [fact · PR #60]
  - บันทึกนี้ยืนยันว่าชุดยามและการส่งต่อทีมผ่าน PR #60 แล้ว พร้อมผลตรวจ doctor 4/4 ตามบันทึกรอบเดิม
  - ช่องแข็งแรงที่ยังต้องทำต่อ: ตรวจคำสั่ง `git -C <path> ...` ที่อาจหลบด่าน และดูแลกิ่ง `dev` ให้เดินตาม main
- **2026-07-16 (Fable): ปิดรอบการเรียก Fable เฉพาะเครื่องเจ้าของ** [fact · PR #54+#55 อยู่ใน main]
  - ชั้นป้องกันในโค้ดบังคับให้ Fable ใช้ได้เฉพาะเครื่องที่มีไฟล์อนุญาต และตัดตัวแปรแวดล้อมที่ทำให้เรียก Claude ซ้อนแล้วล้ม
  - หลักฐานจากรอบเดิม: relay-call ตอบ `status: ok` และชุดทดสอบที่เกี่ยวข้องผ่าน 98/98
  - ข้อจำกัด: เครื่องเจ้าของใช้ Claude Subscription ตรง ส่วนเครื่องพนักงาน/VPS ห้ามเรียก Fable
- **2026-07-18 (BRM-P5): รวมงานสาขาที่ตรวจแล้วกลับ `main` สำเร็จ** [fact]
  - ฐานล่าสุด `origin/main` ถูกผนวกใน commit `c076984d0` และ `main` เลื่อนแบบเดินหน้าอย่างเดียว · push สาขางานและ `main` ขึ้น `origin` สำเร็จที่ SHA `0bd4b03d1`
  - ชุดทดสอบเฉพาะงานหลังรวมฐานผ่าน **146/146** · `git diff --check` ผ่าน · worktree สะอาด
  - branch/worktree ยังเก็บไว้ในช่วงกัก 72 ชั่วโมงตามกฎ WTL; ยังไม่ลบสิ่งใด
- **2026-07-18 (BRM · ตรวจสาขา Fable/NCR): ล็อกกฎปัจจุบันว่า AI ทุกตัวผ่าน AI Portal; ไม่รวม commit ความจำ Fable local-only และไม่ย้าย local fallback จาก NCR** [fact · `DEC-AIR-001` · รายละเอียด `session-log-2026-07-18-ai-portal-routing.md`]
  - งานใหม่จริงจาก NCR ที่รอเขียน: ต่ออายุ lease อย่างตรวจตัวตนครบ · status กัน permit หมดอายุ · Relay ต้องเห็นไฟล์เปลี่ยนและคำตัดสินรีวิว · cleanup ตอนยกเลิก
  - ตัวกั้นปัจจุบัน: Codex DNS ล้ม · Grok ไหลไป CLI ผิดตัว · Gemini รอ login · Ollama exit 1 → UAG Skill ยังไม่ถูกเขียนและห้ามนับว่าจบ
- **2026-07-17 (แชท Opus · SPEC-CENTRAL P5): สเปคกลางต่อสายเข้าคำสั่งกลาง 6 ตัว — branch `task/nat/SPEC-P5-I1-central-prompts-sync` push แล้ว · Save Git = SAFE_TO_MERGE · รอเจ้าของกด merge** [fact]
  - **ทำอะไร**: PR #57 (สเปคกลางพื้นฐาน `_TEMPLATE.md` + `plan-anchor read_spec`) เจ้าของ merge แล้ว → ต่อด้วยแก้คำสั่งกลาง 6 ตัว + ทะเบียน ให้รู้จักสเปคแบบ **capability-based** (โปรเจกต์ไม่มีสเปค = เดินเหมือนเดิม 100% · ไม่พัง version lock)
  - **ไฟล์ (2 สำเนา ตรงกันทุกไบต์ · diff 7/7 สะอาด)**: memory-schema §1d (กติกากลาง: จับคู่สเปคด้วยชื่อไฟล์ · draft ห้ามโค้ด · approved/building ทำได้ · done ห้ามพฤติกรรมใหม่ · **owner_approved เจ้าของพิมพ์เองเท่านั้น + จดหลักฐาน**) · Act-As v3.2 · New Chat v2.9 · Comply v3.3 · Close Chat v2.5 · Save Git v2.3
  - **คุณภาพ**: รีวิวต่างค่าย GPT ก่อนลงมือ (fix-then-proceed → ปิด 3/3: กัน AI ติ๊กอนุมัติเอง/จับคู่ชื่อไฟล์กัน false-block/done แคบ) · coder=grok ผ่าน relay (codex rotate) โหมด 2 · pytest payload 8 เขียว
  - **⚠️ ยังไม่ทำ (สำคัญ)**: **S1 (SPEC-P6) = ตัวบังคับจริงระดับโค้ด ยังไม่เริ่ม** — ตอนนี้สเปคเป็นแค่ด่านระดับคำสั่ง AI (อ่านแล้วทำตาม) ยังปลอมได้ · แผน S1/S2 ยึดใน `plan.md` (SPEC-P6/P7) แล้ว
  - **เทส payload 2 ตัวแดง = ค้างก่อนงานนี้** (base use-new-chat 2.8 vs pin 2.7 · registry/SKILL count 32≠31) พิสูจน์แล้วไม่ใช่ของ SPEC → spawn task แยก
- **2026-07-17 (แชท Opus · DSU-P4): shortcut `Use Create Design System` อัปเป็น v3.1 — ปิดข้อบกพร่อง 3/5 ที่การนำร่อง Root Admin ตรวจพบ · PR #58 merged (`af3aa41db`)** [fact]
  - บัญชีข้อบกพร่องจากการนำร่อง = `.project/dsu-pilot-findings.md` (สิ่งส่งมอบหลักตาม Goal Lock `DEC-DSU-002`): F-01 ด่านตรวจสำเนามาตรฐาน · F-02 กฎกันกลืนเป้าหมายแม่ (`caller_goal` + บรรทัดประกาศสถานี + โหมด pilot) · F-03 ด่านสีจำแนกสีเดิม 3 แบบ — ปิดครบทั้งคลัง (commit `e133f00` · ผู้ตรวจ GPT-5 แก้ตาม 3/3) + payload ตรงคลัง 100% (แฮชตรง 2/2) · F-04 relay ตีผลผิดเมื่อ coder commit = ปักธง task chip (เจอซ้ำ 2 เคสจริง) · F-05 ด่านเครื่องบล็อก ds-gate = รอเจ้าของเคาะ
  - สนามนำร่อง Root Admin (newwebengine2026 · worktree `DSU-P4-I1`): ชั้นแบรนด์ H/U/F ผ่าน `ds-gate` 20/20 exit 0 + สำเนามาตรฐานในโปรเจกต์อัปเป็น v3.1 (commit `c669a7a4`) · ค้าง: เดิน PHASE 3-5 ด้วย prompt รุ่นใหม่ (DSU-P4-I3) + `DesignSystem.md` ของโปรเจกต์นั้นยังไม่เข้า git
  - เหตุการณ์: AI หลงเป้ารอบที่ 20 กลางแชท → สอบสวนพบ 3 ตัวการ (บทใน prompt กลืนเป้าหมาย/บันทึกเป้าไม่ชัด/แรงกด hook) → แก้ถาวรใน DEC-DSU-002 + กฎ F-02 ของ prompt · แผน DSU-P4/P5 อยู่ใน plan.md แล้ว
- **2026-07-16 (แชท Fable · ต่อจาก station gate): ซ่อมยาม prewrite gate over-lock (v1→v2.2) + เสียบปลั๊กกลับ — ล็อกเฉพาะเขตที่ควร ไม่ล็อกตัวเอง + กัน AI ถอด/ปลอมด่านเอง** [fact · รายละเอียดเต็ม `session-log-2026-07-16-gate-repair.md`]
  - ต้นเหตุ: gate v1 ล็อกแน่นเกินจน deadlock ทั้งเครื่อง → แชทก่อนถอด client hook ออกชั่วคราวเพื่อออก PR #51 → เครื่องไม่มีด่านช่วงหนึ่ง
  - แก้ over-lock 4 จุด: คุมเฉพาะ registered worktree+canonical ที่มี session · git ปกติ+ความจำ .project ผ่าน · ทะเบียนล่ม=permit ท้องถิ่น (WTL §8) · ตัดสินจากไฟล์เป้าหมายไม่ใช่แค่ cwd
  - GPT-5 ต่างค่าย 2 รอบ: รอบ1 ปิด cwd-bypass/shell-escape/redirect/find-delete/curl-o/sed-i · รอบ2 ปิด BLOCKING 2 จุด (protected_target กันแก้ hook/session/settings/เครื่องมือ = ถอดปลั๊กเองไม่ได้ · ความจำข้ามพื้นที่เฉพาะโปรเจกต์เดียวกัน)
  - หลักฐาน tier 3: pytest 89 เขียว + ยิง hook binary จริง 15 เคส (block/pass/fail-closed) เขียว + ติดตั้ง ~/.hermes + เสียบ hook + doctor 4/4 · **ยามพิสูจน์ตัวเองโดยบล็อกคำสั่ง Fable เองระหว่างทำงาน**
  - โหมด Use AI Relay ที่ใช้จริง = โหมด 2 (Fable เขียน · GPT-5 cross-check ตรวจ · เครื่อง pytest ตัดสิน) เพราะ **สายพาน relay เต็มระบบใช้ไม่ได้บนเครื่องนี้** (กุญแจ Portal 4 ตัวไม่มี + relay-call ล้มทั้งสาย)
  - ⚠️ ค้าง: commit `4599eaca0` (2 ไฟล์ gate+test บน branch NCR) **push ไม่ได้** — Save Git บล็อกเพราะ 29 ไฟล์ dirty ของเซสชัน NCR ก่อนหน้า + secret risk (ไม่ใช่ของงานนี้ ห้ามแตะ) · gate ที่ติดตั้ง+เสียบทำงานจริงแล้วไม่ขึ้นกับ push
- **2026-07-16 (แชทเช้า · PR #51 merged `f14cf6c09`): flow station gate — ด่านยืนยัน owner จากแชทจริง กัน AI ข้าม flow แบบปลอมไม่ได้** [fact · บันทึกย้อนหลัง — รายละเอียดเต็ม `session-log-2026-07-16-station-gate.md`]
  - ปัญหา 4 วันวน: AI ข้าม M0/M2/M3.5 แล้วสั่งสร้างงานเอง · ด่านเดิมพึ่งไฟล์ `.flow-state` ที่ AI เขียนเองได้ = ปลอม owner_ok ได้
  - แก้ (เจ้าของเลือกทาง ก): `enforce-flow-gate.py` อ่านคำอนุมัติจาก Claude Code transcript (append-only) · นับเฉพาะข้อความคน (`origin.kind=human`) · สถานี+คำอนุมัติติดกัน ≤200 ตัวอักษร · คุมเฉพาะพื้นที่ MW · fail-closed
  - คุณภาพ: Claude เขียนเอง (relay/codex crash ทั้งระบบ — งานซ่อมแยก) · GPT-5 ตรวจต่างค่ายชี้ 4 จุด (ปฏิเสธ/คำถาม · `--role review` · registry fallback) แก้ครบ · เทสต์ station gate 21 เคส · ทั้งชุด 335 passed
  - ข้อจำกัด v2: approval สะสมทั้งแชท ยังไม่ผูกรายเมนู · หลบได้ด้วย `codex --cwd` นอกพื้นที่/python เขียนตรง (guard-write คุมส่วนเขียนไฟล์)
  - ⚠️ ค้างเจ้าของเคาะ: **prewrite-gate (แชทอื่นสร้างวันเดียวกัน) deadlock ถูกถอดชั่วคราวเพื่อออก PR นี้** — ตรวจสด 16 ก.ค.: สคริปต์ `enforce-new-chat-relay.py` มีไฟล์แต่ไม่ผูกใน settings ทั้งสองไฟล์ = ไม่บังคับใช้จริง · แก้ scope แล้วผูกกลับ หรือถอดถาวร
- **2026-07-16 (แชท Fable · PR #49+#50 merged): ชุด `Use Migrate 0-13` — แตก flow 13 สถานีเป็นทางลัดรายเฟส เปิดใช้จริงครบทุกเครื่อง** [fact]
  - **ทำไม**: วิเคราะห์ root cause 2 รอบว่าทำไม AI ไม่ทำตาม `Use Migrate Web` — R1-R6 จากไฟล์ prompt จริง (เห็นคำสั่งทุกขั้นพร้อมกัน/กฎชนกันเอง/จุดหยุดเป็นร้อยแก้ว/โหลดเกิน) + R7-R11 จากตารางผลงานจริง (FW-P0 ถูกข้ามทั้งด่าน · % ไหลลง M1 90%→M5 5% hardcode · เอารีวิว AI แทนการรันด่าน)
  - **ของใหม่ในคลัง (GitLab `ef5b27d`)**: สัญญากลาง `use-migrate-phase-contract` v1.1 (โครง 5 ส่วน: ด่านเข้าตรวจไฟล์จริง/ประกาศสถานี/เนื้อเฉพาะเฟส/ถาม-ตอบบังคับ/ตารางจบเฟส 3 ชั้น + กฎเหล็ก R+G5 + `BLOCKED_TOOLING` เฟสด่านเครื่อง 9/10/11/13 + ไฟล์อนุมัติ `approvals.md` + **โควตาเมนู: ค่าเริ่มต้น 1 คน 1 เมนู · เกินได้เมื่อ owner อนุมัติ `quota:` ใน menu-queue · เฟสโค้ด 8-9 ทีละเมนูต่อพื้นที่เสมอ**) + ไฟล์เฟส 14 ตัว v1.0 + `use-migrate-web` v1.4 (ตัวนำทาง) + ทะเบียนอัปตรงกัน
  - **คุณภาพ**: ผู้ตรวจต่างค่าย Grok อ่านครบ 16 ไฟล์ พบ BLOCKING 6 → แก้ครบ 6/6 (Codex ค้าง MCP 2 รอบ สลับค่ายตามกติกา) · ทดสอบเจาะพฤติกรรม: AI สดเจอ `Use Migrate 5` ข้ามลำดับ → `MIGRATE_BLOCKED` ปฏิเสธถูกต้อง 2/2 · เครื่องตรวจโครง 5 ส่วน × 14 ไฟล์ = 70/70
  - **กระจายครบ**: Mac เจ้าของ (mw tools 7/7 + รอดหลังลบต้นทาง 7/7 + hook doctor 4/4) · **VPS ซิงก์แล้ว 17/17 ไฟล์** (rsync เฉพาะ `ai-context/`+`skills/prompt-shortcuts/` — พบว่ากระจกคลัง VPS เป็น**พื้นที่ทีมใช้ร่วม** มีไฟล์พนักงาน ห้ามยกทั้งโฟลเดอร์) · ทีม notebook: PR #50 merged → รัน installer 1 บรรทัดได้ของครบ
  - **กู้ภัย VPS**: กระจกคลัง VPS เป็นสมุด git คนละเล่ม (ตั้งต้นแยก 4 commit) มีงานค้างไม่เคยขึ้นระบบ — "rename `Use Save Git`→`Use Request Merge`" (เซสชัน AI 28 มิ.ย. เจ้าของไม่รู้จัก) → กู้ทั้งเล่ม+สแนปช็อตไฟล์ค้างขึ้น GitLab กิ่ง `vps-rescue-2026-07-16` (ถึง `6500484`) · **คำแนะนำที่เจ้าของรับ: ไม่รวมเข้า main** (ของรุ่นเก่า ระบบวิ่งเลยแล้ว)
  - **RSF เตรียมพร้อม**: ชุดพร้อมเคาะ `Use Migrate 0` ถอดจาก TOR จริง (MIGRATE · FORM เปิด/BILINGUAL ปิด · งวด 30%/70% ใน 30/90 วัน · ค่าปรับ 0.1%/วัน · WCAG 2.1 AA · gap มาตรฐานเคาะแล้ว DEC-155) — เจ้าของเหลือเคาะ 2 ข้อ: แทร็ก DATA/MINISITE + รายชื่อทีม + สั่ง `quota: nat=3` (จะทำ 3 เมนูขนาน 3 แชท)
  - **มาตรฐานเก็บไฟล์อัปโหลด (คำปรึกษา — เจ้าของรับแล้ว)**: โค้ดกลาง config-only ห้ามแก้รายไซต์ · ก้อนไฟล์ = `uploads/{siteId}/{หมวด}/` นอก git · mini-site = siteId ตัวเอง · โค้ดกลางแก้ที่ Root Admin (เจ้าของเปิดแชทแยก — ใบสั่งงานอยู่ใน session log) · RSF/DRA/CT ตามเก็บไฟล์เก่าตอนทำ
  - เหตุแทรกที่แก้แล้ว: เก็บ 2 ไฟล์ dirty ค้างจากรอบปิด 15 ก.ค. (hook doctor ด่าน 4 + write permit ssh) → PR #49 merged · กิ่งเก่า `close/mem-vps-verified` ซ้ำ main แล้ว ลบได้
- **2026-07-15 (แชท Fable · branch `task/nat/DSU-P1-I1-ds-standard-hardening`): แผน DSU — ยกมาตรฐาน Design System · **จบครบ + merged PR #48 + กระจาย VPS แล้ว (ปิดรอบ 2026-07-16)** [fact]
  - ราก 3 ข้อที่พิสูจน์แล้ว: (1) **version drift** — ทะเบียนบอก v2.5 แต่ไฟล์ prompt จริง 2 สำเนา = v2.4 (grep "ชั้น U/S1/92" = 0) ทุกโปรเจกต์เลยรัน flow เก่าข้ามชั้นแบรนด์ (2) ชั้น H/U/F เป็นตัวหนังสือ ไม่มีเครื่องบังคับ (3) ฝั่งแอดมินครอบคลุม ~15-25% เทียบ global
  - แก้ครบ: prompt → **v3.0** (2 สำเนา + คลัง commit `a8b8ff6`) · เช็กลิสต์ → **v3.1 = 109 หัวข้อ** (F7 Mood&Tone + D14-D17 ด่านวินัยงาน + B18-B20/C17 + ขยาย B2/B4/A18 + **Pack Admin-Pro 8 ข้อ** เทียบ Carbon/Polaris/Ant/Cloudscape/Atlassian ทุกข้อมีที่มา+วิธีตรวจ) · เครื่องตรวจใหม่ **`ds-gate.py`** (H/U/F ต้องผ่านก่อนด่านสี · fail-closed · pytest 5/5) · ทะเบียน registry อัปแล้ว (คลัง commit `faa8545`)
  - ผู้เขียน = Codex CLI ตรง (relay portal token ไม่มีบนเครื่องนี้ — ปักธงงานซ่อมแยกแล้ว) · ผู้ตรวจ = Grok/ต่างค่าย (P3) · commit ทีละชิ้น 5 ก้อน
  - ปิดรอบ: PR #48 merged `61e31af5b` · VPS mirror v3.0 ✓ + repo VPS ดึงแล้ว (เจ้าของยืนยัน) · เหลือ: push คลัง→GitLab (เจ้าของ) + พนักงานรัน installer · pilot ds-gate 1 โปรเจกต์
- **2026-07-15 (แชท Opus→Fable · merged main แล้ว 2 PR): `Use Migrate Web` พร้อมทีมใช้จริง — MW-P4 จบ + MW-P6 Flow Enforcement + เจ้าของทดสอบรับงานผ่าน 5/5 + ประกาศทีมส่งแล้ว** [fact]
  - **MW-P4 จบจริง**: `mw-backend-check` รันจริงกับ RSF site 78 บน VPS (อ่าน 3/3 PASS + negative 2/2 FAIL ถูกต้อง) + **วงจรฟอร์มจริง PASS** (`POST /api/v1/contact` 201 → DB → เทียบค่าตรง · **prefix API จริง = `/api/v1` ไม่ใช่ `/api`**) · ข้อมูลทดสอบ TEST-MW ลบเกลี้ยง (ตรวจซ้ำ = 0) · config ตัวอย่างอยู่ `/home/linux-nat/mw-p4/` บน VPS
  - **เหตุการณ์สำคัญ: AI (Opus) ข้าม flow เองกลางแชท** — เดา workflow 6 ขั้นแทนการเปิดไฟล์ flow13 → เจ้าของสั่ง "แก้ต้นเหตุ" → เกิด **MW-P6**
  - **MW-P6 Flow Enforcement (PR #42 merged)**: ตรวจพบ G5 5 ชั้นในเอกสารมีโค้ดจริงแค่ menu-gate ปลายทาง · สร้าง `flow_eval.py`+`flow-rules.yaml` (สถานะ 13 ขั้นคำนวณสดจากหลักฐาน ไม่มี state ไฟล์ให้ปลอม) + `flow_gate.py` CLI (status/can-enter/guard-write) + hook PreToolUse `enforce-flow-gate.py` (โปรเจกต์มี `.work/profile.yaml` = คุม Edit/Write/shell · fail-closed) + ผูก menu-gate `--menu` + mw-doctor · **Fable วิเคราะห์ · Codex ตรวจค้านดีไซน์ + เขียนโค้ด 3 ใบ (ledger MW-P6-I2/I3/I4) · Fable รีวิว+รันเทสต์เอง**
  - **team-ready (PR #43 merged)**: แก้เทสต์ payload 2 เคสแดง (เทสต์ตรึงรุ่นเก่า 2.6/4.4 — ไฟล์จริงเป็น 2.7/4.5 กลไก Worktree Manager) → **310 passed 0 failed** + ชุดทดสอบรับงาน `team-shortcuts/OWNER-ACCEPTANCE-MW.md` (5 ข้อ) — **เจ้าของกดเองผ่านครบ 5/5** + hook บนเครื่องเจ้าของอัปจากรุ่น MVP 13 ก.ค. (ไม่คุม Bash) เป็นรุ่นใหม่แล้ว (เจ้าของรัน installer เอง)
  - **ประกาศทีมส่งให้เจ้าของแล้ว**: ติดตั้ง 1 คำสั่ง (`curl ... install-from-github.sh | bash` — รวม hook + เครื่องมือ MW อัตโนมัติ) · ทำทีละ 1 เมนู จองคิวก่อน
  - **ติดตั้งบน VPS ยืนยันจริงแล้ว (PR #45 + #46 · เย็น 2026-07-15)**: รัน `curl` จาก main บน linux-nat จากศูนย์ → **`RESULT: PASS`** + เครื่องมือ **รอด 7/7 หลังลบ /tmp** + flow-gate ครบ 3 ไฟล์ (tier 3) · ระหว่างพิสูจน์เจอ+ปิด **"ผ่านปลอม" 3 ชั้น**: (ก) [PR #45] `mw-setup.sh` symlink ชี้ `/tmp` ของ installer ที่ถูกลบ → เครื่องมือตายยกชุด exit 127 (✅ ตอนติดตั้งหลอกเพราะ /tmp ยังอยู่) → แก้เป็น copy เข้า `~/.hermes/mw` ถาวรก่อน link + ตัด `mw-spec-check` (dev-only) ออกจากชุดทีม · (ข) [PR #46] `check-shortcuts.sh` ฝัง pin `version 2.6` ค้าง → `RESULT: FAIL` เงียบทุกเครื่องทีม → แก้เป็นเช็คกติกาสัญญาแทนเลขรุ่นตายตัว · Codex ตรวจ BLOCKING 3 จุดปิดครบ · test_mw_setup 4→8 เคส (มี regression ลบต้นทาง)
  - **เหลืองานคนต่อพนักงาน (ไม่ใช่บั๊ก)**: กุญแจ AI Relay ใน `~/.hermes/.env` ต้องแจกรายคน (AI สร้างแทนไม่ได้) — ตัวติดตั้งบอกวิธีแล้ว
  - เก็บงานเซสชันอื่นกันหายระหว่างทาง: curse/badword tracker + กฎ shortcut "ทุก Use ..." (commit `923dfa374`+`77d47159f` บน `feature/spec-central` · `20b0c1a4c` บน `control_webengine_flow`) — **ยังไม่ merged อยู่บน branch เหล่านั้น**
  - เหตุแทรก: VPS linux-nat ดับ ~8 ชม. กลางคืน (Tailscale offline) — กลับมาปกติเช้า 2026-07-15
- **2026-07-14 (แชท Opus · merged เข้า main แล้ว): `Use Migrate Web` — P3 เครื่องมือ 7/7 ครบ + สัญญา §13 COMPLETE + P4 installer** [fact]
  - **เครื่องมือ 7/7** (`scripts/mw/`): work_locks · menu_gate · page_check · mw_doctor · rtm_report · wow_report · backend_check — ทุกตัว Grok เขียน · GPT-5 ตรวจข้ามค่าย · ปิด ~44 false-positive (false-green/ready/verified/healthy) · **mw suite 252 passed**
  - **§13.1 COMPLETE 32/32** (`mw-spec-check.py` ด่าน 6 · `.project/mw-g-testid-map.md`) · pending 0 · strict mode ผ่าน · สัญญา §13 ครบ 3/3
  - **PR #35 (6/7) + PR #36 (ตัวที่ 7 + §13) merged เข้า main แล้ว** (squash) · main มีเครื่องมือครบ
  - **P4 installer เสร็จ**: `scripts/mw/mw-setup.sh` (symlink 8 เครื่องมือเข้า ~/.local/bin + ยิง --help ทุกตัว) + ผูกเข้า `team-shortcuts/install-shortcuts.sh` (best-effort) · 2 เทสต์ผ่าน
  - **ค้าง (ต้องใช้ของเจ้าของ):** รัน `mw-backend-check` กับ **RoadSafeFund จริง** (เดิน flow 1 เมนู · tier 3+) ต้องมี API base + วิธี query DB + token หรือสิทธิ์ VPS — เป็น P4 verify ข้อสุดท้าย
  - **ข้อจำกัดเครื่องนี้ (จดกันลืม):** coder = Grok ผ่าน relay (`AI_RELAY_ALLOW_LOCAL_CLI=1` + PATH `~/.local/bin` ตัวก่อน homebrew) · **`grok` ใช้ subscription ได้จริง (ตัวทางการ 0.2.99 ที่ ~/.local/bin) — โน้ตเก่าที่ว่า "grok ต้องมี API key" ผิด · ต้นเหตุคือ PATH หยิบ grok homebrew v1.0.1 ผิดตัว** · Codex ผ่าน relay crash (MCP/stdin) · reviewer = GPT-5 ผ่าน cross-check MCP (relay review พัง)

- **2026-07-14 (แชท Fable · branch `control_webengine_flow`): Shortcut `Use Migrate Web` — P1+P2 จบ · P3-I1 จบ · รอสลับ Opus ทำ I2** [fact]
  - **แผน MW ทั้งหมดอยู่ `.project/plan.md` หัวข้อ "Plan — MW"** (แผน active จริงของ branch นี้ · plan-anchor ยังอ่าน QAQC เป็นหลัก → เลขงาน MW ใช้ --no-plan)
  - P1: วิเคราะห์ 5 ชุดข้อมูล (FLOW v2 + Workshop + TOR 3 โปรเจกต์ + คลัง Obsidian + คำสั่งเพิ่ม) → บัญชี 55 กลุ่ม + จุดเคาะ 13 จุด เจ้าของอนุมัติครบ
  - P2: SPEC v1.2 (`.project/mw-spec-draft.md`) เจ้าของอนุมัติ · เครื่องตรวจ `scripts/mw-spec-check.py` PASS (ตารางแม่ 55/55 · baseline sha256)
  - P3-I1: prompt `use-migrate-web.md` + `use-migrate-web-flow13.md` (เนื้อต้นฉบับ 439 บรรทัดตรง 100% + embedded_sha256) + registry row — Codex ตรวจ 2 รอบ แก้ครบ
  - **งานถัดไปของแชทใหม่ (Opus): `Use New Chat` → `Use AI Relay` → ทำ MW-P3-I2 ตามแผนส่งมอบใน plan.md (เครื่องมือ 7 ตัว เริ่มที่ I2d work-locks)** · ข้อจำกัด relay บนเครื่องนี้จดไว้ในแผนแล้ว (review พัง → ใช้ cross-check MCP)

- **2026-07-14: เคลียร์ของค้างส่งต่อทีมอื่น — main สะอาดตรง origin/main** [fact · ตรวจ git state จริง tier 3]
  - ต้นเหตุ: branch `codex/block-ai-worktree-creation` (Codex สร้าง 07-12) ค้างอยู่ พร้อม dirty 19 แก้+8 ใหม่ · วันรุ่งขึ้น (07-13) งานชุดเดียวกันถูกทำใหม่สะอาดกว่า merge เข้า origin/main ผ่าน PR #30/#31/#32/#33 + portal routing ไปแล้ว → branch นี้กลายเป็นของซ้ำ
  - ทำ: ปัก 2 tag กันตก (`archive/codex-block-worktree-2026-07-12`→`c185b8a0b` เก็บ `CONTROL-CENTER-DESIGN.md`+worktree-block tests · `archive/local-main-orphan-2026-07-11`→`3bcfabfb9` เก็บ orphan DEC-036) + patch สำรอง 3181 บรรทัดใน scratchpad
  - ลบ 3 branch ค้าง: `codex/block-ai-worktree-creation` + `close/mem-2026-07-11` (remote gone) + `ds-standard-v3` (merged PR #30) · ขยับ local main `branch -f` + `checkout -f` → HEAD `7087b8fcd` = origin/main (เลี่ยง `reset --hard` ที่ classifier บล็อก)
  - ผล: เหลือ branch แค่ `main` + 2 worktree เจ้าของ (`feature/std-i2-project-dir` + `upgrade-audit/v0170` ไม่ถูกแตะ) · working tree สะอาด 0 dirty/untracked · **local main pointer เพี้ยนเดิม (ahead1/behind20) หายแล้ว**
- **2026-07-11: Design System พร้อมใช้จริง + relay tests เขียว 100% + Git graph สะอาด** [fact]
  - (ก) **DS**: ทำ `contrast-audit-run.mjs` (playwright headless · เอา Codex-review fix เข้า main แก้ 3 bug: NaN false-pass/networkidle-ค้าง/browser-leak) + `ds-adopt.sh` shortcut คำเดียว (`prep`/`check` รันด่านครบ build/ds-check/brand-leak/contrast · exit 1 บล็อก) + `admin-states.html` 5 states + เลิกลอก onemanfleet (brand-leak-check) + path portable (VPS/Mac) → merged PR #18/19/22/24/26
  - (ข) **relay**: DEC-036 quota/auth ปลอม (stderr ≤250 guard · PR #25) + ซ่อม test timeout ให้ตรงโค้ด Popen (mock subprocess.run ล้าสมัย) → **relay tests 72/72 เขียว**
  - (ค) **branch cleanup**: merged nat(#28)+shortcut Use Trade-off(#27 · resolve conflict payload) → ลบ merged 25+ branch · **ลบ remote upstream(NousResearch 1,292)+fork ทิ้ง → Git graph 1,300→6** (เหลือ origin/main + vps) · ต้นตอที่เจ้าของเห็น branch เต็ม = upstream ของ NousResearch ไม่ใช่งานเรา
  - (ง) ยืนยัน **JARVIS อยู่ SaaS repo ครบ + active** (typer งานต่อในนั้น) · Hermes jarvis 4 branch = เศษเก่าก่อนย้าย ลบแล้ว
- **2026-07-10: shortcut `Use QA QC` v1.1 เปิดใช้แล้ว (active · ทะเบียน 29→30)** — เจ้าของสั่งจบด้วย Fable ไม่รอกรรมการ · ตารางแม่ 16 หมวด/178 หัวข้อ + วินิจฉัย ViberQC อยู่ในคลัง (`AI-Security-Testing/`) · New Chat v2.0 + Close Chat v2.3 ผูกไฟล์กลาง `.project/qaqc-scan.md` แล้ว · branch งาน: `feature/use-qa-qc` (แผน active ใหม่ plan_id: QAQC · GRD ย้ายไป plan-grd.md) [fact]
- 2026-07-10: ซ่อม relay-call quota ปลอม (คำตอบยาวที่พูดถึง quota โดนตีเป็นโควต้าหมด) — scoped pytest 68/69 (1 แดง = เทสต์ timeout พังก่อนแก้ พิสูจน์แล้ว) · แก้ adapter grok (CLI v1.0.1 ตัด flag เก่า) · **grok headless ต้องมี API key = งานคนค้าง** · กรรมการรีวิวรวบ P1-P4 ยังไม่สำเร็จ (โควต้า/บั๊กวันเดียวกัน 3 ตัว) เลื่อนเป็น hardening [fact]
- **แผน GRD merged เข้า main แล้ว — PR #16 (`8bd9aa5e0`)** · ระบบกันแผนหาย/กัน AI มั่ว ใช้งานจริงบน main [fact]
- เก็บของค้างเช้า 2026-07-08: commit ไฟล์กฎกลาง 3 ไฟล์ในคลัง Obsidian (commit คลัง 7b52e4b — คนละ repo กับตัวนี้ · re-anchor v2.9/v4.2/v1.9) · push branch `feature/p12b-shortcut-guard` + เปิด **PR #17** (install guard กันเขียนทับไฟล์คลังที่ใหม่กว่า) [fact]
- memory-audit รันจริงบน repo: schema/SHA/ไฟล์ความจำ ✅ ครบ · เตือนเลขงานกำพร้า 33 ตัว (งานตั้งค่าจร ไม่ใช่บั๊ก) [fact]
- **แผน GRD ทำครบทั้ง 4 เฟสแล้ว (ประวัติ)** — P1 สัญญางานผูกแผน (plan-anchor + relay-call บังคับ + กฎ re-anchor ใน vault) · P2 memory-audit ตัวเทียบความจำ · P3 ด่านกัน stash กวาดงานคนอื่น · P4 ล้างความจำเก่า — ทุกชิ้นผ่านผู้ตรวจต่างค่าย + เทสต์ scoped เขียว (154 เคสรวม: 64 relay + 10 memory-audit + 80 guards) [fact]
- ตัวเขียนโค้ดจริงของรอบนี้: **Grok เป็นหลัก** (Codex ชนโควต้าตั้งแต่ใบแรก) · ใบแก้สุดท้าย Gemini · ผู้ตรวจ = Claude ทุกใบ [fact]
- **ชุดเทสต์เต็ม repo แดงอยู่ก่อนแล้ว**: `pytest -q` ที่ฐาน main = 683 failed / 24,193 passed (จุดตกอยู่ใน tests/cli, tests/gateway ที่งาน GRD ไม่ได้แตะ) — gate-run จดเป็นแถวแรกใน `.hermes/ledger/` แล้ว · เป็นงานซ่อมแยกรอบ [fact]
- PR #15 (แก้ auth ปลอมใน relay-call) merge เข้า main แล้ว — main HEAD = `5aa135e7f` [fact]
- สาย JARVIS v2: รอเจ้าของทดสอบเสียง P0 แล้วเปิดแชตใหม่ส่ง Use AI Relay [fact]

## งานถัดไป
0. **SPEC-CENTRAL ต่อ**: (ก) เจ้าของกด merge PR `SPEC-P5-I1` (SAFE_TO_MERGE แล้ว) + push คลัง Obsidian 7 ไฟล์ขึ้น GitLab · (ข) เปิดแชทใหม่ทำ **S1 (SPEC-P6-I1..I4)** = ตัวบังคับจริงระดับโค้ด (spec-interview + hook default-deny + เทสโจมตี 13 เคส ปิด C1-C5) — งาน security ห้ามรีบ · (ค) S2 + กระจาย 30-40 โปรเจกต์ (SPEC-P7)
1. **เริ่มใช้จริง RSF**: เจ้าของเปิดแชทที่ NewWebEngine2026 → `Use Migrate 0` (ชุดพร้อมเคาะอยู่ session log 2026-07-16) → เคาะ 2 ข้อ + `quota: nat=3` → 3 แชทจองคนละเมนู · เฟสโค้ด 8-9 ทีละเมนูเสมอ
1b. ประกาศทีม: รัน `curl .../install-from-github.sh | bash` ซ้ำเพื่อรับ `Use Migrate 0-13` (PR #50 merged แล้ว) + กุญแจ relay รายคน
2. **merge งานเซสชันอื่นที่เก็บกันหายไว้**: `feature/spec-central` (curse tracker + กฎ shortcut + spec ทดลอง) + `control_webengine_flow` (badword WIP + snapshot content) — รวม PR ให้เจ้าของกด
3. MW-P4 โซนแดงส่วนหลังบ้าน admin (ดูผ่านจอ admin จริง = M5 ของเมนูแรก) ทำตอนเดินเมนูจริง
4. (คิวเดิม) GRD-P5..P8 + QAQC-P5 รอเจ้าของสั่ง

## ข้อห้าม/กติกาล็อก
- **DEC-DSU-002 (2026-07-16 · Goal Lock):** สิ่งส่งมอบจริง = **ตัว shortcut `Use Create Design System` ที่แก้เสร็จ** (Front ครบ / Admin ครบ / ใช้ได้ VPS+Notebook พนักงาน / สร้าง DS ให้โปรเจกต์อื่นได้จริง) — **pilot Root Admin เป็นแค่เครื่องมือพิสูจน์ shortcut ไม่ใช่ตัวงาน** · ทุกขั้นต้องตอบว่า "พิสูจน์อะไรเกี่ยวกับ shortcut" · ห้ามทำงานนอกเป้าหมายนี้จนกว่า verified 100% · บรรทัดประกาศสถานีบังคับทุกข้อความ · รายละเอียดใน decisions.md
- ห้ามเขียนความจำทำงานต่อลง `.hermes/` หรือ root — เขียน `.project/` เท่านั้น (Schema v1.2)
- หลังสร้าง/ย้ายไฟล์ `.project/` ต้องผ่านด่าน `git check-ignore` + `git ls-files` ก่อนบอกเสร็จ
- **เลขงานต้องขึ้นต้นด้วย plan_id (เช่น GRD-P1-I1) · เลขที่ไม่มีใน plan.md = ห้ามทำ** · หลังตอบคำถามแทรก ต้องเปิด plan.md ทวนเฟสก่อนลงมือ (กติกาเหล็กของแผน GRD)
- ห้ามแตะ `.claude/launch.json` (งานเจ้าของค้าง) · [ปลดล็อก 2026-07-11: `design-system-standard-v2/` เจ้าของสั่งแก้จน DS พร้อมใช้จริง merged main แล้ว · `scripts/jarvis-voice/` ย้ายไป SaaS repo แล้ว = เศษ]
- ห้าม merge→main / deploy เอง — เจ้าของกด · งานหลายเฟส = 1 PR เดียว
- สมองแผน GRD = Fable ตามคำสั่งเจ้าของ 2026-07-07 (ข้อยกเว้นจากกติกา relay v2.7 ที่ปกติใช้ Opus) · Codex/Claude เขียน-ตรวจสลับค่ายผ่าน relay-call · **verified = มีแถว gate-run เท่านั้น**
- **กระจกคลัง Obsidian บน VPS = พื้นที่ทีมใช้ร่วม (มีไฟล์พนักงานจริง เช่น session log ของ peter)** — ห้าม mv/rsync ทั้งโฟลเดอร์เด็ดขาด · ซิงก์ได้เฉพาะโฟลเดอร์กลาง `ai-context/` + `skills/prompt-shortcuts/` จากเครื่องเจ้าของ · เจองานแปลกบนนั้น = กู้ขึ้นกิ่ง rescue ใน GitLab ก่อนเสมอ (2026-07-16)

## งานค้าง/ส่งต่อ
- **ใหม่ 2026-07-17 (SPEC-CENTRAL P5)**: (ก) รอเจ้าของกด **merge PR `task/nat/SPEC-P5-I1-central-prompts-sync`** (Save Git = SAFE_TO_MERGE) · (ข) รอเจ้าของ **push คลัง Obsidian 7 ไฟล์** (memory-schema + use-act-as/new-chat/comply/close-chat/save-git + registry) ขึ้น GitLab — AI push ตรงไม่ได้ · (ค) **S1 (SPEC-P6) ยังไม่เริ่ม** = ตัวบังคับจริง (ตอนนี้สเปคเป็นด่านระดับคำสั่ง AI ยังปลอมได้) · (ง) เทส payload 2 ตัวแดง-ค้างก่อนงานนี้ (spawn task แยก · ไม่ใช่ของ SPEC) · **next_owner: เจ้าของ (merge+push) → แชทใหม่ (S1)**
- **ใหม่ 2026-07-16 (ซ่อมยาม prewrite gate — อัปเดตสถานะ)**: prewrite gate v2.2 **ซ่อมเสร็จ + เสียบปลั๊กกลับแล้ว บังคับใช้จริง** (แก้ธง "ไม่บังคับใช้" ของ station gate ด้านล่าง) · เหลือ: (ก) **push commit `4599eaca0`** ติดเพราะ 29 ไฟล์ dirty ของเซสชัน NCR ก่อนหน้า → เจ้าของงาน NCR เคลียร์ก่อน หรือเจ้าของสั่ง cherry-pick ขึ้น branch สะอาด (ตอนนี้ทำเองไม่ได้ gate บล็อก checkout/switch) (ข) prewrite gate v2 ยังไม่เข้า PR/main (โค้ด local + ติดตั้งบนเครื่องแล้ว) (ค) ซ่อมสายพาน relay เต็มระบบ = งานเจ้าของ (ง) harden รอบหน้า: git plumbing chain + false-block quoted metachar
- **2026-07-16 (station gate · แก้แล้วบางส่วน)**: ~~prewrite-gate ไม่บังคับใช้อยู่~~ **เสียบกลับแล้ว 2026-07-16 (ยาม v2.2)** · (ก) **prewrite-gate ไม่บังคับใช้อยู่** — `~/.claude/hooks/enforce-new-chat-relay.py` มีไฟล์ (+.bak) แต่ไม่ผูกใน `settings.json`/`settings.local.json` (ถูก neutralize ระหว่างทำ PR #51 เพราะ deadlock) · เจ้าของเลือก: แก้ scope แล้วผูกกลับ หรือถอดถาวร · (ข) relay/codex crash ทั้งระบบบนเครื่องนี้ (station gate ต้องให้ Claude เขียนเอง) — งานซ่อมแยก ยังไม่ตรวจซ้ำ · (ค) station gate v2: ผูก approval รายเมนู/รายรอบ = งานปรับปรุงรอบหน้า · (ง) canonical repo จอดที่ `fix/mw-flow-station-gate` (merged · clean) สลับกลับ main ได้
- **ใหม่ 2026-07-16**: (ก) เจ้าของ: เริ่ม RSF `Use Migrate 0` + แชท Root Admin เรื่องรวมทางอัปโหลด (ใบสั่งงานใน session log) · (ข) ตัดสินใจค้าง: บรรจุข้อตรวจ "ที่เก็บอัปโหลด {siteId}/{หมวด} ทางเดียว" เข้า `Use Migrate 0` (เสนอแล้ว รอเคาะ) · (ค) กิ่ง `vps-rescue-2026-07-16` ใน GitLab คลัง = เก็บงาน rename `Use Request Merge` + สแนปช็อต VPS (แนะนำไม่รวม main · ลบได้เมื่อเจ้าของยืนยันไม่ใช้) · (ง) **ช่องว่างเครื่องมือ WTL**: `hermes-new-chat` ไม่มีคำสั่ง close/cleanup + ธง `--allow-over-limit` ที่ข้อความ error แนะนำไม่มีจริงใน CLI → worktree merge แล้วปิด/เก็บกวาดตามสัญญาไม่ได้ (วันนี้มี 4 โฟลเดอร์ค้าง: DSU, mw-station-gate, NCR, MWTS — 2 ตัวหลัง merge แล้วรอ cleanup dry-run) · (จ) ลบกิ่ง `close/mem-vps-verified` (ซ้ำ main)
- **แก้ความจำล้าสมัย 2026-07-16**: ~~"AI push คลัง Obsidian ไม่ได้ ด่านบล็อก"~~ — **push ได้จริงแล้ว** (พิสูจน์ 2 ครั้งวันนี้: `ef5b27d` + กิ่ง rescue ขึ้น GitLab สำเร็จ) · แถว "push คลัง" ในงานค้างเดิมข้างล่างถือว่าปิดแล้ว
- **ใหม่ 2026-07-15: branch งานเซสชันอื่นยังไม่ merged** — `feature/spec-central` (commit `923dfa374` curse tracker + `77d47159f` กฎ shortcut + spec-central 2 commit) และ `control_webengine_flow` (`20b0c1a4c` badword WIP + snapshot content v22) · เก็บกันหายแล้ว test เขียว แต่ต้องรวม PR ให้เจ้าของกด · เจ้าของถัดไป: เซสชันที่ทำงานนั้นต่อ
- ~~claimed: mw-setup.sh บน VPS ยังไม่รันยืนยัน~~ **verified 2026-07-15 เย็น: curl จาก main บน linux-nat → RESULT: PASS + เครื่องมือ 7/7 (PR #45+#46 · tier 3)** [fact]
- claimed (ยังไม่ตรวจ): เครื่องพนักงานจริงแต่ละคน (พิสูจน์แล้วเครื่องเจ้าของ Mac + VPS linux-nat · ยังไม่ครบทุกโน้ตบุ๊กทีม) · แต่ละคนต้องใส่กุญแจ AI Relay ใน `~/.hermes/.env` เอง
- ~~**2026-07-11: local main pointer เพี้ยน** (ahead1/behind20 + orphan DEC-036)~~ **แก้แล้ว 2026-07-14: main สะอาดตรง origin/main `7087b8fcd` · orphan เก็บ tag `archive/local-main-orphan-2026-07-11`** [fact] · vps เหลือ branch cache (prune ได้ถ้าอยาก)
- ~~รอเจ้าของ: ตรวจ+กด merge PR #17 + PR #14~~ **merged หมดแล้ว 2026-07-11 (PR ค้าง = 0)** [fact]
- รอเจ้าของ (เดิม): **ตรวจ+กด merge PR #17** (install guard) และ **PR #14** (relay-relogin ที่เปิดค้าง) · ส่งปัญหาชุดสุดท้าย (ปลดล็อก GRD-P6..P8) · rotate GitLab token (ค้างจาก 2026-07-04) · **push คลัง Obsidian ขึ้น GitLab** (commit คลัง 7b52e4b + 614e00a ค้างในเครื่อง 2 ตัว — คนละ repo กับตัวนี้ · AI push main ตรงไม่ได้ ด่านบล็อก) · ติดตั้ง memory-audit รายสัปดาห์ (ถ้าต้องการ): `(crontab -l 2>/dev/null; echo '0 9 * * 1 cd "/Users/rattanasak/Documents/Viber Project/Tech Tools/Hermes Agent" && ./venv/bin/python scripts/memory-audit/memory_audit.py >> ~/.claude/ai-fail-stats/memory-audit.log 2>&1') | crontab -`
- ~~สั่ง commit ไฟล์ JARVIS untracked~~ **แก้ความจำ 2026-07-08: ไฟล์ JARVIS เข้า git แล้วครบ 9 ไฟล์ (รวม FeatureSpec-jarvis-voice.md) — ไม่ใช่งานค้าง** [fact · ยืนยันด้วย git ls-files]
- **งานซ่อมแยกรอบ (ใหม่ 2026-07-08): ชุดเทสต์เต็ม repo แดง 683 เคสที่ฐาน main** — ทำให้ gate-run ตัดสิน pass ไม่ได้ทั้ง repo · ควรไล่ซ่อมหรือกำหนด gate ย่อยที่เขียวได้จริง (เสนอดูดเข้า GRD-P8)
- โควต้า AI คืน 2026-07-08: Codex + Grok ชนโควต้าทั้งคู่ช่วงดึก · Gemini crash ตอนจบแต่เขียนไฟล์สำเร็จ — เช็กโควต้าก่อนเริ่มงานใหญ่รอบถัดไป
- claimed (ยังไม่ตรวจ): iptables :3010 ไม่ persistent ข้าม reboot · webhook pr-review ลงแค่ project เด็กฝึก 527
- ด่านกันลบโฟลเดอร์ทั้งก้อน (phase-013): **โค้ด+เทสต์เข้า main แล้ว (`f9fb0827f`) [fact — แก้ความจำเก่าที่จดว่ายังค้าง]** · ที่ยังค้างจริง = ยืนยันว่า VPS runtime รันโค้ดรุ่นที่มีด่านนี้ (ยัง unverified)
- feature ค้างจากตารางรีวิว Hermes 2026-07-03: F3-F8
- อัปรุ่น v0.18.0 = GRD-P9 (ยังไม่เริ่ม · ต้องทำบัญชีของต่อเติมก่อน)

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
