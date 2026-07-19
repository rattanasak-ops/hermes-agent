---
name: agent-center
description: Diagnose and route thinking, analysis, planning, design, build, review, and training work to a suitable Hermes Agent team and skill set, then produce a deterministic Team Manifest and Work Packet through the bundled Agent Center tools. Use when the owner says "Use Agent", asks Hermes to choose an AI team, asks which agents or skills fit a task, needs two-provider thinking review, or needs separated worker/reviewer execution.
---

# Agent Center

Use Agent Center as the single entry point for choosing a Hermes Agent team. Keep diagnosis in the current AI, keep team selection deterministic in the bundled plugin, and keep execution in the Git workspace already open by the owner.

`Use Agent` is not limited to code or implementation. It must accept thinking-only, analysis-only, planning, design, review, and training tasks. Never refuse a task merely because it has no build step.

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
  "execution_mode": "think|plan|build|review|train",
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

### 4. Assemble the active seats

Provide `agent_center_route` with the diagnosis plus the available healthy seat pool, current provider ID, and current session ID. Each seat record needs a provider ID, session ID, health state, and supported roles. For runtime thinking calls, use a callable model ID as `provider_id` (for example `anthropic/claude-opus-4.6` or `openai/gpt-5.4`) and use a unique logical run ID as `session_id`; these bounded calls are not resumable Hermes child sessions. Set `execution_mode` explicitly when the task intent is known; otherwise the router derives a compatible default from `phase`.

The router enforces:

- `planner_primary` and `planner_challenger` use different provider families.
- `think`, `plan`, `review`, and `train` activate the planner pair only. They do not authorize code or build work.
- `build` additionally activates `worker` and `reviewer` on different provider families and sessions.
- the build reviewer is read-only.
- all active seats use distinct sessions.

If the pool cannot satisfy the active mode, return the router's blocked result and reason. Never invent a rule that thinking is forbidden. Never silently weaken the two-provider or worker/reviewer separation policy.

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
- Execution mode / active seats:
- Deliverables:
- Evidence gates:

Decision
- route_ready | blocked
- Recommended next action:
```

Validate the packet with `agent_center_validate` before execution. Do not start work from an invalid packet.

### 6. Execute in the approved channel

The route result assigns seats; it does not prove that any assigned AI actually ran. Call `agent_center_execute` with the validated packet and the owner's request. The tool invokes fresh sessions through the owner's logged-in subscriptions: Codex uses ChatGPT login, Claude uses first-party OAuth, and Grok uses Hermes xAI OAuth. It never accepts a provider override, reads an API key, or routes through AI Relay. The tool preserves output text plus a SHA-256 fingerprint for each active seat, asks a fresh primary session to reconcile planner disagreement, and returns a packet-bound version-2 receipt. Completion requires `receipt_runtime_valid`; `receipt_structural_valid` checks identities and shape only and is not proof that the agents ran. Never fabricate a seat output or a cross-check. If a subscription is unavailable, return the blocked result and route again using a healthy family.

For `think`, `plan`, `review`, or `train`, return the cross-checked analysis or decision without requiring a branch, code change, worker, or build approval. For `build`, the tool requires a clean approved workspace plus non-empty `allowed_paths`, runs a writable Codex or Claude worker, checks changed paths, and then runs a separate read-only reviewer. The worker and reviewer must remain different sessions and provider families. The tool does not commit, push, merge, deploy, install dependencies, or contact external systems. Use AI Relay only after an explicit owner request.

Validate completion by sending the original packet and its receipt together to `agent_center_validate`. A receipt alone is not completion evidence. Version 1 packets/receipts must be routed again under schema 2; never infer build authority from a missing mode or version.

If Agent Center tools are unavailable, report `AGENT_CENTER_UNAVAILABLE` with the missing skill/plugin/tool evidence. Do not replace a missing runtime with a fabricated policy such as "Use Agent cannot think."

### 7. Capture training evidence without promotion

When real feedback or gate evidence may improve an agent or skill, call `agent_center_prepare_training_candidate`. Return the candidate ID, suggested review path, and Markdown draft to the owner. Do not write it or promote it automatically. After explicit approval, use only the approved Obsidian review-queue bridge.

## Failure handling

- Invalid diagnosis: correct the structured fields and call once more.
- Unsupported execution mode: return the accepted modes and correct the diagnosis once.
- Missing Agent Center runtime: return `AGENT_CENTER_UNAVAILABLE`; never invent a scope restriction.
- Assigned cross-provider seat cannot be called: return `THINK_PAIR_EXECUTION_UNAVAILABLE`; never fabricate evidence.
- Build packet without a clean workspace or allowed paths: return the matching build blocker before starting the worker.
- Subscription quota or login failure: return `SUBSCRIPTION_SEAT_EXECUTION_FAILED`, mark that family unhealthy, route once more with the approved fallback family, and never switch the packet identity silently.
- Invalid catalog: stop and report catalog validation errors.
- Unsatisfied seat policy: return `blocked` with the missing provider/session capability.
- Invalid packet or receipt: do not execute or record it.
- Same error class three times: stop, summarize the evidence, and ask one precise question.

## Verification checklist

- [ ] Current Git root, branch, SHA, dirty paths, and path scope are known.
- [ ] Catalog validation returns `catalog_valid`.
- [ ] Team selection comes from `agent_center_route`.
- [ ] Team Manifest and Work Packet are both present.
- [ ] Execution mode matches the owner's requested outcome.
- [ ] THINK_PAIR passes for every mode; BUILD_REVIEW passes only when mode is `build`.
- [ ] Work Packet validation passes before execution.
- [ ] Non-build planner pairs run through `agent_center_execute`; build work uses a tool-capable worker channel.
- [ ] Every active seat has a real output reference and the receipt is validated together with the original packet.
- [ ] Real test, lint, build, or manual evidence is attached to completion claims.
- [ ] Training candidates remain pending until owner approval.
