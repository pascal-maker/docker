# Requirements: refactor-agent Migration Orchestrator

**Defined:** 2026-04-01
**Core Value:** The agent ships migrations as PRs — the PR description (component counts, tsc delta, strict flag status, files needing review) is the demo moment.

## v1 Requirements

### Component Classification

- [x] **CLASS-01**: System detects all React class components in a TypeScript workspace via AST analysis
- [ ] **CLASS-02**: Hard-block rules applied before AI classification: components using `getSnapshotBeforeUpdate`, `componentDidCatch`, or `forceUpdate` are routed to `manual` tier unconditionally
- [ ] **CLASS-03**: AI triage agent assigns each remaining component a complexity tier: `safe-auto`, `assisted`, or `manual`
- [ ] **CLASS-04**: Complexity tier criteria: `safe-auto` = no `componentDidUpdate`, no instance fields, no refs, no HOC wrapping; `assisted` = one or two of those present; `manual` = remainder
- [ ] **CLASS-05**: Classification result includes rationale per component for PR description and developer review

### Migration Transformation

- [ ] **MIGR-01**: `safe-auto` components transformed from class to function component with hooks using ts-morph
- [ ] **MIGR-02**: Supported lifecycle mappings: `componentDidMount` → `useEffect(fn, [])`, `componentWillUnmount` → cleanup in `useEffect`, `setState` → `useState`, `render()` unwrapped to function body
- [ ] **MIGR-03**: Transformations applied to a new git branch — never directly to main/default branch
- [ ] **MIGR-04**: Migration schedule respects component dependency order (parent migrated after children it renders)
- [ ] **MIGR-05**: Executor is transactional: if any transformation fails, git rollback to pre-migration state
- [ ] **MIGR-06**: Post-transform ESLint gate runs `rules-of-hooks` and `exhaustive-deps` before writing changes to disk; violations escalate component to `assisted` tier

### tsc Gate

- [ ] **TSC-01**: tsc diagnostics snapshot taken before any transformation (Error category only, `DiagnosticCategory.Error`)
- [ ] **TSC-02**: tsc diagnostics snapshot taken after all transformations complete
- [ ] **TSC-03**: Gate uses per-file `(file, line, code)` fingerprinting — not total error count — to detect new errors introduced by migration
- [ ] **TSC-04**: If new errors detected, PR is not opened; migration branch preserved with error report
- [ ] **TSC-05**: tsc gate uses the workspace's actual `tsconfig.json` — never hardcoded compiler defaults

### PR Integration

- [ ] **PR-01**: PR opened on new migration branch against default branch after tsc gate passes
- [ ] **PR-02**: PR title: `chore: migrate {N} React class components to hooks`
- [ ] **PR-03**: PR description is agent-generated and includes: component count by tier (auto/assisted/skipped), tsc error delta (before → after), list of files needing manual review with reason, which strict flags are now clean (if Layer 2 ran)
- [ ] **PR-04**: PR label applied: `safe-auto-migration` if all components were safe-auto; `needs-review` if any assisted or manual components present
- [ ] **PR-05**: PR description includes fallback guidance for escalated components (link to assisted mode)

### TypeScript Strict Mode Hardening (Layer 2)

- [ ] **STRICT-01**: Strict hardening layer runs after hooks migration completes on a workspace
- [ ] **STRICT-02**: Each tsc strict flag enabled incrementally (one flag per run): `noImplicitAny` → `strictNullChecks` → `strictFunctionTypes` → `strictBindCallApply` → `strictPropertyInitialization`
- [ ] **STRICT-03**: Flag ordering determined by ascending error count (fewest new errors first)
- [ ] **STRICT-04**: Each flag enablement produces its own PR with tsc error delta for that flag
- [ ] **STRICT-05**: Flags with zero new errors auto-applied; flags with errors documented in PR for manual fix

### MCP Surface

- [ ] **MCP-01**: `run_migration(workspace_path)` MCP tool exposed — triggers full migration pipeline and returns PR URL
- [ ] **MCP-02**: `get_migration_status(workspace_path)` MCP tool — returns component classification summary and migration state

### Infrastructure Prerequisites

- [x] **INFRA-01**: Bare exception handlers in engine subprocess path replaced with typed handlers and git rollback (unblocks transactional executor)
- [x] **INFRA-02**: Module-level global state in `a2a/executor.py` replaced with request-scoped context (unblocks concurrent migration jobs on A2A)

## v2 Requirements

### Assisted Mode

- **ASST-01**: File-by-file IDE review for `assisted` tier components — show before/after in VS Code before applying
- **ASST-02**: Developer can approve, skip, or escalate each assisted component individually

### Complex Lifecycle Migration

- **CMPLX-01**: `componentDidUpdate` → `useEffect` with inferred dependency arrays (`assisted` tier, not full auto)
- **CMPLX-02**: Instance field migration (class fields → `useRef` or `useState` based on mutability)
- **CMPLX-03**: Higher-order component unwrapping

### Advanced PR Features

- **PR-06**: Per-component before/after diff included in PR description (collapsible)
- **PR-07**: Re-run migration idempotently (skip already-migrated components)

## v3 Requirements

### Cross-Repo

- **REPO-01**: Run migration across multiple repos in dependency order
- **REPO-02**: Fan out migration schedule via A2A to parallel repo agents

## Out of Scope

| Feature | Reason |
|---------|--------|
| Error boundary migration (`componentDidCatch`) | No hooks equivalent — React docs state class-only permanently |
| `getSnapshotBeforeUpdate` migration | No hooks equivalent — React docs explicit |
| `forceUpdate()` migration | Breaks hooks state semantics — manual rewrite required |
| jscodeshift / Babel AST | Second TS engine violates PROJECT.md constraint; cannot resolve TS types |
| PyGithub / gh CLI for PR creation | Direct HTTP matches existing `github_api.ts` pattern; avoids new dep |
| Simultaneous strict flag enablement | Error noise is unmanageable; incremental per-flag is the correct UX |
| Non-React migrations (Django, Node upgrades) | Out of scope until React/TS proven; different AST domain |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLASS-01 | Phase 1 | Complete |
| CLASS-02 | Phase 2 | Pending |
| CLASS-03 | Phase 2 | Pending |
| CLASS-04 | Phase 2 | Pending |
| CLASS-05 | Phase 2 | Pending |
| MIGR-01 | Phase 3 | Pending |
| MIGR-02 | Phase 3 | Pending |
| MIGR-03 | Phase 3 | Pending |
| MIGR-04 | Phase 3 | Pending |
| MIGR-05 | Phase 3 | Pending |
| MIGR-06 | Phase 3 | Pending |
| TSC-01 | Phase 2 | Pending |
| TSC-02 | Phase 2 | Pending |
| TSC-03 | Phase 2 | Pending |
| TSC-04 | Phase 2 | Pending |
| TSC-05 | Phase 2 | Pending |
| PR-01 | Phase 4 | Pending |
| PR-02 | Phase 4 | Pending |
| PR-03 | Phase 4 | Pending |
| PR-04 | Phase 4 | Pending |
| PR-05 | Phase 4 | Pending |
| STRICT-01 | Phase 5 | Pending |
| STRICT-02 | Phase 5 | Pending |
| STRICT-03 | Phase 5 | Pending |
| STRICT-04 | Phase 5 | Pending |
| STRICT-05 | Phase 5 | Pending |
| MCP-01 | Phase 4 | Pending |
| MCP-02 | Phase 4 | Pending |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 after initial definition*
