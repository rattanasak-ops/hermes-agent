---
name: prompt-shortcuts
description: Use this skill when the user invokes any reusable prompt shortcut from HermesAgent, including "Use Act-As", "Use Comply", "Use Summary", "Use Scan Feature", "Use AI Relay", "Use Agent", "Use Viber Structure", "Use Viber Audit", "Use Impeccable", "Use Blog Auto", "Use WOW Resource", "Use Flow Guardian", "Use New Chat", "Use Migrate Web", "Use Close Chat", "Use Save Git", "Use Merge to Production", "Use Continue", "Use Move Folder", "Review Chat", "Use AI Pair", "Use Business Plan", "Use SaaS Opus Master Prompt", "Use BusinessPlan", "Use OverviewProgress", "Use FeatureSpec", "Use DesignSystem", "Use Create Design System", "Use Hermes Structure", "Use Create Content", "Use SonarQube", or Thai/alias variants such as "ใช้ AI Relay", "จัดทีม AI", "ปิดแชท", "เซฟ Git", "ทำต่อ", "รีวิวแชท", "สร้างคอนเทนต์จากแชท", "สร้างไฟล์ภาพรวมงาน", and "สแกน SonarQube".
metadata:
  short-description: Reusable prompt shortcut loader
---

# Prompt Shortcuts

This skill loads standard reusable prompts from HermesAgent. The v2 prompt files in `references/` are the source of truth; do not paraphrase them when the user asks to use a shortcut.

Before applying any mapped prompt, read and enforce `references/next-action-contract.md`. This shared contract applies to every Shortcut, so individual prompt files do not need duplicate closing rules.

## Shortcut Map

| Shortcut | Aliases | Prompt File |
| --- | --- | --- |
| `Use Act-As` | `use-act-as`, `Use Act As`, `Act-As`, `act-as`, `ใช้ Act-As`, `กำหนดบทบาท`, `เรียกทีมผู้เชี่ยวชาญ` | `references/use-act-as.md` |
| `Use Comply` | `use-comply`, `Comply`, `comply`, `ใช้ Comply`, `ทำ Comply`, `แตกเฟส`, `ทำตารางเปอร์เซ็นต์` | `references/use-comply.md` |
| `Use Summary` | `use-summary`, `Summary`, `summary`, `ใช้ Summary`, `สรุป`, `สรุปลิงก์`, `วิเคราะห์บทความ`, `สรุปข้อมูล` | `references/use-summary.md` |
| `Use Scan Feature` | `use-scan-feature`, `Scan Feature`, `scan-feature`, `สแกนฟีเจอร์`, `ตรวจฟีเจอร์`, `บัญชีฟีเจอร์` | `references/use-scan-feature.md` |
| `Use AI Relay` | `use-ai-relay`, `AI Relay`, `ai-relay`, `ใช้ AI Relay`, `สายพาน AI`, `สายพานส่งต่องาน AI`, `Claude วางแผน Grok โค้ด`, `ให้ AI ตัวอื่นโค้ดแล้ว Claude ตรวจ` | `references/use-ai-relay.md` |
| `Use Agent` | `use-agent`, `ใช้ Agent`, `จัดทีม AI`, `เลือกทีม AI` | `references/use-agent.md` |
| `Use Viber Structure` | `use-viber-structure`, `Viber Structure`, `viber-structure`, `ใช้ Viber Structure`, `โครงสร้าง Viber`, `วางโครงสร้าง Viber Code`, `วางแผน Viber Code`, `Vibe Code Enterprise` | `references/use-viber-structure.md` |
| `Use Viber Audit` | `use-viber-audit`, `Viber Audit`, `viber-audit`, `Use Viber Standard Audit`, `Use Viber Compliance`, `ใช้ Viber Audit`, `ตรวจ Viber Standard`, `ตรวจ Viber Enterprise`, `ตรวจมาตรฐาน Viber`, `Viber Enterprise Standard` | `references/use-viber-audit.md` |
| `Use Impeccable` | `use-impeccable`, `Impeccable`, `ใช้ Impeccable`, `ตรวจ UI Slop`, `แก้ AI Slop` | `references/use-impeccable.md` |
| `Use Blog Auto` | `use-blog-auto`, `Blog Auto`, `blog-auto`, `ใช้ Blog Auto`, `เขียนบล็อกอัตโนมัติ`, `ทำบล็อกจากงานนี้`, `ส่งเข้า One Man Fleet` | `references/use-blog-auto.md` |
| `Use WOW Resource` | `use-wow-resource`, `WOW Resource`, `wow-resource`, `ใช้ WOW Resource`, `ใช้ WOW`, `WOW Layout`, `WOW Menu`, `WOW Script`, `WOW Design`, `WOW Web Engine` | `references/use-wow-resource.md` |
| `Use Flow Guardian` | `use-flow-guardian`, `Flow Guardian`, `Safe Flow`, `New Chat Gate`, `ใช้ Flow Guardian`, `ใช้ Safe Flow`, `เปิด Flow Guardian`, `ตรวจ worktree`, `กัน AI แก้งานทับกัน` | `references/use-flow-guardian.md` |
| `Use New Chat` | `use-new-chat`, `Start New Chat`, `New Chat Startup`, `Initialize Hermes Agent chat`, `เริ่ม New Chat`, `เปิด New Chat`, `เริ่มแชทใหม่`, `เปิดแชทใหม่` | `references/use-new-chat.md` |
| `Use Migrate Web` | `use-migrate-web`, `Migrate Web`, `migrate-web`, `ใช้ Migrate Web`, `ย้ายเว็บตาม Flow`, `ทำเว็บ 13 ขั้น`, `Flow ย้ายเว็บ` | `references/use-migrate-web.md` |
| `Use Migrate 0` … `Use Migrate 13` | `use-migrate-0` … `use-migrate-13`, `ใช้ Migrate <เลข>` | `references/use-migrate-<เลข>.md` + `references/use-migrate-phase-contract.md` |
| `Use Close Chat` | `use-close-chat`, `Close Chat`, `close-chat`, `Use Post Chat`, `use-post-chat`, `Post Chat`, `ใช้ Close Chat`, `ปิดแชท`, `ปิดงานแชท`, `จบแชท` | `references/use-close-chat.md` |
| `Use Save Git` | `use-save-git`, `Save Git`, `save-git`, `Save Grid`, `save-grid`, `Use Save Grid`, `ใช้ Save Git`, `เซฟ Git`, `ก่อน push`, `ก่อน merge`, `ก่อน deploy`, `Git Safe Flow`, `GitLab Deploy Safe Flow`, `Use GitLab Deploy Safe Flow`, `Use Ship Gate` | `references/use-save-git.md` |
| `Use Merge to Production` | `use-merge-to-production`, `Merge to Production`, `merge-to-production`, `ใช้ Merge to Production`, `ขึ้น production`, `deploy production`, `Ship to Production` | `references/use-merge-to-production.md` |
| `Use Continue` | `use-continue`, `Continue`, `continue`, `ทำต่อ`, `ทำต่อเอง`, `ทำงานต่อ`, `ทำต่ออัตโนมัติ`, `ไม่ต้องรอผม`, legacy: `Go to Sleep`, `go-to-sleep`, `Sleep Mode`, `sleep-mode`, `เข้าโหมดนอน`, `โหมดนอน` | `references/use-continue.md` |
| `Use Move Folder` | `use-move-folder`, `Move Folder`, `move-folder`, `movefolder`, `ใช้ Move Folder`, `ย้ายโฟลเดอร์`, `จัดเรียง Folder`, `จัดเรียงโฟลเดอร์` | `references/use-move-folder.md` |
| `Review Chat` | `review-chat`, `Chat Review`, `chat-review`, `รีวิวแชท`, `ตรวจแชท`, `สรุปส่งต่อ`, `สรุปเปิดแชทใหม่` | `references/review-chat.md` |
| `Use AI Pair` | `use-ai-pair`, `AI Pair`, `ai-pair`, `Use Pair AI`, `Pair AI`, `pair-ai`, `ใช้ AI Pair`, `ใช้ Pair AI`, `จับคู่ AI เขียนตรวจ`, `ทีม AI สามตัว` | `references/use-ai-pair.md` |
| `Use Business Plan` | `use-business-plan`, `Business Plan`, `business-plan`, `ใช้ Business Plan`, `รีวิวโจทย์ธุรกิจ`, `วางแผนธุรกิจ`, `วางแผนการตลาด`, `วางแผน Pitch`, `งานประมูล` | `references/use-business-plan.md` |
| `Use SaaS Opus Master Prompt` | `use-saas-opus-master-prompt`, `SaaS Opus Prompt`, `Opus SaaS Plan`, `Opus SaaS Master Prompt`, `ส่ง prompt SaaS Opus`, `prompt วางแผน SaaS`, `prompt ธุรกิจ SaaS`, `prompt pitch SaaS`, `prompt SaaS แบบละเอียดที่สุด` | `references/use-saas-opus-master-prompt.md` |
| `Use BusinessPlan` | `use-businessplan`, `Use BusinessPlan File`, `Use Project BusinessPlan`, `BusinessPlan File`, `ใช้ BusinessPlan`, `สร้างไฟล์แผนธุรกิจ`, `สแกนแผนธุรกิจ project`, `อัปเดตแผนธุรกิจ project` | `references/use-businessplan.md` |
| `Use OverviewProgress` | `use-overviewprogress`, `Use Overview Progress`, `ใช้ OverviewProgress`, `สร้างไฟล์ภาพรวมงาน`, `อัปเดตภาพรวม project`, `ภาพรวมความคืบหน้า` | `references/use-overviewprogress.md` |
| `Use FeatureSpec` | `use-featurespec`, `Use Feature Spec`, `ใช้ FeatureSpec`, `สแกนฟีเจอร์ project`, `บัญชีฟีเจอร์`, `อัปเดตรายการฟีเจอร์` | `references/use-featurespec.md` |
| `Use DesignSystem` | `use-designsystem`, `Use Design System File`, `ใช้ DesignSystem`, `สร้างไฟล์ Design System`, `อัปเดต Design System project`, `ตรวจดีไซน์ตามมาตรฐาน` | `references/use-designsystem.md` |
| `Use Create Design System` / `Use Design System` | `use-create-design-system`, `Create Design System`, `create-design-system`, `Use Design System`, `use-design-system`, `ใช้ Design System`, `ใช้ Create Design System`, `สร้าง Design System`, `ทำ Design System มาตรฐาน`, `วาง Design System ให้โปรเจกต์` | `references/use-create-design-system.md` |
| `Use Hermes Structure` | `use-hermes-structure`, `Hermes Structure`, `ใช้ Hermes Structure`, `มาตรฐานกลาง Hermes` | `references/use-hermes-structure.md` |
| `Use Create Content` | `use-create-content`, `Create Content`, `create-content`, `ใช้ Create Content`, `สร้างคอนเทนต์จากแชท`, `แปลงแชทเป็นคอนเทนต์`, `ทำ Content Master` | `references/use-create-content.md` |
| `Use QA QC` / `Use QC QA` | `use-qa-qc`, `use-qc-qa`, `Use QAQC`, `Use QCQA`, `QA QC`, `QC QA`, `ใช้ QA QC`, `ใช้ QC QA`, `ตรวจคุณภาพงาน`, `สแกนคุณภาพโปรเจกต์`, `สแกน QA`, `ตรวจงานก่อนส่งมอบ` | `references/use-qa-qc.md` |
| `Use SonarQube` | `use-sonarqube`, `SonarQube`, `ใช้ SonarQube`, `สแกน SonarQube`, `ตรวจโค้ดด้วย SonarQube` | `references/use-sonarqube.md` |

## How To Use

When the user invokes a shortcut:

1. Read `references/next-action-contract.md` and `references/work-execution-policy.md` first, then read the mapped prompt file in full. Read `references/worktree-lifecycle-contract.md` only when the owner explicitly asks to create, hand off, close, inspect, or clean up a Worktree.
2. Apply the prompt to the user's current task or the task text that follows the shortcut.
3. If the shortcut is invoked without a target task, ask what task the user wants to apply it to.
4. Follow any safety or approval constraints inside the loaded prompt exactly. If an older prompt creates/switches a branch or Worktree, requires `NEW_CHAT_READY`/`WTL_READY`, or forces AI Relay, Work Execution Policy v2 takes precedence.

## Current Workspace Gate

ทุก Shortcut ใช้โหมด `CURRENT_WORKSPACE_ONLY` จาก `references/work-execution-policy.md` รุ่นเดียวกัน:

- Shortcut ใช้เฉพาะ Git root และกิ่งที่แอปเปิดอยู่
- Shortcut ห้ามสร้าง ลบ ย้าย หรือสลับ Worktree/กิ่งเอง และห้ามเรียก `hermes-new-chat open` หรือ `hermes worktree open`
- `OWNER_EXPLICIT_BRANCH_ONLY`: เมื่อข้อความสั้นล่าสุดจากเจ้าของระบุให้สร้างกิ่งพร้อมชื่อชัดเจน AI จึงสร้างกิ่งชื่อนั้นใน Git root ปัจจุบันได้หนึ่งครั้งโดยไม่สร้าง Worktree และไม่ผลักให้เจ้าของใช้ Terminal; ข้อความตัวอย่างยาวและชื่อที่ AI คิดเองไม่ให้สิทธิ์
- `SYSTEM_REGISTERED_BRANCH_RECOVERY`: ใช้เฉพาะเมื่อ Git root ตรงงานและหลุด detached HEAD ให้ AI รัน `hermes-current-workspace-recover --cwd <Git root> --json` เพื่อกู้กิ่งตามสมุดทะเบียนในพื้นที่เดิม ห้ามสร้าง Worktree ห้ามเดาชื่อกิ่ง และห้ามผลักให้ผู้ใช้เปิดพื้นที่/กิ่งเอง; กิ่งร่วมต้องคืน `PROTECTED_BRANCH_WRITE_BLOCKED` โดยไม่สลับกิ่ง
- ก่อนเขียนต้องตรวจ path/branch/SHA/dirty และต้องไม่ใช่กิ่งร่วม กิ่งใช้งานจริง หรือ detached HEAD
- AI ในแอปปัจจุบันเขียนตรงได้; AI Relay เป็นทางเลือกเมื่อเจ้าของเรียกเท่านั้น
- `.env`, `.hermes`, `.grok`, secret, การเขียนข้าม Git root และคำสั่งอันตรายยังถูกขวาง
- Decision token กลางคือ `CURRENT_WORKSPACE_READY`, `CURRENT_WORKSPACE_READ_ONLY`, `CURRENT_WORKSPACE_BLOCKED`
- Worktree Lifecycle v1 เป็นส่วนเสริมสำหรับตรวจและจัดการ Worktree ที่มีอยู่โดยกระบวนการของเจ้าของ ด่าน AI ไม่เปิด Worktree ใหม่

## Important Behavior

For `Use Act-As`, the loaded prompt requires deep role definition and work decomposition, and explicitly says not to create files until the user approves. Respect that constraint even if the surrounding task sounds implementation-ready.

For `Use Comply`, build phase-level plans with detailed issue checklists, numeric completion percentages, and localhost/VPS verification before delivery. Label every issue `ZONE_A` (safe work the AI continues autonomously inside the approved task/worktree scope) or `ZONE_B` (work requiring grouped phase-level owner approval); only verified evidence counts as 100%, finish unblocked Zone A work first, and never ask for approval issue by issue.

For `Use Summary`, summarize and analyze user-provided links plus content, present routing options first, and do not write to memory, KITS, registry, or files until the owner approves unless the owner explicitly says to choose and proceed.

For `Use Scan Feature`, scan the real repository phase by phase, refuse to claim any feature without reading evidence, label every capability as real/partial/mock/planned/blocked/unknown, stop at every required gate, and produce only a Thai feature/capability extraction document. Do not create marketing, SWOT, pricing, GTM, or roadmap output under this shortcut.


For `Use AI Pair`, treat it as a compatibility alias for an explicitly requested multi-AI review. The AI in the current app may write directly in the current workspace when it is ready; AI Relay is optional and must not be introduced unless the owner requested another AI. Keep every reviewer read-only and use real tests/CI as the final evidence. No paired AI may create or switch a branch/Worktree.

For `Use AI Relay`, load `references/use-ai-relay.md` and `references/ai-relay-catalog.md`. Honor the owner's mode from Use New Chat without asking twice: mode 1 assigns separate AIs to study/plan, production, and review; mode 2 uses a primary AI to produce the study/analysis output and a second AI to review it before acceptance. If no mode was supplied, use mode 1 and report that default instead of stopping for another confirmation. Every code call is confined to the current Git root, current branch, and owner-approved path scope. Reviewers stay read-only against the same path/SHA. Relay must never create, discard, move, or switch a branch/Worktree, and it must not require a New Chat session. Fable/Faber/Fiber 5 is removed from the active path. Use `relay-call --role review` for AI reviews so Codex is read-only, silence alone does not stop it, one compact retry stays under the same issue, retry suffixes cannot reset counters, and concurrent duplicate work returns `already_running`. The same reviewer plus review method may fail at most twice per root issue; after that split the findings and switch to deterministic gates or a different-vendor reviewer, never a third identical review. Use `gate-run` for real verification; never treat an AI claim or partial timeout output as verified without a gate row.

For `Use Agent`, load `references/use-agent.md` and the in-repo `skills/agent-center/SKILL.md` when available. It supports thinking, analysis, planning, design, build, review, and training; never reject it merely because the task has no code or build step. Diagnose the task, validate the catalog, and use the Agent Center route tool to return a Team Manifest plus Work Packet. Require the cross-provider planner pair for every execution mode; activate the separate worker/reviewer pair only for `build`. A route assigns seats but does not prove that they ran: invoke every active seat through a real agent/subagent capability, preserve each output reference, and validate the version-2 receipt together with its original packet. If a real cross-provider pair cannot be called, return `THINK_PAIR_EXECUTION_UNAVAILABLE`; never fabricate a cross-check. Keep durable knowledge pending owner review, work only in the current workspace, and use AI Relay only when the owner explicitly requests it. If the runtime is missing, return `AGENT_CENTER_UNAVAILABLE` with evidence instead of inventing a scope restriction.

For `Use Business Plan`, review the owner's raw business/marketing/pitch/tender/website question before execution, choose the right business modules and expert roles, build phase and issue checklists, ask for missing inputs first, and do not create files or durable writes until approved.

For `Use SaaS Opus Master Prompt`, send the owner-approved detailed one-file Opus 4.8 master prompt for SaaS business, product, marketing, pricing, pitch, WOW proof, and portfolio decision work. Do not replace it with a short summary.

For `Use Viber Structure`, turn the Viber Code / Vibe Code Enterprise playbook into a project structure, artifact matrix, phase/issue tracker, and quality-gate plan. Require spec before code, numeric compliance, and real verification evidence before claiming completion.

For `Use Viber Audit`, inspect one or many real Viber Project repos against the full Viber Enterprise Standard, score artifact/gate/tracking/verification coverage from evidence only, identify missing critical work, and create or update per-project tracking when authorized.

For `Use Impeccable`, use exactly one owner-facing shortcut for Impeccable UI quality work. Read the mapped prompt, infer the target from context when possible, ask one short target question only when needed, and let the AI choose whether to install, scan, explain, fix blocking UI issues, or plan UI-debt cleanup. Do not expose multiple Impeccable sub-shortcuts to the owner.

For `Use Blog Auto`, extract useful work knowledge into a One Man Fleet blog route, run privacy review first, decide whether to create a new post or update an existing one, use English public plus Thai internal summary by default, create only drafts until owner approval, record Obsidian index/traceability, and hand off platform drafts to Content Factory without auto-posting.

For `Use WOW Resource`, read the mapped prompt, route through WOW System and Web Design Intelligence, select resources based on the project goal, reject mismatched/generic options, and transform the selected patterns into project-specific layout/design/script direction. Do not copy scripts or visual patterns directly.

For `Use Flow Guardian`, inspect and report the current folder, Git root, branch, SHA, dirty state, target paths, secret-path safety, and overlap risk. Return a current-workspace decision without creating, switching, moving, or deleting a branch/Worktree. Require no-write audit, approval gates, verification, tracking, and handoff when applicable.

For `Use New Chat`, inspect only the workspace and branch already open in the app. Read project memory, branch, SHA, dirty state, target paths, and hook health, then return `CURRENT_WORKSPACE_READY`, `CURRENT_WORKSPACE_READ_ONLY`, or `CURRENT_WORKSPACE_BLOCKED`. It must never call `hermes-new-chat open`, create/switch a Worktree, or treat the shortcut invocation as permission to do so. If the exact Git root is detached, run `SYSTEM_REGISTERED_BRANCH_RECOVERY` before blocking. A protected branch returns `PROTECTED_BRANCH_WRITE_BLOCKED` without changing branches. A separate short owner command naming an exact branch follows `OWNER_EXPLICIT_BRANCH_ONLY`. Never ask the user to open or create a workspace, Worktree, folder, or branch. Report AI Relay as optional unless the owner invoked it explicitly.

For `Use Migrate 0` through `Use Migrate 13`, read `references/use-migrate-phase-contract.md` and the exact numbered phase file. The owner advances phases by number. These phases still obey `CURRENT_WORKSPACE_ONLY`; they may lock a menu inside the current branch but may not create or switch a branch/Worktree.

For `Use Close Chat` and its full alias `Use Post Chat`, load the same `references/use-close-chat.md` file. Run preview then close/write only after every explicitly requested merge, main, VPS, and team rollout phase is finished or genuinely blocked by external authority. Do not write premature closeout files into an active code delivery. Reuse a matching Save Git receipt instead of repeating heavy gates, but always run fresh Git status. Seal all memory targets under one close_id and verify the final memory receipt. Return CLOSED_CLEAN, CLOSED_WITH_PENDING, or NEED_OWNER_ACTION_BEFORE_CLOSE; it does not push, merge, or deploy.

For `Use Save Git` (including `Save Grid`), run the Git/GitLab/VPS gate only before commit, push, merge, deploy, or final Git readiness claims. A gate block never permits creating or switching a branch/Worktree. Diagnose reused-branch and squash history in the current branch first. If no Git action applies, return `SAVE_GIT_NOT_APPLICABLE` without running five stages. Emit a receipt bound to project/task/branch/SHA.

For `Use Merge to Production`, treat it as a merger-only production path. Confirm the caller and target are allowed, run the Save Git merge gate and ship gate, deploy only from the approved remote/branch, and stop on any unknown state.

For `Use Continue`, continue autonomously through phases in the current workspace only, make best-judgment choices when selection is needed, require each phase to reach verified 100%, and provide a final phase percentage table for review. Split work into `ZONE_A` (safe, reversible, inside the approved current workspace and path scope; continue without per-issue approval) and `ZONE_B` (risky, scope-expanding, external, destructive, shipping, or identity-uncertain; gather into one phase-level approval request after Zone A). Once the owner approves the goal or phase, the Zone A question budget is zero until the phase gate: answer status questions, re-read the active plan, then resume the same phase. Only an evidence-backed `OWNER_INPUT_REQUIRED: <reason>` may pause for external access, identity, destructive, production, secret, or scope decisions, and the same question must not be repeated until machine state changes. It must not create or switch a branch/Worktree. Treat `Go to Sleep` and sleep-related names only as legacy aliases for this same behavior.

For `Use Move Folder`, load `references/use-move-folder.md`, then read the live VPS registry under `/home/linux-nat/.codex/use-move-folder/project-registry` before doing any cleanup, folder move, retention review, or disk-space work. Do not claim the shortcut is missing just because it is stored in Codex runtime state. Do not scan protected/no-touch roots or mutate anything unless the owner gives exact approval.

For `Review Chat`, route to `Use Close Chat` PREVIEW_ONLY. Review evidence and proposed memory writes but do not write files, release claims, or estimate a context percentage that the UI does not expose.

For `Use BusinessPlan`, create or update the per-project business memory files under `.project/` after reading the real repo and the existing business files. Keep it separate from `Use Business Plan`, which is the raw business-planning prompt.

For `Use OverviewProgress`, create or update `.project/OverviewProgress.md` using the Memory Schema v1.2 top sections and prove the file is not hidden by git ignore rules.

For `Use FeatureSpec`, scan the real code and record feature status as real, partial, mock, planned, blocked, or unknown with path evidence.

For `Use DesignSystem`, create or update the per-project design-system memory file. Do not confuse it with `Use Create Design System`, which builds or migrates a project-wide design system.

For `Use Create Design System`, read the project first, then apply the approved design-system standard with owner color approval and measured adoption gates before code changes.

For `Use Hermes Structure`, route the owner to the Hermes standard workflow and use the safe apply tools from the central standard set. Do not edit VPS/global files directly unless the owner approves that exact action.

For `Use Create Content`, convert the current chat or source material into a privacy-reviewed Content Master draft, then hand off to Blog Auto or the content factory without publishing.

For `Use QA QC` (or `Use QC QA`), open a two-axis quality-scan menu (project progress 25/50/75/100% × 16 check categories Q01-Q16, multi-select, Scan All last behind a confirm gate), run real project checks first, keep reviewer different from fixer when a reviewer is used, and never block direct fixes solely because AI Relay or another AI is unavailable. Only tool evidence counts as verified. Produce a severity table, then write `.project/qaqc-scan.md` before any fixes.

For `Use SonarQube`, analyze an existing project with the owner's already-installed SonarQube instance. Read the project rules, detect its build system, verify server status and credentials without revealing secrets, run the matching scanner, confirm the server-side analysis through the API, and return a Thai report. Never install or upgrade the SonarQube server through this shortcut, and never change source code without separate owner approval.

## Source Files

- `Prompt Shortcuts.md`: Obsidian index note for all shortcuts.
- `ai-context/prompt-shortcut-registry.md`: shared registry for non-Codex adapters.
- `references/use-act-as.md`: full prompt for `Use Act-As`.
- `references/use-comply.md`: full prompt for `Use Comply`.
- `references/use-summary.md`: full prompt for `Use Summary`.
- `references/use-scan-feature.md`: full prompt for `Use Scan Feature`.
- `references/use-ai-pair.md`: full prompt for `Use AI Pair`.
- `references/use-ai-relay.md`: full prompt for `Use AI Relay`.
- `references/use-agent.md`: full prompt for `Use Agent` and Agent Center routing.
- `references/ai-relay-catalog.md`: AI Relay catalog and routing rules.
- `references/work-execution-policy.md`: shared direct-write, optional-Relay, safety, and app-wiring policy.
- `references/use-business-plan.md`: full prompt for `Use Business Plan`.
- `references/use-saas-opus-master-prompt.md`: full prompt for `Use SaaS Opus Master Prompt`.
- `references/use-viber-structure.md`: full prompt for `Use Viber Structure`.
- `references/use-viber-audit.md`: full prompt for `Use Viber Audit`.
- `references/use-impeccable.md`: full prompt for `Use Impeccable`.
- `references/use-blog-auto.md`: full prompt for `Use Blog Auto`.
- `references/use-wow-resource.md`: full prompt for `Use WOW Resource`.
- `references/use-flow-guardian.md`: full prompt for `Use Flow Guardian`.
- `references/use-new-chat.md`: full prompt for `Use New Chat`.
- `references/use-close-chat.md`: full prompt for `Use Close Chat`.
- `references/use-save-git.md`: full prompt for `Use Save Git`.
- `references/use-merge-to-production.md`: full prompt for `Use Merge to Production`.
- `references/use-continue.md`: full prompt for `Use Continue`.
- `references/use-move-folder.md`: full prompt for `Use Move Folder`.
- `references/go-to-sleep.md`: legacy alias note for old `Go to Sleep` invocations.
- `references/review-chat.md`: full prompt for `Review Chat`.
- `references/use-businessplan.md`: full prompt for `Use BusinessPlan`.
- `references/use-overviewprogress.md`: full prompt for `Use OverviewProgress`.
- `references/use-featurespec.md`: full prompt for `Use FeatureSpec`.
- `references/use-designsystem.md`: full prompt for `Use DesignSystem`.
- `references/use-create-design-system.md`: full prompt for `Use Create Design System`.
- `references/use-hermes-structure.md`: full prompt for `Use Hermes Structure`.
- `references/use-create-content.md`: full prompt for `Use Create Content`.
- `references/use-qa-qc.md`: full prompt for `Use QA QC` / `Use QC QA`.
- `references/use-sonarqube.md`: full prompt for recurring `Use SonarQube` project analysis.
- `references/sonarqube-vps-install-for-cursor.md`: one-time Cursor prompt for installing SonarQube Community Build on the owner's VPS; this is not a shortcut.

## Graph Links

- Parent hub: [[skills/README|skills]]
- Router: [[00-Center/docs/AI_SKILL_ROUTER|AI Skill Router]]
- Graph: [[00-Center/docs/SKILL_GRAPH|Skill Graph]]
