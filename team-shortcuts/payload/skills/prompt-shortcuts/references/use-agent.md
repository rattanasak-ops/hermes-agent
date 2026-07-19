---
title: Use Agent
aliases:
  - Use Agent
  - use-agent
  - ใช้ Agent
  - จัดทีม AI
  - เลือกทีม AI
tags:
  - prompt-shortcuts
  - agent-center
  - team-routing
status: active
version: "1.3"
updated: 2026-07-19
---

# Use Agent

## Shortcut

```text
Use Agent
```

## Prompt

```text
Use Agent

ใช้ศูนย์รวมทีม AI เพื่อวินิจฉัยงานนี้ เลือกทีมและทักษะจากสมุดรายชื่อจริง แล้วคืนใบรายชื่อทีมกับซองสั่งงานก่อนลงมือ

Use Agent ใช้ได้กับงานคิด วิเคราะห์ วางแผน ออกแบบ สร้าง ตรวจ และฝึก Agent/Skill ไม่ได้จำกัดเฉพาะงานเขียนโค้ด ห้ามปฏิเสธเพียงเพราะโจทย์เป็นงานคิดหรือไม่มีขั้นลงมือสร้าง

กติกา:
1. อ่าน AGENTS.md และความจำโปรเจกต์ที่กำหนดก่อนวินิจฉัย
2. ทำงานเฉพาะ Git root และ branch ที่เจ้าของเปิดอยู่ ห้ามสร้างหรือสลับ branch/Worktree
3. แปลงคำขอเป็น structured diagnosis ที่มี project, goal, phase, execution_mode, domains, risks, signals, allowed paths, forbidden actions, deliverables และ evidence gates โดย execution_mode ใช้ think, plan, build, review หรือ train
4. เรียก agent_center_validate เพื่อตรวจสมุดรายชื่อ แล้วใช้ agent_center_route เพื่อสร้าง Team Manifest, แผน Shortcut ของทั้ง Phase และ Work Packet ห้ามเลือก Shortcut จากความจำเอง
4.1 อ่าน Prompt เต็มของทุก Shortcut ที่อยู่ใน `team.workflow.selected_shortcuts` ก่อนถึงสถานีนั้น โดย `Use Agent` เป็นทางเข้าเดียว ผู้ใช้ไม่ต้องจำหรือเรียก Shortcut ที่เหลือเอง
4.2 งาน build ใช้ลำดับกลาง `Use Flow Guardian` → `Use Comply` → Shortcut เฉพาะสายงาน → `Use Continue` → `Use Save Git` → `Use Close Chat` ภายใต้ Phase ใหญ่ งานปลอดภัยมีงบถามกลาง Phase 0 ครั้ง งานที่กระทบภายนอกรวบขออนุมัติไม่เกิน 1 ชุดต่อ Phase และรวมผลตรวจที่ปลาย Phase
5. ทุกโหมดบังคับ THINK_PAIR ให้ AI สองค่ายตรวจความคิดกัน ส่วน BUILD_REVIEW ใช้เฉพาะโหมด build โดยคนสร้างห้ามตรวจงานตัวเอง ห้ามลดเหลือยี่ห้อเดียวเงียบ ๆ
6. ตรวจ Work Packet ด้วย agent_center_validate ก่อนลงมือ
7. โหมด think, plan, review และ train ให้ส่งผลวิเคราะห์หรือคำตัดสินที่ผ่านคู่คิดได้ทันที โดยไม่บังคับสร้าง branch เขียนโค้ด หรือขออนุมัติงานสร้าง ส่วนโหมด build ให้ AI ในแอปปัจจุบันลงมือได้เมื่อพื้นที่และขอบเขตผ่าน ใช้ Use AI Relay เฉพาะเมื่อเจ้าของเรียกชัดเจน
8. ผลผ่านต้องมาจาก test/lint/build/manual evidence จริง ไม่ใช่คำบอกของ AI
9. การเทรน Agent/Skill ให้สร้าง training candidate เท่านั้น ห้ามเลื่อนขั้นหรือเขียน Obsidian ถาวรอัตโนมัติ
10. ถ้าไม่พบ Skill, plugin หรือเครื่องมือ Agent Center ให้คืน AGENT_CENTER_UNAVAILABLE พร้อมหลักฐานส่วนที่หาย ห้ามแต่งกฎว่า Use Agent ใช้กับงานคิดไม่ได้
11. ผล route_ready หมายถึงจัดทีมได้เท่านั้น ยังไม่ใช่หลักฐานว่า AI ทุกที่นั่งทำงานแล้ว ให้เรียก agent_center_execute ด้วย Packet ที่ตรวจผ่านและคำขอเดิม เครื่องมือนี้ต้องเรียก Subscription ที่ล็อกอินอยู่จริงเท่านั้น: Codex ผ่าน ChatGPT login, Claude ผ่าน OAuth ของ Claude Code และ Grok ผ่าน xAI OAuth ของ Hermes ห้ามรับ provider override ห้ามอ่านกุญแจ API และห้ามวิ่งผ่าน AI Relay เครื่องมือต้องคืนผลจริง ลายนิ้วมือ SHA-256 และ output_ref แยกทุกที่นั่งก่อนสังเคราะห์ ถ้าเรียกคู่คิดคนละตระกูลจริงไม่ได้ ให้คืน THINK_PAIR_EXECUTION_UNAVAILABLE ห้ามสร้างผลตรวจปลอม ส่วน build ต้องใช้พื้นที่สะอาดที่อนุมัติ มี allowed_paths ชัดเจน ให้ผู้ลงมือเขียนไฟล์จริง แล้วส่งผู้ตรวจคนละ session และคนละตระกูลตรวจแบบอ่านอย่างเดียว
12. ก่อนอ้างว่างานคิด/วิเคราะห์จบ ต้องส่ง Work Packet ต้นฉบับพร้อม Work Receipt รุ่น 2 ที่มี request/output/synthesis hash เข้า agent_center_validate ในครั้งเดียว และต้องได้ receipt_runtime_valid เท่านั้น ส่วน receipt_structural_valid แปลว่าตรวจเพียงโครงกับตัวตน ยังห้ามอ้างว่า AI ทำงานจริง Receipt เดี่ยวหรือ Packet รุ่น 1 ห้ามใช้เป็นหลักฐานจบงาน

ผลลัพธ์ขั้นต่ำ:
- ใบวินิจฉัยงาน
- Team Manifest: leads, specialists, skills, reasons
- Phase Workflow: Shortcut ที่เลือกตามลำดับ, งบถามงานปลอดภัย 0 ครั้ง, จุดรวมผลตรวจ และด่านขออนุมัติภายนอก
- Work Packet: packet_schema_version, packet_id, execution_mode, scope, active seats, workflow, deliverables, evidence gates
- Work Receipt รุ่น 2: seat_evidence ของทุก active seat, synthesis, gate results และผลตรวจที่ผูกกับ Work Packet ต้นฉบับ
- Decision: route_ready หรือ blocked พร้อมเหตุผลและขั้นตอนถัดไปหนึ่งข้อ
```

## Runtime source

ขั้นตอนฉบับใช้งานจริงอยู่ที่ `skills/agent-center/SKILL.md` และเครื่องมือทั้ง 7 ตัวมาจากปลั๊กอิน `plugins/agent_center/` ใน Hermes Agent

## Safety

- ไม่แก้แกน Hermes Agent ผ่าน Shortcut นี้
- ไม่บังคับ AI Relay
- ไม่ติดตั้งโปรไฟล์ Agent จากสมุดรายชื่อ
- ไม่เขียนความรู้ถาวรหรือส่งข้อมูลลับ
- ไม่ commit, push, merge หรือ deploy โดยไม่มีด่านเฉพาะและคำอนุมัติ
