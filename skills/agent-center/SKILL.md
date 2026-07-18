---
name: agent-center
description: Select and validate an AI team, specialist roles, skill set, and review path from the bundled Agent Center catalog. Use when the user invokes Use Agent, asks which AI or specialist should handle a task, requests a cross-provider team, or wants to prepare a training candidate for owner review.
---

# Agent Center

Use the bundled Agent Center plugin as the single source of truth for team selection. Do not invent agents, sessions, provider health, skill IDs, or review evidence.

## Required workflow

1. Read the current project memory, worktree status, active plan, and owner constraints before selecting a team.
2. Call `agent_center_validate` with no packet or receipt first. Stop if the catalog is invalid.
3. Build a structured diagnosis containing `project_id`, `goal`, `phase`, `domains`, `risk_tags`, and `signals`.
4. Use only real, currently healthy provider sessions in the seat pool. A session ID or health state that was not observed must never be guessed.
5. Call `agent_center_route` with the diagnosis, seat pool, current provider ID, and current session ID.
6. If the result has `blocked: true`, stop team execution and report the missing evidence or seat in plain language.
7. Validate the returned Work Packet with `agent_center_validate` before execution. Validate the Work Receipt again before closeout.

## Available tools

- `agent_center_list_agents`
- `agent_center_get_agent`
- `agent_center_list_skills`
- `agent_center_route`
- `agent_center_prepare_training_candidate`
- `agent_center_validate`

## Owner and Relay rules

- AI Relay may be used only when the owner has approved it for the current task.
- If the owner cancels Relay, preserve any existing packet as evidence, continue only through the approved direct worktree, and never describe direct work as cross-provider review.
- Do not modify provider credentials, provider configuration, Hermes core, or production services from this skill.

## Training candidates

Prepare a candidate only through `agent_center_prepare_training_candidate`. The tool returns review-ready content but writes nothing.

Never write or promote a training candidate automatically. Present it for owner approval first; after approval, place it in the review queue defined by the project memory.

## Safety boundary

All catalog and routing actions are local, deterministic, and read-only. Network calls, persistent writes, and production actions require a separate approved workflow.
