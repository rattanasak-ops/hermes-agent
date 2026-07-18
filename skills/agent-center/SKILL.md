---
name: agent-center
description: Diagnose a project task, select a suitable Hermes Agent team and skill set, and produce a deterministic Team Manifest and Work Packet through the bundled Agent Center tools. Use when the owner says "Use Agent", asks Hermes to choose an AI team, asks which agents or skills fit a task, or needs a governed four-seat planner/worker/reviewer packet before execution.
---

# Agent Center

Use Agent Center as the single entry point for choosing a Hermes Agent team. Keep diagnosis in the current AI, keep team selection deterministic in the bundled plugin, and keep execution in the Git workspace already open by the owner.

## Operating boundaries

- Work only in the current Git root and branch. Never create, move, delete, or switch a branch or Worktree.
- Read the repository's `AGENTS.md` and the project memory files required there before diagnosing the task.
- Treat `Use AI Relay` as optional. Invoke it only when the owner explicitly asks for Relay or another AI.
- Never install the catalog entries as runtime profiles. They are logical team and skill records in this phase.
- Never write durable Obsidian knowledge automatically. Prepare a training candidate first and wait for owner approval before using the approved review-queue bridge.
- Treat machine checks and repository tests as the acceptance evidence. An AI opinion is not a passing gate.

## Workflow

### 1. Inspect the current workspace

Record the Git root, branch, SHA, dirty paths, project rules, current phase, allowed paths, forbidden actions, required outputs, and evidence gates. Stop with `CURRENT_WORKSPACE_BLOCKED` when the branch is shared/production, the target is outside the Git root, ownership is unclear, or a secret path is involved.

### 2. Build a structured diagnosis

Translate the owner's request into this object before calling the router:

```json
{
  "project_id": "project-slug",
  "goal": "plain-language outcome",
  "phase": "discovery|design|build|review|release",
  "domains": ["ui-web-design", "quality"],
  "risk_tags": ["brand-drift"],
  "signals": ["public-site"],
  "project_context_refs": [".project/plan.md"],
  "allowed_paths": ["apps/web/**"],
  "forbidden_actions": ["deploy production"],
  "deliverables": ["implementation", "test evidence"],
  "evidence_gates": ["targeted tests", "visual check"]
}
```

Use only domain IDs returned by `agent_center_validate` or `agent_center_list_skills`. The built-in domain IDs cover discovery, business/product, creative/brand, graphic, UX, web UI, motion, design systems, web engines, engineering, quality, and knowledge/training.

### 3. Check the catalog

Call `agent_center_validate` with no packet or receipt. Continue only when it returns `catalog_valid`. Use these tools for inspection when needed:

- `agent_center_list_agents` — list or filter logical team roles.
- `agent_center_get_agent` — inspect one role in detail.
- `agent_center_list_skills` — list or filter skill records.

Do not replace catalog results with a team invented from memory.

### 4. Assemble the four seats

Provide `agent_center_route` with the diagnosis plus the available healthy seat pool, current provider ID, and current session ID. Each seat record needs a provider ID, session ID, health state, and supported roles.

The router enforces:

- `planner_primary` and `planner_challenger` use different provider families.
- `worker` and `reviewer` use different provider families and sessions.
- `reviewer` is read-only.
- all four seats use distinct sessions.

If the pool cannot satisfy the rules, return the router's blocked result and reason. Never silently weaken the two-provider or worker/reviewer separation policy.

### 5. Return the routing result

Present both machine output and a short owner-facing summary:

```text
Team Manifest
- Leads:
- Specialists:
- Skills:
- Selection reasons:

Work Packet
- Packet ID:
- Goal / phase:
- Allowed paths:
- Forbidden actions:
- Four seats:
- Deliverables:
- Evidence gates:

Decision
- route_ready | blocked
- Recommended next action:
```

Validate the packet with `agent_center_validate` before execution. Do not start work from an invalid packet.

### 6. Execute in the approved channel

When the current workspace and path scope are approved, let the AI in the current app execute the packet directly. Use AI Relay only after an explicit owner request. Keep commit, push, merge, deployment, dependency installation, external communication, spending, and destructive actions behind their separate approval gates.

### 7. Capture training evidence without promotion

When real feedback or gate evidence may improve an agent or skill, call `agent_center_prepare_training_candidate`. Return the candidate ID, suggested review path, and Markdown draft to the owner. Do not write it or promote it automatically. After explicit approval, use only the approved Obsidian review-queue bridge.

## Failure handling

- Invalid diagnosis: correct the structured fields and call once more.
- Invalid catalog: stop and report catalog validation errors.
- Unsatisfied seat policy: return `blocked` with the missing provider/session capability.
- Invalid packet or receipt: do not execute or record it.
- Same error class three times: stop, summarize the evidence, and ask one precise question.

## Verification checklist

- [ ] Current Git root, branch, SHA, dirty paths, and path scope are known.
- [ ] Catalog validation returns `catalog_valid`.
- [ ] Team selection comes from `agent_center_route`.
- [ ] Team Manifest and Work Packet are both present.
- [ ] Four-seat policies pass without weakening.
- [ ] Work Packet validation passes before execution.
- [ ] Real test, lint, build, or manual evidence is attached to completion claims.
- [ ] Training candidates remain pending until owner approval.
