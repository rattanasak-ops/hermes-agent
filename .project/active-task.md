# Active Task — SCG-P9-I4

> สร้างจาก .project/active-task.json · ห้ามแก้ไฟล์นี้เป็นแหล่งข้อมูลหลัก
> goal_hash: `5fc4330ffb27805ef8cb4d6013f65c33dabfe657facf67bb4b4a0eb5c1c4df18`
> status: `active` · branch: `codex/scg-goal-contract-core` · base: `f6408b2992df8c3fcc12ebd80841bb718d5c6607`

## เป้าหมาย

นำ Goal Contract และชุด Shortcut รุ่น 2026.07.19-12 เข้า main โดยไม่ปะปนงานจากกิ่งเก่า

## ผลที่ต้องส่ง

- คำขอรวมงานไม่เกิน 30 ไฟล์
- ชุดตรวจผ่าน
- ไม่ลบไฟล์จาก main โดยไม่ได้ตั้งใจ

## เส้นทางที่อนุญาต

- `.project/active-task.json`
- `.project/active-task.md`
- `.project/spec/SCG-GOAL-DRIFT.md`
- `agent/conversation_loop.py`
- `agent/next_action_contract.py`
- `agent/prompt_builder.py`
- `plugins/shortcut_governance/__init__.py`
- `plugins/shortcut_governance/cli.py`
- `plugins/shortcut_governance/plugin.yaml`
- `plugins/shortcut_governance/store.py`
- `scripts/plan_index_check.py`
- `scripts/shortcut_dependency_graph.py`
- `team-shortcuts/check-shortcuts.sh`
- `team-shortcuts/hooks/enforce-goal-contract.py`
- `team-shortcuts/hooks/enforce-memory-receipt.py`
- `team-shortcuts/hooks/enforce-phase-autonomy.py`
- `team-shortcuts/hooks/enforce-shortcut-central.py`
- `team-shortcuts/hooks/enforce-spec-gate.py`
- `team-shortcuts/hooks/goal_contract.py`
- `team-shortcuts/hooks/goal_evidence.py`
- `team-shortcuts/hooks/memory_receipt.py`
- `team-shortcuts/hooks/phase_state.py`
- `team-shortcuts/hooks/record-spec-owner.py`
- `team-shortcuts/hooks/team-stop-gates.py`
- `team-shortcuts/hooks/validate-thai-language.py`
- `team-shortcuts/install-team-hooks.py`
- `team-shortcuts/team-hook-doctor.py`
- `team-shortcuts/verify-bundle.py`
- `tests/team_shortcuts/test_goal_contract.py`
- `tests/team_shortcuts/test_goal_contract_hook.py`

## Prompt ถัดไป

AUTO_CONTINUE: เพิ่ม Workflow และชุดตรวจหลังบัญชี GitHub มีสิทธิ์ workflow
