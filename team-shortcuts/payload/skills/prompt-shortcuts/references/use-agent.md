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
version: "1.0"
updated: 2026-07-18
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

กติกา:
1. อ่าน AGENTS.md และความจำโปรเจกต์ที่กำหนดก่อนวินิจฉัย
2. ทำงานเฉพาะ Git root และ branch ที่เจ้าของเปิดอยู่ ห้ามสร้างหรือสลับ branch/Worktree
3. แปลงคำขอเป็น structured diagnosis ที่มี project, goal, phase, domains, risks, signals, allowed paths, forbidden actions, deliverables และ evidence gates
4. เรียก agent_center_validate เพื่อตรวจสมุดรายชื่อ แล้วใช้ agent_center_route เพื่อสร้าง Team Manifest และ Work Packet
5. บังคับ THINK_PAIR และ BUILD_REVIEW ตามผลเครื่องมือ ห้ามลดเหลือยี่ห้อเดียวเงียบ ๆ
6. ตรวจ Work Packet ด้วย agent_center_validate ก่อนลงมือ
7. ให้ AI ในแอปปัจจุบันลงมือได้เมื่อพื้นที่และขอบเขตผ่าน ใช้ Use AI Relay เฉพาะเมื่อเจ้าของเรียกชัดเจน
8. ผลผ่านต้องมาจาก test/lint/build/manual evidence จริง ไม่ใช่คำบอกของ AI
9. การเทรน Agent/Skill ให้สร้าง training candidate เท่านั้น ห้ามเลื่อนขั้นหรือเขียน Obsidian ถาวรอัตโนมัติ

ผลลัพธ์ขั้นต่ำ:
- ใบวินิจฉัยงาน
- Team Manifest: leads, specialists, skills, reasons
- Work Packet: packet_id, scope, four seats, deliverables, evidence gates
- Decision: route_ready หรือ blocked พร้อมเหตุผลและขั้นตอนถัดไปหนึ่งข้อ
```

## Runtime source

ขั้นตอนฉบับใช้งานจริงอยู่ที่ `skills/agent-center/SKILL.md` และเครื่องมือทั้ง 6 ตัวมาจากปลั๊กอิน `plugins/agent_center/` ใน Hermes Agent

## Safety

- ไม่แก้แกน Hermes Agent ผ่าน Shortcut นี้
- ไม่บังคับ AI Relay
- ไม่ติดตั้งโปรไฟล์ Agent จากสมุดรายชื่อ
- ไม่เขียนความรู้ถาวรหรือส่งข้อมูลลับ
- ไม่ commit, push, merge หรือ deploy โดยไม่มีด่านเฉพาะและคำอนุมัติ
