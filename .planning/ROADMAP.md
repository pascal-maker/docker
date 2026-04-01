# Roadmap: refactor-agent Migration Orchestrator

## Overview

Five phases build the migration platform from its prerequisites to a complete two-layer migration product. Phase 1 fixes the infrastructure gaps that would corrupt any migration built on top. Phase 2 locks in the classifier and tsc gate — the safety foundation. Phase 3 builds the transactional executor that applies safe-auto transforms and produces a working migration branch. Phase 4 assembles the full end-to-end pipeline: PR creation, agent-generated description, and MCP surface. Phase 5 adds TypeScript strict mode hardening (Layer 2), which reuses the proven Layer 1 infrastructure to incrementally harden the workspace after hooks migration is complete.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Fix infrastructure prerequisites and add React class component detection bridge (completed 2026-04-01)
- [ ] **Phase 2: Classifier and tsc Gate** - Classify components by migration complexity and implement per-file tsc fingerprint gate
- [ ] **Phase 3: Migration Executor** - Apply safe-auto transforms on isolated branches with transactional rollback
- [ ] **Phase 4: PR Creation and Runner** - Assemble full pipeline, agent-generated PR description, and MCP tools
- [ ] **Phase 5: TypeScript Strict Hardening** - Incrementally enable strict flags with per-flag PRs (Layer 2)

## Phase Details

### Phase 1: Foundation
**Goal**: Infrastructure prerequisites are resolved and the system can detect and inventory React class components in a TypeScript workspace
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, CLASS-01
**Success Criteria** (what must be TRUE):
  1. Given any workspace path, the system returns a typed list of all React class components with their file locations and lifecycle method inventory
  2. Bare exception handlers in the engine subprocess path are replaced with typed handlers — a partial transform failure surfaces as an explicit typed error, not a swallowed exception
  3. The A2A executor no longer holds module-level global state; concurrent migration job requests do not share or corrupt each other's context
**Plans:** 2/2 plans complete

Plans:
- [x] 01-01-PLAN.md — Narrow bare exception handlers (INFRA-01) and eliminate shared state in A2A executor (INFRA-02)
- [x] 01-02-PLAN.md — Add React class component detection bridge handler, Python wrapper, and Pydantic models (CLASS-01)

### Phase 2: Classifier and tsc Gate
**Goal**: Every detected class component is assigned a complexity tier with rationale, and the tsc gate can reliably detect new type errors introduced by any transformation
**Depends on**: Phase 1
**Requirements**: CLASS-02, CLASS-03, CLASS-04, CLASS-05, TSC-01, TSC-02, TSC-03, TSC-04, TSC-05
**Success Criteria** (what must be TRUE):
  1. Components using `getSnapshotBeforeUpdate`, `componentDidCatch`, or `forceUpdate` are unconditionally routed to `manual` tier before any AI classification runs
  2. Each remaining component receives a tier assignment (`safe-auto`, `assisted`, or `manual`) with a per-component rationale string explaining the classification decision
  3. The tsc gate captures before-and-after per-file `(file, line, code)` fingerprints using the workspace's actual `tsconfig.json` — not hardcoded compiler defaults
  4. If any migrated file gains a new tsc error (by fingerprint comparison), the gate reports which file and error code introduced the regression
**Plans**: TBD

### Phase 3: Migration Executor
**Goal**: Safe-auto components are transformed from class to function components with hooks on a new isolated git branch, with the guarantee that any failure leaves the branch in the last clean committed state
**Depends on**: Phase 2
**Requirements**: MIGR-01, MIGR-02, MIGR-03, MIGR-04, MIGR-05, MIGR-06
**Success Criteria** (what must be TRUE):
  1. Running the executor against a workspace with safe-auto components produces a new git branch containing transformed function components — main/default branch is never modified
  2. Transformed components correctly map `componentDidMount` → `useEffect(fn, [])`, `componentWillUnmount` → `useEffect` cleanup return, `setState` → `useState`, and `render()` → function body
  3. If a transform fails mid-run, the branch is rolled back to the last successful committed state — no partial or corrupted files remain
  4. Components are transformed in dependency order: child components are migrated before the parent components that render them
  5. Components that fail the post-transform ESLint `rules-of-hooks` or `exhaustive-deps` gate are escalated to `assisted` tier, not written to disk
**Plans**: TBD
**UI hint**: no

### Phase 4: PR Creation and Runner
**Goal**: Running the migration pipeline end-to-end produces a GitHub PR with an agent-generated description that communicates migration scope, tsc delta, tier breakdown, and files needing manual review
**Depends on**: Phase 3
**Requirements**: PR-01, PR-02, PR-03, PR-04, PR-05, MCP-01, MCP-02
**Success Criteria** (what must be TRUE):
  1. After a successful migration run, a PR is opened against the default branch with title `chore: migrate {N} React class components to hooks` and a label of either `safe-auto-migration` or `needs-review` based on tier composition
  2. The PR description includes: component count by tier (auto/assisted/skipped), tsc error delta (before count → after count), list of files needing manual review with per-file reason, and guidance for escalated components
  3. If the tsc gate detects new errors, no PR is opened — the migration branch is preserved with an error report accessible to the developer
  4. A developer can trigger the full migration pipeline via the `run_migration(workspace_path)` MCP tool and receive back the PR URL
  5. A developer can query migration state at any time via the `get_migration_status(workspace_path)` MCP tool and receive a component classification summary
**Plans**: TBD
**UI hint**: no

### Phase 5: TypeScript Strict Hardening
**Goal**: After hooks migration, TypeScript strict flags are enabled one at a time — each producing its own PR — ordered by ascending error impact so safe flags ship immediately and risky flags are documented for manual review
**Depends on**: Phase 4
**Requirements**: STRICT-01, STRICT-02, STRICT-03, STRICT-04, STRICT-05
**Success Criteria** (what must be TRUE):
  1. The strict hardening layer runs after hooks migration completes on a workspace and produces at least one flag-enablement PR
  2. Each strict flag is enabled in its own separate PR — never multiple flags in one commit — with the tsc error delta for that specific flag in the PR body
  3. Flags are processed in ascending order of new error count (fewest errors first), so the easiest wins ship before the riskier flags are attempted
  4. Flags that introduce zero new errors are auto-applied and their PR opened automatically; flags with errors produce a PR documenting the errors for manual fix
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete   | 2026-04-01 |
| 2. Classifier and tsc Gate | 0/TBD | Not started | - |
| 3. Migration Executor | 0/TBD | Not started | - |
| 4. PR Creation and Runner | 0/TBD | Not started | - |
| 5. TypeScript Strict Hardening | 0/TBD | Not started | - |
