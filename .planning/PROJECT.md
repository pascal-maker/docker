# refactor-agent: Migration Orchestrator

## What This Is

An agentic migration platform that ships large-scale React and TypeScript migrations as reviewable PRs — not suggestions, not diffs to copy-paste, but actual branches with agent-generated PR descriptions. Built on top of the existing refactor-agent infrastructure (planner, executor, AST engines, MCP/A2A interfaces), this is the first capability that transforms the tool from a refactoring wrapper into a migration product.

## Core Value

The agent ships migrations as PRs. The PR description — component counts, tsc error delta, strict flag status, files needing manual review — is the demo moment. Not the code diff.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Triage agent classifies React class components by migration complexity (simple / medium / complex)
- [ ] Migration schedule built with dependency ordering across component graph
- [ ] tsc before-check run against workspace prior to any transformation
- [ ] Transformations applied on a new git branch (never directly to main)
- [ ] tsc after-check as pass/fail exit gate
- [ ] PR opened with agent-generated description (component counts, tsc delta, flags clean, files needing review)
- [ ] Three-tier routing: safe-auto (full auto) / assisted (file-by-file IDE review) / manual (excluded with explanation)
- [ ] PR labels applied: `safe-auto-migration` or `needs-review`
- [ ] TypeScript strict mode hardening layer (runs after hooks migration, incrementally enables flags)
- [ ] Fallback: schedule → approval → PR flow when user wants to review plan first
- [ ] Fallback: file-by-file IDE mode for assisted components

### Out of Scope (v1)

- Complex components (irregular lifecycle, refs, error boundaries, instance fields) — escalated to manual, not auto-migrated in v1
- Cross-repo migrations — v3
- Non-React migrations (Django, Node upgrades) — after React/TS is proven
- Real-time collaborative review — future

## Context

**Existing infrastructure (leverage fully):**
- `TsMorphProjectEngine` — TypeScript full-project transforms, the execution backbone
- `schedule/planner.py` + `schedule/executor.py` — planner/executor pipeline with toposort, reuse for migration schedule
- `agentic/triage.py` — existing complexity triage agent, extend for component classification
- `mcp/server.py` — MCP server for VS Code/Cursor integration
- `a2a/server.py` — A2A endpoint already deployed on Cloud Run
- `ci/runner.py` — CI preset runner, extend for migration presets

**Key gaps to fill:**
- No React AST analysis (class component detection, lifecycle mapping)
- No git branch management in executor
- No PR creation integration (GitHub API or `gh` CLI)
- tsc before/after integration not wired up
- MCP server only exposes `rename_symbol` — needs migration tools added

**Rollout framing:**
- v1: React hooks migration (AI-classified simple/medium, full auto → PR)
- v2: tsc strict mode hardening gate after migration
- v3: Complex component assisted mode + cross-repo support

## Constraints

- **Tech stack:** Must use existing TsMorphProjectEngine for TypeScript AST transforms — do not introduce a second TS engine
- **Branch safety:** Transformations NEVER applied to main/default branch — always a new migration branch
- **tsc gate:** tsc after-check is a hard exit gate — if tsc error count increases, PR is not opened without explicit override
- **Strict typing:** All new Python code follows CLAUDE.md rules (no `Any`, no `dict` in signatures, Pydantic models)
- **No LLM in tests:** PydanticAI `TestModel` for all agent tests

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PR-first as primary UX | The PR description is the demo moment — makes migration value immediately legible to the whole team | — Pending |
| AI-based complexity classification | Heuristic rules for "simple" are brittle; AST-based triage agent is more robust and aligns with existing architecture | — Pending |
| Layer 1 then Layer 2 sequencing | React hooks migration is the visible win; tsc hardening is the credibility layer that proves safety | — Pending |
| Extend existing triage agent | Avoid duplicating classification logic — extend `agentic/triage.py` with migration-specific complexity scoring | — Pending |
| TsMorphProjectEngine as backbone | Already handles full TS project transforms; React class→hooks is a superset of existing op types | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-01 after initialization*
