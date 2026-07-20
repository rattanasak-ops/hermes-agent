# Active Task — SCG-P9-I4

> สร้างจาก .project/active-task.json · ห้ามแก้ไฟล์นี้เป็นแหล่งข้อมูลหลัก
> goal_hash: `c9779b16874b8cd84585837c1ab538fc534dc3beb46b83a4ea72e8aca4c22556`
> status: `active` · branch: `codex/scg-shortcut-rollout` · base: `247bf0006e2bff7b8870222be6d36d34b489e580`

## เป้าหมาย

นำ Goal Contract และชุด Shortcut รุ่น 2026.07.19-12 เข้า main โดยไม่ปะปนงานจากกิ่งเก่า

## ผลที่ต้องส่ง

- คำขอรวมงานไม่เกิน 30 ไฟล์
- ชุดตรวจผ่าน
- ไม่ลบไฟล์จาก main โดยไม่ได้ตั้งใจ

## เส้นทางที่อนุญาต

- `.project/active-task.json`
- `.project/active-task.md`
- `team-shortcuts/VERSION`
- `team-shortcuts/install-shortcuts.sh`
- `team-shortcuts/payload/ai-context/prompt-shortcut-registry.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/Prompt Shortcuts.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/SKILL.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/goal-contract.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/next-action-contract.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-act-as.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-agent.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-close-chat.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-comply.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-continue.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-create-design-system.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-flow-guardian.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-migrate-web.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-new-chat.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-qa-qc.md`
- `team-shortcuts/payload/skills/prompt-shortcuts/references/use-save-git.md`
- `team-shortcuts/sync-from-vault.sh`
- `team-shortcuts/BUNDLE-MANIFEST.json`
- `tests/run_agent/test_run_agent.py`
- `tests/team_shortcuts/test_bundle_manifest.py`
- `tests/team_shortcuts/test_goal_contract_distribution.py`
- `tests/team_shortcuts/test_goal_drift_real_incidents.py`
- `tests/team_shortcuts/test_goal_shortcut_chain.py`
- `tests/team_shortcuts/test_new_chat_write_permit.py`
- `tests/team_shortcuts/test_phase_goal_contract.py`
- `tests/team_shortcuts/test_team_shortcut_distribution.py`
- `tests/team_shortcuts/test_phase_distribution.py`

## Prompt ถัดไป

AUTO_CONTINUE: ตรวจและรวมกิ่ง codex/scg-shortcut-rollout
