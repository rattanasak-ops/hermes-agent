---
memory-schema: v1.2
spec_id: UAG
status: building         # draft | approved | building | done
linked_plan: UAG
owner_approved: true     # เจ้าของพิมพ์อนุมัติสเปคเทคนิคนี้เมื่อ 2026-07-18
updated: 2026-07-18
---

# สเปค: ศูนย์รวมทีม AI ประจำบริษัท "Use Agent" (Agent Center) — เฟส 1

> รัฐธรรมนูญโปรเจกต์ = Locked Decisions Vault + CLAUDE.md · สเปคนี้ห้ามขัด
> สเปคนี้ **อนุมัติแล้ว** · เจ้าของอนุมัติทั้ง "ทิศทาง + แผนที่ Agent v0.1" และ "ตัวสเปคเทคนิคนี้" เมื่อ 2026-07-18 → ปลดล็อกให้เริ่ม UAG-P2 ได้
> คำแปลไทย (ใช้ครั้งแรก): `Agent Center` = ศูนย์รวมทีม AI · `Consultor` = ที่ปรึกษาวินิจฉัยหน้าด่านแรก (ไม่ผูกยี่ห้อ AI) · `catalog` = สมุดรายชื่อ · `plugin` = ปลั๊กอินเสริมที่แถมมากับ Hermes · `Work Packet` = ซองสั่งงาน · `Team Manifest` = ใบรายชื่อทีมที่เลือก · `provider` = ยี่ห้อ AI (Opus/Codex/Grok) · `routing` = การจัดเส้นทางงานไปหาทีมที่เหมาะ · `promote` = เลื่อนขั้นความรู้ให้เป็นของถาวร

## 1. จะทำอะไร · ทำไม (WHAT / WHY — ห้ามพูดวิธี/เทคโนโลยี)
- ทำอะไร: ทำ **ประตูเดียว "Use Agent"** ที่มีที่ปรึกษาวินิจฉัยงาน (โปรเจกต์/ปัญหา/ช่วงงาน/ความเสี่ยง/ผลที่อยากได้) แล้วเลือก "ทีม AI + ทักษะ" ที่เหมาะ ก่อนให้ AI ในแอปปัจจุบันลงมือในพื้นที่ที่อนุมัติ · `Use AI Relay` เป็นทางเลือกเมื่อเจ้าของเรียกชัดเจน  [fact]
- ทำไม / ใครได้ประโยชน์: เจ้าของ/ทีมมีที่เดียวจบสำหรับสั่งงาน AI ทั้งบริษัท · ความรู้เรื่องทีม/ทักษะเป็นของ Hermes กลาง ไม่ผูกยี่ห้อ AI ตัวใดตัวหนึ่ง · เน้นงานสาย Creative/Brand/กราฟิก/UX-UI/ออกแบบเว็บ/เว็บแอป โดยเฉพาะงาน Web Engine ใหญ่  [fact]

## 2. จุดต้องเคลียร์ก่อนเขียนโค้ด (ด่านกันเดา · DEC-040)

### จุดเปิดจริง (ปิดครบแล้ว)
- [x] เจ้าของอนุมัติ **ตัวสเปคเทคนิคนี้** แยกจากการอนุมัติทิศทาง → เจ้าของพิมพ์เมื่อ 2026-07-18: "อนุมัติสเปค UAG ฉบับนี้ให้ผมเปลี่ยนสถานะเป็น approved และเริ่ม UAG-P2 ได้" → เริ่ม UAG-P2 ได้

### ปิดแล้วเป็นข้อเท็จจริง (มีหลักฐานในรอบนี้ ไม่ต้องถามเจ้าของซ้ำ)
- [x] คู่ตรวจ default ของกฎ 2 สมอง = AI ปัจจุบัน + Grok · **รอบนี้ Grok ล่มจริง เจ้าของอนุมัติให้ใช้ Opus แทนชัดเจน** → สรุปเป็นข้อเท็จจริง: มีตัวสำรอง Opus/Codex ตามกติกาข้อ 3 (fallback) [fact]
- [x] ที่อยู่ปลั๊กอิน `plugins/agent_center/` เป็นตำแหน่งปลั๊กอินแถมที่ถูกต้อง + skill `skills/agent-center/SKILL.md` เป็นตำแหน่ง skill ในrepo ที่อนุมัติสำหรับดีไซน์นี้ → ยืนยันเป็นข้อเท็จจริง ใช้ path นี้ใน P2/P3 [fact]
- [x] "เตรียมซองสมัครเทรนทักษะ" เฟส 1 เขียนลง `95-Inbox-Lab/review/` ผ่าน `obsidian_safe_write_review` **ทางเดียวเท่านั้น** → ยืนยันเป็นข้อเท็จจริง [fact]

## 3. ขอบเขต
- ทำ (in):
  - ปลั๊กอินแถม `plugins/agent_center/` เจ้าของสมุดรายชื่อทีม/ทักษะ (มีเลขรุ่น) + ตัวตรวจ/จัดเส้นทางแบบผลลัพธ์แน่นอน — **ห้ามแก้แกน Hermes (core)**
  - เครื่องมือเฟส 1 · 6 ตัว (ดูรายชื่อทีม / เปิดดูทีม / ดูรายชื่อทักษะ / จัดเส้นทาง 1 งาน / เตรียมซองสมัครเทรนโดยยังไม่เลื่อนขั้น / ตรวจความถูกต้อง)
  - skill `Use Agent` + payload ของ shortcut ทีม
  - 2 นโยบายบังคับ: THINK_PAIR (คิดคู่) + BUILD_REVIEW (ทำ-รีวิวแยกคน)
  - สมุดรายชื่อ 9 โปรไฟล์ **เก็บเป็นรายการตรรกะเท่านั้น** (ยังไม่ติดตั้งเป็นโปรไฟล์รันจริง)
  - เทสต์ + บัญชี N/M
- ไม่ทำรอบนี้ (out):
  - ไม่ทำหน้าจอ (UI) · ไม่แก้ตัวเชื่อม provider · ไม่แก้ค่าตั้งผู้ใช้
  - ไม่ติดตั้งโปรไฟล์รันจริง · ไม่เลื่อนขั้นความรู้ถาวรอัตโนมัติ · ไม่แก้ไฟล์ core
  - ไม่แตะสมุดทะเบียนกลางใน Obsidian จนกว่าโค้ด+เทสต์เสร็จ

### แผนที่ทับซ้อน (overlap · UAG-P1-I2 · จาก Opus safeguard #3)
| ของเดิม | บทบาทในระบบใหม่ |
|---|---|
| `~/.claude/agents/orchestra/conductor.md` (Claude) | **วัตถุดิบอ้างอิงเท่านั้น** · แทนที่ด้วยความหมาย Consultor ที่ไม่ผูกยี่ห้อ |
| `Use AI Relay` | ตัวรับส่งงาน/รีวิวแบบเลือกใช้ **คงเดิม** · Agent Center ไม่บังคับเรียกและไม่เขียนทับ |
| โปรไฟล์ Hermes (รันจริง) | รูปแบบตอนรัน **ทีหลัง** · เฟส 1 ยังไม่ติดตั้ง |
| `obsidian_safe_bridge` / `obsidian_safe_write_review` | ทางเขียนที่อนุมัติ **ทางเดียว** เข้า `95-Inbox-Lab/review/` |

## 4. เกณฑ์ผ่าน (ถ้า/เมื่อ/แล้วต้องได้ · given/when/then)
| # | given (สถานะตั้งต้น) | when (ทำอะไร) | then (ผลที่ต้องได้) |
|---|---|---|---|
| 1 | มีสมุดรายชื่อทีม/ทักษะในปลั๊กอิน | เรียกเครื่องมือ "ดูรายชื่อทีม/ทักษะ" | คืนรายการครบตามสมุด ไม่ตกหล่น |
| 2 | มีคำขอ 1 งาน (เช่น งานออกแบบเว็บ) | เรียกเครื่องมือ "จัดเส้นทาง" | ได้ทีม+ทักษะที่เหมาะ โดย Creative/Design เป็นโดเมนชั้นหนึ่ง |
| 3 | มีคำของาน Web Engine ใหญ่ | เรียกเครื่องมือ "จัดเส้นทาง" | web-engine-lead ถูกเลือกเป็นแกน ไม่ถูกมองเป็นงานทั่วไป |
| 4 | หา 2 ยี่ห้อ AI ต่างกันไม่ได้ | ระบบจะบังคับกฎ THINK_PAIR | คืนผล "ติดกันชน (blocked)" + เหตุผล · ห้ามแอบใช้ยี่ห้อเดียวแล้วบอกผ่าน |
| 5 | คนทำ (worker) = ยี่ห้อ X | ระบบจัด BUILD_REVIEW | คนรีวิวต้องเป็นยี่ห้อ ≠ X และอ่านอย่างเดียว |
| 6 | มี feedback/หลักฐานให้เทรนทักษะ | เรียก "เตรียมซองสมัครเทรน" | ได้ซองรอรีวิว **ยังไม่เลื่อนขั้น** · เขียนผ่าน review queue เท่านั้น |
| 7 | ปลั๊กอินทำงาน | ตรวจ diff เทียบ core | ไฟล์ core ไม่มีการแก้ (0 บรรทัด) |

## 5. ตารางแม่กันหาย (นับ N/M · แบบ scripts/mw-spec-check.py)
| รหัส | สิ่งที่ต้องมี | จุดพิสูจน์ path:line | สถานะ |
|---|---|---|:---:|
| U1 | ปลั๊กอินแถม + สมุดรายชื่อมีเลขรุ่น | `plugins/agent_center/plugin.yaml` + `data/*.json` | ☑ |
| U2 | เครื่องมือ 6/6 | `plugins/agent_center/__init__.py` + `tools.py` | ☑ 6/6 |
| U3 | skill `Use Agent` | `skills/agent-center/SKILL.md` | ☑ |
| U4 | payload shortcut ทีม | `team-shortcuts/payload/` | ☑ 4/4 |
| U5 | นโยบาย THINK_PAIR (คิดคู่ · 2 ยี่ห้อต่างกัน) | `plugins/agent_center/policies.py` | ☑ |
| U6 | นโยบาย BUILD_REVIEW (ทำ-รีวิวแยกยี่ห้อ) | `plugins/agent_center/policies.py` | ☑ |
| U7 | ซองสั่งงาน 4 ที่นั่ง (planner_primary/planner_challenger/worker/reviewer) | `plugins/agent_center/routing.py` | ☑ 4/4 |
| U8 | สายเทรนทักษะ (หลักฐาน→ซอง→รีวิวอิสระ→เจ้าของอนุมัติ→ออกรุ่น→pilot→เลื่อนขั้น) | `routing.py` + `use-agent.md` | ☑ |
| U9 | สมุดรายชื่อ 9 หัวหน้าทีม (lead · รายการตรรกะ) | `data/agents.json` | ☑ 9/9 |
| U10 | สมุดรายชื่อผู้เชี่ยวชาญ 37 บทบาท (specialist · รายการตรรกะ) | `data/agents.json` | ☑ 37/37 |
| U11 | ตระกูลทักษะ 12 ตระกูล | `data/skills.json` | ☑ 12/12 |
| U12 | ทักษะเริ่มต้น (seed skill) 52 ตัว | `data/skills.json` | ☑ 52/52 |
| U13 | ช่องนิยาม Agent ขั้นต่ำ 19 ช่อง + Skill ขั้นต่ำ 13 ช่อง | `plugins/agent_center/catalog.py` | ☑ 19/19 + 13/13 |
| U14 | ใบเสร็จงาน (Work Receipt) เฟส 1 นิยาม schema · pilot กรอกจริง | `plugins/agent_center/policies.py` | ☑ 2/2 pilot receipt valid |
| U15 | เทสต์คลุมสมุด/จัดเส้นทาง/2 นโยบาย/4 ที่นั่ง | `tests/plugins/test_agent_center.py` | ☑ 109/109 |

### รายการ 9 หัวหน้าทีม (lead · เก็บเป็นรายการตรรกะเท่านั้น · ยังไม่ติดตั้งรันจริง · N/M = 9/9)
1. consultor — ที่ปรึกษาวินิจฉัยหน้าด่านแรก
2. strategy-research-lead — หัวหน้ากลยุทธ์/วิจัย
3. creative-brand-lead — หัวหน้าครีเอทีฟ/แบรนด์
4. experience-design-lead — หัวหน้าออกแบบประสบการณ์ (UX/UI)
5. web-engine-lead — หัวหน้างานเว็บเอนจินใหญ่
6. application-engineering-lead — หัวหน้างานเว็บแอป
7. quality-risk-lead — หัวหน้าคุณภาพ/ความเสี่ยง
8. platform-delivery-lead — หัวหน้าส่งมอบ/แพลตฟอร์ม
9. knowledge-training-curator — ผู้ดูแลคลังความรู้/การเทรน

### รายการผู้เชี่ยวชาญ 37 บทบาท (specialist · รายการตรรกะเท่านั้น ไม่ใช่โปรไฟล์รันจริง · N/M = 37/37)

> รวมเป็นสมุดรายชื่อในสมุดของปลั๊กอิน แยก 5 กลุ่ม · กลุ่ม = 5+6+8+9+9 = 37

**กลุ่ม A · กลยุทธ์/ค้นโจทย์ (strategy & discovery · 5/5)**
1. business-strategist — นักกลยุทธ์ธุรกิจ
2. product-strategist — นักกลยุทธ์ผลิตภัณฑ์
3. market-researcher — นักวิจัยตลาด
4. ux-researcher — นักวิจัยผู้ใช้
5. content-strategist — นักกลยุทธ์เนื้อหา

**กลุ่ม B · ครีเอทีฟ/แบรนด์/กราฟิก (creative, brand & graphic · 6/6)**
6. creative-director — ผู้กำกับครีเอทีฟ
7. brand-strategist — นักกลยุทธ์แบรนด์
8. art-director — ผู้กำกับศิลป์
9. graphic-designer — นักออกแบบกราฟิก
10. illustrator — นักวาดภาพประกอบ
11. content-designer — นักออกแบบเนื้อหา

**กลุ่ม C · UX/UI/ออกแบบเว็บ (UX, UI & web design · 8/8)**
12. information-architect — สถาปนิกสารสนเทศ
13. ux-designer — นักออกแบบประสบการณ์
14. interaction-designer — นักออกแบบการโต้ตอบ
15. ui-designer — นักออกแบบหน้าจอ
16. web-designer — นักออกแบบเว็บ
17. motion-designer — นักออกแบบการเคลื่อนไหว
18. design-system-architect — สถาปนิกระบบดีไซน์
19. design-engineer — วิศวกรดีไซน์ (ต่อดีไซน์เข้าโค้ด)

**กลุ่ม D · เว็บเอนจิน/เว็บแอป (web engine & application · 9/9)**
20. web-engine-architect — สถาปนิกเว็บเอนจิน
21. multi-tenant-architect — สถาปนิกหลายผู้เช่า (แยกข้อมูลรายลูกค้า)
22. cms-workflow-designer — นักออกแบบขั้นตอนจัดการเนื้อหา
23. search-architect — สถาปนิกระบบค้นหา
24. frontend-engineer — วิศวกรหน้าเว็บ
25. backend-engineer — วิศวกรหลังบ้าน
26. database-engineer — วิศวกรฐานข้อมูล
27. integration-engineer — วิศวกรเชื่อมระบบ
28. ai-automation-engineer — วิศวกรงานอัตโนมัติด้วย AI

**กลุ่ม E · คุณภาพ/ส่งมอบ (quality & delivery · 9/9)**
29. design-critic — ผู้วิจารณ์ดีไซน์
30. visual-qa — ผู้ตรวจภาพหน้าจอ
31. accessibility-specialist — ผู้เชี่ยวชาญการเข้าถึง
32. performance-specialist — ผู้เชี่ยวชาญความเร็ว
33. security-reviewer — ผู้ตรวจความปลอดภัย
34. test-engineer — วิศวกรทดสอบ
35. release-reviewer — ผู้ตรวจก่อนปล่อยรุ่น
36. platform-engineer — วิศวกรแพลตฟอร์ม
37. reliability-engineer — วิศวกรความเสถียร

### รายการตระกูลทักษะ 12 ตระกูล + ทักษะเริ่มต้น 52 ตัว (seed skill · รายการตรรกะเท่านั้น · N/M = 12 ตระกูล / 52 ตัว)

> ทักษะเป็นของ Hermes กลาง ไม่ผูกยี่ห้อ AI · เฟส 1 เก็บเป็นรายชื่อในสมุด ยังไม่เทรน/ยังไม่เลื่อนขั้น

**1. discovery (ค้นโจทย์ · 4)**: project-discovery · stakeholder-intake · requirement-framing · evidence-audit
**2. business-product (ธุรกิจ/ผลิตภัณฑ์ · 4)**: value-proposition · product-prioritization · user-journey · competitor-analysis
**3. creative-brand (ครีเอทีฟ/แบรนด์ · 4)**: creative-direction · brand-strategy · moodboard-direction · art-direction
**4. graphic (กราฟิก · 4)**: logo-system · iconography · illustration-direction · campaign-visual
**5. ux (ประสบการณ์ผู้ใช้ · 4)**: ux-research · information-architecture · task-flow · usability-review
**6. ui-web-design (หน้าจอ/ออกแบบเว็บ · 4)**: visual-hierarchy · responsive-layout · interaction-states · web-page-composition
**7. motion (การเคลื่อนไหว · 4)**: motion-language · scroll-interaction · transition-design · reduced-motion
**8. design-system (ระบบดีไซน์ · 4)**: token-architecture · component-anatomy · theming · design-system-audit
**9. web-engine (เว็บเอนจิน · 5)**: multi-tenant-web · page-builder · cms-workflow · reusable-module-design · search-design
**10. engineering (วิศวกรรม · 5)**: frontend-build · api-contract · database-design · integration-design · ai-automation
**11. quality (คุณภาพ · 5)**: visual-check · accessibility-audit · performance-audit · security-review · release-gate
**12. knowledge-training (ความรู้/การเทรน · 5)**: training-intake · evidence-scoring · skill-evaluation · agent-evaluation · promotion-review

รวม: 4+4+4+4+4+4+4+4+5+5+5+5 = **52 ทักษะเริ่มต้น** ใน **12 ตระกูล**

### ช่องนิยามขั้นต่ำ (schema ของสมุดรายชื่อ · เฟส 1 กำหนดโครง ยังไม่กรอกครบทุกตัว)

**นิยาม Agent ขั้นต่ำ 19 ช่อง** (ครบตามแผนที่ Agent v0.1 ที่เจ้าของอนุมัติ):
`id` (รหัส) · `name_th` (ชื่อไทย) · `mission` (ภารกิจ) · `activates_when` (เปิดใช้เมื่อ) · `must_not_use_when` (ห้ามใช้เมื่อ) · `owned_outcomes` (ผลที่ต้องรับผิดชอบ) · `required_inputs` (ของที่ต้องได้ก่อนเริ่ม) · `project_context` (บริบทโปรเจกต์) · `skills_required` (ทักษะที่ต้องมี) · `skills_optional` (ทักษะเสริม) · `allowed_tools` (เครื่องมือที่ใช้ได้) · `write_policy` (นโยบายการเขียน) · `deliverables` (ของที่ส่งมอบ) · `acceptance_gates` (ด่านตรวจผ่าน) · `reviewer_policy` (กติกาผู้ตรวจ) · `memory_scope` (ขอบเขตความจำ) · `ai_preferences` (ยี่ห้อ AI ที่เหมาะ) · `metrics` (ตัววัดผล) · `version` (เลขรุ่น)

**นิยาม Skill ขั้นต่ำ 13 ช่อง** (ครบตามแผนที่ Agent v0.1 ที่เจ้าของอนุมัติ):
`name` (ชื่อ) · `description` (คำอธิบาย) · `triggers` (คำ/เหตุที่กระตุ้น) · `not_for` (ไม่ใช้กับ) · `required_inputs` (ของที่ต้องได้ก่อนเริ่ม) · `steps` (ขั้นตอน) · `deliverables` (ของที่ส่งมอบ) · `evidence` (หลักฐาน) · `allowed_tools` (เครื่องมือที่ใช้ได้) · `risks` (ความเสี่ยง) · `examples` (ตัวอย่าง) · `training_metrics` (ตัววัดตอนเทรน) · `version` (เลขรุ่น)

### เส้นแบ่งหน้าที่ (Consultor / plugin / route / Use Agent / Relay — กันสับสน)

| ตัวไหน | ทำอะไร | ไม่ทำอะไร |
|---|---|---|
| Consultor (ที่ปรึกษา) | ใช้การคิดของ AI แปลงภาษาคนเป็น "ใบวินิจฉัยงาน" มีโครง (โดเมน/ช่วงงาน/ความเสี่ยง/ผลที่อยากได้) | ไม่ตัดสินคะแนน/ไม่เลือกทีมเอง · ไม่ผูกยี่ห้อ AI |
| plugin (ปลั๊กอิน) | รับใบวินิจฉัย แล้ว **ตรวจ+ให้คะแนนแบบผลลัพธ์แน่นอน** (โค้ดตายตัว รันซ้ำได้ผลเดิม) | ไม่ใช้การเดาของ AI · ไม่แก้แกน Hermes |
| `route` (จัดเส้นทาง) | คืน **ใบรายชื่อทีม (Team Manifest) + ซองสั่งงาน (Work Packet)** | ไม่ลงมือทำงานเอง · ไม่ส่งเข้า Relay เอง |
| skill `Use Agent` | ส่งซองสั่งงานให้ AI ในแอปปัจจุบัน หรือ Relay เมื่อเจ้าของเรียกชัดเจน | เฟส 1 **ไม่แก้แกน Relay** และไม่บังคับใช้ Relay |
| `Use AI Relay` | รับส่งงาน/รีวิว (transport) ตามเดิม | คงเดิม · Agent Center ไม่เขียนทับ |

### ใบเสร็จงาน (Work Receipt · เพิ่มเข้าผลงานที่วางแผน)

> เหตุผล: การเทรนทักษะต้องมี "หลักฐานว่าใครวางแผน/ใครค้าน/ใครทำ/ใครตรวจ · ใช้ทักษะอะไร · ด่านตรวจผลเป็นไง · ลิงก์ซองรอรีวิว"

- เฟส 1: **กำหนดโครง (schema) ของใบเสร็จงานเท่านั้น** · pilot (นำร่อง) ค่อยกรอกจริง
- ช่องขั้นต่ำของใบเสร็จงาน: `packet_id` · `planner_primary` · `planner_challenger` · `worker` · `reviewer` (แต่ละช่องเก็บทั้ง provider ID + session ID) · `skills_used` · `gate_results` (ผลด่านตรวจ + tier) · `candidate_links` (ลิงก์ซองรอรีวิวใน `95-Inbox-Lab/review/`) · `created_at` · `version`
- ใบเสร็จงานเป็นวัตถุดิบเข้าสายเทรนทักษะ (§7) · ไม่ใช่การเลื่อนขั้นอัตโนมัติ

### 2 นโยบายบังคับ (รายละเอียด)
- **THINK_PAIR (คิดคู่)**: คนวางแผนหลัก + คนค้าน ต้องเป็น **คนละยี่ห้อ** · ต้องบันทึกทั้ง 2 ความเห็น + ข้อสรุปสุดท้าย · **ห้ามมีผลสำเร็จจากยี่ห้อเดียวแบบเงียบ ๆ**
  - **กติกาเลือกตัวสำรอง (ชัด ไม่กำกวม · เรียงตามลำดับ)**:
    1. default = AI ปัจจุบัน + Grok
    2. ถ้า Grok ใช้ไม่ได้ → เลือก Opus **เฉพาะเมื่อ AI ปัจจุบันไม่ใช่ Opus** · ถ้า AI ปัจจุบันเป็น Opus อยู่แล้ว → เลือก Codex แทน
    3. กติกาทั่วไป: เลือก provider ตัวแรกที่ยังใช้งานได้ (healthy) และ **provider ID ต่างจาก AI ปัจจุบัน**
    4. ถ้าหาตัวที่ต่างยี่ห้อไม่ได้เลย → คืนผล **"ติดกันชน (blocked)"** พร้อมเหตุผล
  - **ห้ามเด็ดขาด**: Opus↔Opus หรือ Codex↔Codex ถือเป็นคู่ตรวจที่ใช้ไม่ได้ (ยี่ห้อเดียวกัน = ไม่ใช่การตรวจข้าม)
- **BUILD_REVIEW (ทำ-รีวิวแยกคน)**: รอบทำงานกับรอบรีวิวแยกกัน · ยี่ห้อคนทำต้อง ≠ ยี่ห้อคนรีวิว · คนรีวิวอ่านอย่างเดียว · **`gate-run` คือหลักฐานตัดสินจริง** ไม่ใช่ปากคนรีวิว

### ซองสั่งงาน 4 ที่นั่ง (แต่ละที่นั่งรันคนละรอบ · session แยก)
planner_primary · planner_challenger · worker · reviewer — **ทั้ง 4 ที่นั่งรันแยกรอบเสมอ (session ID คนละตัวทุกที่นั่ง)** ไม่ใช่ให้ยี่ห้อเดียวสวมหลายที่นั่งในรอบเดียว

- **ใช้ยี่ห้อเดิมซ้ำได้เฉพาะที่นั่งที่ไม่ใช่ worker/reviewer** และได้ต่อเมื่อ **รันคนละ session จริง** และกฎคิดคู่ (THINK_PAIR) ยังมี 2 ยี่ห้อต่างกันอยู่ (คนวางแผนหลัก ≠ คนค้าน)
- **worker กับ reviewer ต้องต่างกันทั้ง 2 อย่าง**: ต่าง provider ID (ยี่ห้อ AI) **และ** ต่าง session ID (คนละรอบ) · ยี่ห้อเดียว/รอบเดียวกัน = ใช้ไม่ได้เด็ดขาด
- เก็บ provider ID + session ID ของทุกที่นั่งลงใบเสร็จงาน (Work Receipt) เพื่อพิสูจน์ย้อนหลังว่าที่นั่งแยกกันจริง

### สายเทรนทักษะ (§7)
feedback/หลักฐาน → ซองสมัคร → รีวิวโดยคนอิสระ → เจ้าของอนุมัติ → ออกรุ่น → pilot → เลื่อนขั้น · **feedback ซ้ำ ๆ = หลักฐาน ไม่ใช่สิทธิ์อัตโนมัติ** · เนื้อซองส่งผ่าน `obsidian_safe_write_review` · Agent Center ไม่เขียนความรู้ถาวรลงคลังเอง

## 6. ส่งต่องาน
- ห้ามเริ่มเขียนโค้ดถ้า status ไม่ใช่ approved/building (ตอนนี้ building เมื่อ 2026-07-18)
- verified = แถว gate-run เท่านั้น (สืบทอด Schema §3–§4) · งานเอกสารรอบนี้ = `manual_verified`
- เฟส 1 ไม่มีหน้าจอ/ไม่แตะ core/ไม่แก้ provider/ไม่เลื่อนขั้นความรู้ถาวรอัตโนมัติ
- ให้ AI ในแอปปัจจุบันลงมือในพื้นที่ที่เจ้าของเปิด · เรียก `Use AI Relay` เฉพาะเมื่อเจ้าของสั่งตรง

<!-- จุดเชื่อม lifecycle (ทาง A · capability-based · ไม่แตะ schema core)
New Chat 0a: อ่าน .project/spec/ ถ้ามี · Act-As: เขียน spec ก่อน/คู่ plan.md
Comply: แตก issue อ้าง spec_id · Continue/Relay: plan-anchor --emit-brief ผนวก spec
Close: Spec Sync (แบบ Business Plan/QA-QC Sync) · Save Git: field spec_gate ใน .savegit.json -->
