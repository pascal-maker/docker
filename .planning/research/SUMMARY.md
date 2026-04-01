# Project Research Summary

**Project:** refactor-agent — Migration Orchestrator (React class→hooks + TypeScript strict mode)
**Domain:** Automated codebase migration — React lifecycle patterns + TypeScript strict hardening
**Researched:** 2026-04-01
**Confidence:** HIGH (architecture and stack grounded in direct codebase inspection; feature boundaries and heuristics MEDIUM)

## Executive Summary

This project adds a Migration Orchestrator capability to the existing refactor-agent platform. The core product is a two-layer automated migration system: Layer 1 converts React class components to function components with hooks; Layer 2 incrementally enables TypeScript strict mode flags. The existing codebase already provides almost everything needed — `TsMorphProjectEngine`, `schedule/executor.py`, `agentic/git.py`, PydanticAI agent framework, and structured logging. No new Python or npm packages are required. All new work is code additions within existing packages, specifically a new `migration/` Python package and new handlers in `packages/ts-morph-bridge/src/react.ts`.

The recommended approach is to build the React migration pipeline as a self-contained `migration/` package that wraps the existing infrastructure at well-defined integration points: the router dispatches a `react_migration` intent to a new `MigrationRunner`, which runs a classify → plan → tsc-gate → execute → PR pipeline. The ts-morph bridge handles all TypeScript AST transforms through new handlers (`apply_hooks_transform`, `list_react_class_components`, `get_component_lifecycle_map`). The central UX output is an agent-generated PR description that communicates migration scope, tsc error delta, and per-tier component breakdowns to a tech lead within 60 seconds.

The most serious risks concentrate in three areas: (1) false-positive "safe-auto" classification for components with unmigrateable patterns (error boundaries, `getSnapshotBeforeUpdate`, `forceUpdate`), which must be hard-blocked before the LLM classifier runs; (2) the tsc gate counting total errors rather than per-file, error-only fingerprints — a flaw that lets regressions hide behind unrelated changes; and (3) pre-existing bare exception handlers in the engine path that can swallow partial transform failures, leaving files in a corrupted state. All three must be addressed before the migration executor is built.

## Key Findings

### Recommended Stack

The migration capability requires zero new dependencies. ts-morph 25.0.1 (already locked in `pnpm-lock.yaml`) exposes all required class introspection APIs (`getClasses()`, `getMethods()`, `getProperties()`, `getBaseClass()`). `project.getPreEmitDiagnostics()` — already wired in the existing `handleGetDiagnostics` bridge handler — is the correct tsc gate mechanism, equivalent to `tsc --noEmit`. GitHub PR creation uses direct HTTP to `api.github.com`, matching the repo's established pattern in `github_api.ts` and `github_auth.py`. The `gh` CLI must not be used for PR creation because it is not guaranteed in Cloud Run containers.

The one stack decision with lingering risk is the GitHub OAuth token scope: the existing OAuth app may not include the `repo` scope needed for branch push. This must be confirmed against the OAuth app configuration before shipping PR creation. The triage complexity heuristics (simple/medium/complex tier boundaries) are derived from community migration practice and should be validated against a real codebase sample before the classifier is considered reliable.

**Core technologies:**
- ts-morph 25.0.1: TypeScript AST read/write for all React transform operations — already the sole engine; extend only, never add Babel or jscodeshift
- pydantic-ai 1.59.0+: PydanticAI agent framework for `ReactClassifier` and `PRDescriptionAgent` — already in use; add new factory functions
- `project.getPreEmitDiagnostics()` via existing bridge: tsc gate (before/after error fingerprinting) — already implemented; extend to per-file scope
- `agentic/git.py` + subprocess git: branch creation, per-component commits, rollback — extend with `push_branch` and optional `branch_prefix` param
- Direct HTTP to `api.github.com`: PR creation in new `agentic/github_pr.py` — matches existing codebase pattern

### Expected Features

**Must have (table stakes):**
- React class component detection and lifecycle inventory — entry point; without this nothing else runs
- `state`/`props`/`componentDidMount`/`componentWillUnmount` transformation — the "safe-auto" tier that produces the first PR
- AI complexity classification (simple / medium / complex / manual) — drives three-tier routing; failure here causes silent runtime bugs
- tsc before/after gate using per-file, error-only fingerprints — safety claim; must use `(file, line, code)` tuples not aggregate counts
- Branch isolation and per-component git checkpoints — already partially implemented in `agentic/git.py`
- PR creation with agent-generated description — the demo moment; must include component counts, tsc delta, tier breakdown
- Hard-coded blocklist check for unmigrateable patterns (`getSnapshotBeforeUpdate`, `componentDidCatch`, `forceUpdate`, `getDerivedStateFromProps`) before any classification runs

**Should have (competitive differentiators):**
- Three-tier routing with per-component explanations in PR description ("Component X is manual: uses `getSnapshotBeforeUpdate`")
- Dependency graph ordering — transform leaf components before parents so parent props types are stable
- Post-transform ESLint gate (`react-hooks/exhaustive-deps`) — catches hook ordering violations that tsc cannot
- Idempotent re-runs — skip already-migrated function components
- Fallback schedule-approval flow — reviewable plan artifact before execution

**Defer to v2+:**
- `componentDidUpdate` auto-migration — high risk, incorrect dep arrays do not surface via tsc
- TypeScript strict mode hardening layer (Layer 2) — per PROJECT.md milestone sequencing
- Per-file rollback on tsc regression — desirable but adds significant v1 complexity
- Context API class→hook migration — separate migration pass, different blast radius
- Testing file migration (Enzyme → RTL) — separate domain

**Defer indefinitely (anti-features):**
- Error boundary auto-migration, `getSnapshotBeforeUpdate` transform, `getDerivedStateFromProps` auto-fix, `noUncheckedIndexedAccess` automatic enablement, auto-merge

### Architecture Approach

The migration capability is a new `migration/` package inside `apps/backend/src/refactor_agent/`, parallel to the existing `agentic/` and `schedule/` packages. It does not modify `execute_schedule()` or `ScopeSpec` — instead it introduces parallel types (`MigrationScope`, `MigrationSchedule`, `MigrateComponentOp`) and a dedicated execution loop (`MigrationExecutor`) that calls `TsMorphProjectEngine` and `agentic/git.py` directly. The router adds a `react_migration` intent that dispatches to a new `MigrationRunner`. New ts-morph handlers (`apply_hooks_transform`, `list_react_class_components`, etc.) are added to `packages/ts-morph-bridge/src/react.ts` and registered in the existing dispatch table.

**Major components:**
1. `migration/classifier.py` (`ReactClassifier`) — scans workspace, runs hard-blocklist check, classifies components into safe_auto / assisted / manual tiers using heuristics plus LLM fallback
2. `migration/tsc_gate.py` (`TscGate`) — snapshots per-file, error-only diagnostic fingerprints before and after transform; fails if any migrated file gains new errors
3. `migration/executor.py` (`MigrationExecutor`) — per-component transform loop calling ts-morph bridge, with git commit on success and `reset_to_last_commit` on failure; fully transactional
4. `migration/pr.py` + `PRDescriptionAgent` — creates GitHub PR via direct HTTP; PR body generated by a minimal PydanticAI agent from `MigrationResult`
5. `migration/runner.py` (`MigrationRunner`) — top-level orchestrator: classifier → planner → tsc-gate → executor → PR
6. `packages/ts-morph-bridge/src/react.ts` — new TypeScript handlers for `apply_hooks_transform`, `list_react_class_components`, `get_component_lifecycle_map`, `get_component_state_shape`, `classify_react_component`

### Critical Pitfalls

1. **False-positive "safe-auto" for unmigrateable components** — Hard-code a blocklist check (AST scan for `getSnapshotBeforeUpdate`, `componentDidCatch`, `getDerivedStateFromError`, `forceUpdate`) before the LLM classifier runs. These are unconditional `manual` escalations, not confidence-score decisions.

2. **tsc gate gaming via aggregate error counts** — Implement the gate as per-file `frozenset[tuple[file, line, code]]` fingerprints, not total count comparison. Scope to migrated files only; filter to `DiagnosticCategory.Error` (category 1) exclusively.

3. **Hook ordering violations not caught by tsc** — Wire `eslint-plugin-react-hooks` (`exhaustive-deps` + `rules-of-hooks`) as a post-transform gate before `apply_changes()` writes to disk, not as a development-only tool.

4. **tsc gate scope mismatch due to missing tsconfig** — The migration runner must always auto-discover and pass `workspace/tsconfig.json` to `TsMorphProjectEngine`. Never allow the fallback default compiler options (`strict: true`, `ES2022`) for migration work.

5. **Bare exception handlers swallow partial transforms** — Audit and address the 20+ bare `except` clauses in the engine path before building the migration executor on top. `MigrationExecutor` must implement transactional apply: git rollback on any unhandled exception.

## Implications for Roadmap

Based on combined research, the build order is tightly constrained by dependencies. The architecture research provides a 13-step build graph. The pitfalls research identifies three prerequisites that must be addressed before the main pipeline is built. The recommended phase structure follows the natural dependency graph.

### Phase 1: Foundation — Models, Bridge Handlers, Engine Extensions

**Rationale:** Everything else depends on the Pydantic models and ts-morph bridge handlers. These are pure additions with no risk of breaking existing functionality. The tsconfig auto-discovery fix (Pitfall 10) and bare exception handler audit (Pitfall 11) belong here as prerequisites that make later phases safe to build on.
**Delivers:** `migration/models.py` (all Pydantic models), new ts-morph `react.ts` handlers registered in bridge, `TsMorphProjectEngine` wrapper methods for new commands, tsconfig auto-discovery assertion in engine initialization, exception handler audit in engine subprocess path.
**Addresses:** Table stakes — class component detection and lifecycle inventory; tsc gate infrastructure
**Avoids:** Pitfall 10 (tsconfig scope mismatch), Pitfall 11 (bare exception swallowing)

### Phase 2: Classifier and Tsc Gate

**Rationale:** Classification must precede scheduling. The tsc gate implementation (per-file fingerprints) must be locked in before the executor is built, because retrofitting it later would require redesigning the executor's rollback logic.
**Delivers:** `migration/classifier.py` with hard blocklist check, `migration/tsc_gate.py` with per-file error-only fingerprint comparison, `agentic/triage.py` extension with `MigrationTriageResult` and `ComponentComplexity`
**Addresses:** AI complexity classification (simple/medium/complex), tsc before/after gate
**Avoids:** Pitfall 1 (false-positive safe-auto), Pitfall 3 (error count gaming), Pitfall 5 (`getDerivedStateFromProps`), Pitfall 6 (ref-contract components)

### Phase 3: Migration Planner and Executor (Safe-Auto Tier)

**Rationale:** With models, bridge handlers, classifier, and tsc gate in place, the executor can be built with a transactional contract from the start. Scope to safe-auto components only to constrain the blast radius of the first real end-to-end run.
**Delivers:** `migration/planner.py` (toposort-based schedule builder), `migration/executor.py` (transactional per-component loop, git checkpoint + rollback), `agentic/git.py` extension (`push_branch`, optional `branch_prefix` param), `schedule/models.py` extension (`MigrateClassToHooksOp`, `EnableStrictFlagOp`)
**Addresses:** Branch isolation, per-component git checkpoints, `state`/`props`/`componentDidMount`/`componentWillUnmount` transformation, dependency graph ordering
**Avoids:** Pitfall 2 (hook ordering — ESLint gate wired here), Pitfall 4 (state batching — updater function detection), Pitfall 11 (transactional apply)

### Phase 4: PR Creation and Runner Integration

**Rationale:** Once the executor produces a working branch, the PR creation and top-level runner can be assembled. The `PRDescriptionAgent` is a thin agent that takes `MigrationResult` and returns markdown — low risk but high UX value.
**Delivers:** `agentic/github_pr.py` (`PrRequest`, `PrResult`, `create_pull_request`, `add_labels`), `migration/pr.py` (`PRDescriptionAgent`, tiered PR description format with collapsed sections), `migration/runner.py` (full orchestration loop), `agentic/router.py` extension (`react_migration` intent), `mcp/server.py` extension (`run_react_migration`, `get_migration_plan` tools)
**Addresses:** PR creation with agent-generated description, component count output, tier breakdown, tsc delta in PR body, MCP surface area
**Avoids:** Pitfall 9 (PR noise — tiered format, per-PR component ceiling enforced in planner)

### Phase 5: TypeScript Strict Mode Hardening (Layer 2)

**Rationale:** Layer 2 is explicitly a v2 milestone per PROJECT.md. It reuses the `TscGate`, `execute_schedule()`, and git infrastructure already proven in Layer 1. It does not need a new pipeline — it adds a `strict_mode_hardening` CI preset type and `EnableStrictFlagOp` execution.
**Delivers:** Incremental strict flag enablement (one flag per PR), per-flag error impact reports, flag dependency DAG, tsconfig.json rewrite, CI preset for strict hardening
**Addresses:** Current tsconfig audit, error count baseline per flag, flag ordering (safe-to-unsafe), PR per flag batch
**Avoids:** Pitfall — enabling `strict: true` in one shot; `noUncheckedIndexedAccess` requires explicit human approval

### Phase Ordering Rationale

- Phase 1 must come first because all other phases depend on the Pydantic models and bridge handlers. Fixing the bare exception handlers and tsconfig scope issue here prevents building on a flawed foundation.
- Phase 2 (classifier + tsc gate) must precede the executor because the gate's per-file fingerprint design determines the executor's rollback contract. Reversing this order would require a rewrite.
- Phase 3 (executor, safe-auto only) deliberately excludes `componentDidUpdate` migration. This is the single highest-risk transform (incorrect dep arrays do not surface via tsc) and belongs in a separate phase or v2 once the safe-auto pipeline has been proven against real codebases.
- Phase 4 completes the MVP user-facing flow. The PR description is explicitly identified as "the demo moment" in PROJECT.md — it is the validation artifact that drives adoption.
- Phase 5 is sequenced after Layer 1 is proven because strict hardening is meaningless if the hooks migration introduced new type noise. The Layer 1 PR establishes the clean tsc baseline that Layer 2 builds on.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (executor — safe-auto transform):** The `apply_hooks_transform` handler for `componentDidUpdate` is excluded from v1 but the `componentDidMount`/`componentWillUnmount` transform still has non-trivial edge cases (e.g. multiple `setState` in mount, cleanup return placement). Consider a spike against 5-10 real components before committing to the transform implementation.
- **Phase 3 (state batching):** The updater-function detection logic (multiple `setState` calls on same key in same handler) requires a non-trivial AST walk. Research how ts-morph `CallExpression` traversal handles nested call sites before scoping the implementation.
- **Phase 4 (GitHub OAuth scope):** Confirm whether the existing OAuth app includes the `repo` scope before implementing `push_branch` + `create_pull_request`. If scope expansion is required, this has a deployment dependency outside the code change.
- **Phase 5 (flag ordering DAG):** The strict flag dependency ordering is MEDIUM confidence (training data only). Verify against current TypeScript 5.x docs before encoding the static DAG.

Phases with well-documented patterns (skip or minimal research):
- **Phase 1 (models + bridge):** Pure code additions following established patterns. ts-morph class introspection APIs confirmed in existing `ast.ts`. Extension pattern confirmed in `handlers.ts` + `index.ts`.
- **Phase 2 (tsc gate):** `get_diagnostics` is fully implemented end-to-end; the per-file fingerprint design is a well-understood pattern. No research needed.
- **Phase 4 (PR creation via HTTP):** Direct GitHub REST API pattern confirmed in `github_api.ts` and `github_auth.py`. Endpoint stable since 2020.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technology decisions grounded in direct codebase inspection. ts-morph 25.0.1 confirmed in lockfile. No new dependencies required. Only gap: OAuth `repo` scope unconfirmed. |
| Features | MEDIUM | Table stakes and anti-features are HIGH confidence (React docs, codebase inspection). Complexity tier heuristics and `componentDidUpdate` dep array inference are MEDIUM — derived from community migration practice, not verified against this specific codebase. |
| Architecture | HIGH | All component boundaries and integration points derived from direct inspection of `agentic/runner.py`, `schedule/executor.py`, `engine/typescript/ts_morph_engine.py`, and `handlers.ts`. Build order is a deterministic dependency graph, not inference. |
| Pitfalls | HIGH | All critical pitfalls sourced from either react.dev (authoritative) or direct codebase inspection (bare exception handlers, tsconfig fallback, module-level global state in A2A executor). No pitfall is training-data-only speculation. |

**Overall confidence:** HIGH

### Gaps to Address

- **OAuth `repo` scope:** Confirm whether the GitHub OAuth app registered for this project includes the `repo` scope. If not, scope expansion must be coordinated with a deployment change before Phase 4 ships.
- **Complexity tier boundary tuning:** The `simple` / `medium` / `complex` thresholds (e.g. "300 lines = complex", "one instance field = assisted") should be validated against a sample of 10-20 real components from a target codebase before the classifier is used in production.
- **`componentDidUpdate` dep array inference:** This is the highest-complexity transform in the system. It is deferred to v2 in the feature plan, but the classification heuristic (detecting components with `componentDidUpdate`) must be correct in v1 since it drives routing to `assisted`. Validate the AST detection logic against real-world usage patterns.
- **A2A module-level global state:** `a2a/executor.py` has request-scoped state issues documented in `CONCERNS.md`. If migration jobs are exposed via A2A before this is fixed, concurrent jobs will produce corrupt results. This is a prerequisite for A2A-triggered migrations, not for MCP-triggered ones.
- **ESLint gate integration:** The post-transform ESLint gate (`react-hooks/exhaustive-deps`) must run in the migration pipeline, not just as a dev tool. The integration path (subprocess call to `eslint`, parsing output into `DiagnosticEntry` equivalents) should be scoped in Phase 3 planning.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `packages/ts-morph-bridge/src/ast.ts`, `handlers.ts`, `state.ts`, `index.ts` — confirmed ts-morph 25.0.1 API usage and extension pattern
- Direct codebase inspection: `apps/backend/src/refactor_agent/engine/typescript/ts_morph_engine.py` — confirmed `get_diagnostics` implementation and bridge command pattern
- Direct codebase inspection: `apps/backend/src/refactor_agent/agentic/git.py`, `runner.py`, `triage.py` — confirmed subprocess git pattern and agent factory pattern
- Direct codebase inspection: `functions/shared/src/github_api.ts`, `auth/github_auth.py` — confirmed direct-HTTP GitHub API pattern
- Direct codebase inspection: `apps/backend/src/refactor_agent/schedule/models.py`, `executor.py` — confirmed op type extension pattern and toposort infrastructure
- Direct codebase inspection: `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONCERNS.md` — confirmed project constraints, deployment target (Cloud Run), existing technical debt
- react.dev: `Component` reference, `getSnapshotBeforeUpdate`, `componentDidCatch`, `useState`, `useEffect`, `useContext`, `forwardRef` — confirmed no-hook-equivalent patterns and stale closure semantics

### Secondary (MEDIUM confidence)
- Training knowledge: ts-morph class declaration API (`getClasses()`, `getMethods()`, `getProperties()`, `getBaseClass()`, `getImplements()`) — stable since ts-morph v10, not verified against v25 docs
- Training knowledge: React lifecycle → hooks mapping (react-codemod project, React Hooks RFC, community migration guides) — React 18/19 stable; hooks API not changing
- Training knowledge: TypeScript strict flag semantics and safe ordering — TypeScript handbook and community migration guides; verify against TS 5.x docs before Phase 5

### Tertiary (LOW confidence)
- GitHub REST API `POST /repos/{owner}/{repo}/pulls` — API stable since 2020, version header `2022-11-28` matches existing code; not live-verified
- Complexity tier boundary thresholds ("300 lines = complex") — synthesized from community migration guides; needs validation against target codebase

---
*Research completed: 2026-04-01*
*Ready for roadmap: yes*
