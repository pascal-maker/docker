# Feature Landscape

**Domain:** React class→hooks migration + TypeScript strict mode hardening platform
**Researched:** 2026-04-01
**Confidence note:** WebSearch unavailable. All findings from training data (cutoff August 2025)
plus direct codebase inspection. Confidence levels reflect this.

---

## React-Specific Features

### Table Stakes — React Migration

Features that any migration tool must have or it is not useful. Without these, engineers
will revert to jscodeshift scripts or manual work.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Class component detection | Entry point for everything else | Low | `getClasses()` in ts-morph already works; need React.Component/PureComponent filter |
| Lifecycle method inventory | Teams need to know what mappings exist before trusting the tool | Low-Med | `componentDidMount`, `componentDidUpdate`, `componentWillUnmount` → `useEffect`; `shouldComponentUpdate` → `React.memo`; constructor state → `useState` |
| `state` → `useState` conversion | The most common pattern; missing it means the tool is a non-starter | Med | Must handle `this.state.x` reads AND `this.setState({x: ...})` writes; partial setState merges are the trap |
| `this.props` → destructured props | Every class component has props access | Low-Med | Props typing must be preserved; FC generic signature `React.FC<Props>` or `(props: Props) =>` |
| `componentDidMount` → `useEffect` | ~90% of class components have this lifecycle | Med | Dependency array must be correct — empty `[]` for mount-only; must not introduce stale closure bugs |
| `componentWillUnmount` → cleanup fn in useEffect | Paired with mount; missing breaks subscriptions | Med | Returned cleanup function in the same `useEffect` block as mount logic |
| `componentDidUpdate` → useEffect with deps | Conditional update logic is common | High | Must detect which state/props the method reads to build dep array; incorrect deps are a runtime bug not a type error |
| Import rewrite | `import React, { Component }` → `import React` or named hook imports | Low | ts-morph `organize_imports` partially handles this; need hook imports added |
| tsc check before transformation | Non-negotiable safety gate | Low | Already have `get_diagnostics` in engine; need before-count capture |
| tsc check after transformation | Non-negotiable safety gate | Low | Same engine; need after-count comparison, fail if count increases |
| Branch isolation | Transformations must never land on main | Low | `agentic/git.py` already has `ensure_refactor_branch`; wire it up |
| Component count in output | Teams need to see scope before approving | Low | Count per tier (safe-auto / assisted / manual); include in PR description |

### Differentiators — React Migration

What makes this better than running a jscodeshift codemod script once.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI complexity classification (simple / medium / complex) | Heuristic codemod scripts fail on unusual patterns; AI classification with AST evidence is more robust and explains WHY a component is complex | Med | Extend existing `triage.py`; inputs: lifecycle count, `this.refs` usage, instance fields, error boundary, `getDerivedStateFromProps`. Confidence < threshold → escalate tier |
| Three-tier routing with explanations | "Component X is manual: uses `getSnapshotBeforeUpdate` + 3 instance fields" is actionable; a jscodeshift skip is not | Med | safe-auto: no lifecycle except simple mount/unmount + no refs + no instance fields. assisted: `componentDidUpdate` with complex deps OR one instance field. manual: error boundary, `getSnapshotBeforeUpdate`, `getDerivedStateFromProps`, `createRef`/`ref=` callback |
| Dependency graph ordering | Transform leaf components first; parent components last so props types are stable when parent is transformed | Med | Reuse `schedule/executor.py` toposort; add import-graph analysis to build the DAG |
| PR description with agent-generated analysis | "12 safe-auto, 3 assisted (listed below), 2 manual (error boundaries)" is the entire demo moment — it's legible to a tech lead in 30 seconds | High | This is the primary UX differentiator. Must include: component counts by tier, tsc error delta, list of assisted files with reason, list of manual files with reason, strict flags enabled/remaining |
| Fallback: schedule-approval flow | Teams with change-freeze policies need to review a plan before any file is touched | Low-Med | Expose schedule as a reviewable artifact (JSON or markdown table) before execution; approval triggers branch creation + execution |
| Idempotent re-runs | Running migration twice must not double-wrap hooks or corrupt imports | Med | Detect already-migrated components (is it already a function component?) and skip them |
| Per-file rollback on tsc regression | If a specific file causes new tsc errors, revert that file's changes and move it to manual tier | High | Requires per-file before/after diagnostic comparison; only viable because changes are committed per checkpoint in `agentic/git.py` |

### Anti-Features — React Migration (v1)

Things to deliberately NOT build. Building them in v1 creates unbounded scope with low return.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| `getSnapshotBeforeUpdate` auto-migration | Extremely rare; always requires bespoke logic; wrong migration breaks scroll/animation | Classify as manual with explanation |
| Error boundary auto-migration | `componentDidCatch` has no hooks equivalent; must remain a class component | Detect and mark manual; add comment explaining permanent class status |
| `getDerivedStateFromProps` auto-migration | Complex state derivation; error-prone with hooks; most codebases have < 3 instances | Classify as manual; suggest `useMemo` with a comment for engineer to validate |
| Automatic ref migration (callback refs, `createRef`) | `useRef` migration is syntactically simple but semantically subtle; requires human judgment on lifecycle timing | Move to assisted or manual tier based on usage pattern |
| Context API class→hook migration | `contextType` and `Context.Consumer` → `useContext` is a separate migration pass; mixing it into class→hooks migration increases blast radius | Defer; document as a subsequent milestone |
| Testing file migration (Enzyme → RTL) | Entirely separate domain; test migration breaks without component migration finishing first | Separate milestone |
| Automated PR merge | The tool creates and describes PRs; humans approve and merge | Never add auto-merge in v1; builds trust first |
| Cross-repo migrations | Needs separate infrastructure; too much ambient risk in v1 | v3 per PROJECT.md |

---

## TypeScript Strict Mode Features

### Table Stakes — TS Strict Hardening

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Current tsconfig audit | Before enabling anything, need a baseline of what flags exist and what's missing | Low | Parse `tsconfig.json`; compare against full `strict: true` flag set |
| Error count baseline per flag | Teams need to know "enabling `noImplicitAny` adds 47 errors" before agreeing to enable it | Med | For each candidate flag: enable in-memory in ts-morph project, count diagnostics with that flag enabled; do NOT write to disk yet |
| Flag enablement ordering (safe → unsafe) | Some flags are nearly free (e.g. `strictBindCallApply`); others are expensive (e.g. `noUncheckedIndexedAccess`). Order by error count ascending | Med | Recommended order: `strictNullChecks` → `noImplicitAny` → `strictFunctionTypes` → `strictPropertyInitialization` → `noImplicitReturns` → `strictBindCallApply` → `noUncheckedIndexedAccess`. Each flag is separate; never all at once |
| tsc gate: flag produces no new errors | The gate is the same as React migration: before and after error count must not increase | Low | Reuse same diagnostic comparison infrastructure |
| tsconfig.json rewrite | After validation, update `tsconfig.json` with newly enabled flags | Low | ts-morph or direct JSON parse; preserve comments with `json5`-aware parser if possible |
| PR per flag batch | Each PR should enable a small cohort of flags (those with 0 or near-0 new errors) | Med | Batching logic: group flags with 0 new errors together; flags with > 0 errors get individual PRs with error list |

### Differentiators — TS Strict Hardening

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-flag error impact report | "Enabling `noImplicitAny` will produce 47 errors in 12 files (listed below)" is actionable; a raw tsc run is not | Med | Build from diagnostic scan results; group by file; include error codes |
| Auto-fix safe violations | For flags like `strictNullChecks`, some violations are mechanical: add `!` assertion for cases where type narrowing already proves non-null, or add explicit ` | null` to type annotations. This is a known limited set | High | Confidence: LOW. Auto-fixing type errors requires care. In v1, report only. In v2, offer per-file fix suggestions for simple patterns |
| Flag dependency graph | `strictNullChecks` must come before `strictPropertyInitialization`; `noImplicitAny` is a prerequisite for many downstream improvements. Encode this as a DAG | Low-Med | Small static DAG; encode in code, not inferred dynamically |
| Incremental tsconfig strategy | Rather than a monolithic `"strict": true`, use individual flags so the git history is legible ("PR: enable strictNullChecks — 0 new errors") | Low | The PR description must explain why each flag is safe |
| Integration with React migration sequence | Strict hardening runs AFTER hooks migration. The React migration PR establishes a clean tsc baseline; strict hardening builds on that baseline | Low | Sequencing is a product decision, not a technical one; encode in documentation and PR description |

### Anti-Features — TS Strict Hardening (v1)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Auto-fixing `noImplicitAny` violations | Adding `: any` as a fix defeats the purpose; adding correct types requires understanding domain intent | Report violations with file/line; leave fixing to engineer |
| Enabling `noUncheckedIndexedAccess` automatically | This flag changes runtime semantics of array access; `arr[0]` becomes `T | undefined`. High false-positive rate in large codebases | Add to the end of the flag queue; require explicit human approval |
| `strict: true` in one shot | Binary: either breaks everything or does nothing. Opaque to reviewers | Incremental per-flag PRs only |
| Modifying `node_modules` type stubs | Out of scope; creates dependency on tool for type integrity | Recommend `@types/...` upgrades separately |
| Path mapping changes | `tsconfig` paths are a different class of problem; touching them breaks builds in unexpected ways | Never modify `paths` or `baseUrl` in v1 |

---

## Feature Dependencies

```
React class detection
    → complexity classification (simple / medium / complex)
        → three-tier routing
            → dependency graph ordering
                → safe-auto transformation execution
                    → tsc after-gate
                        → per-file rollback (if regression)
                            → commit checkpoint
                                → PR creation with agent description

tsc baseline capture (before)
    → flag impact scan (per-flag error count)
        → flag ordering (0-error flags first)
            → tsconfig update
                → tsc after-gate
                    → PR with flag enablement description

React migration PR (merged)
    → TS strict hardening layer (runs after hooks baseline is clean)
```

---

## MVP Recommendation

The PR description is the demo moment (per PROJECT.md). Prioritize the features that make
that description legible and trustworthy.

**Prioritize in this order:**

1. Class component detection + lifecycle inventory — no migration without this
2. Simple `state`/`props`/`componentDidMount`/`componentWillUnmount` transformation — the
   "safe-auto" tier; this is what ships as the first PR
3. AI complexity classification — drives the three-tier routing; without it, everything
   is manual
4. tsc before/after gate — the safety claim; without this the PR description cannot say
   "tsc clean"
5. PR creation with agent description — the demo moment; must include component counts,
   tsc delta, and tier breakdown
6. Branch isolation and git checkpoints — already partially implemented; wire up

**Defer to v2:**

- `componentDidUpdate` auto-migration — high complexity, high risk; makes the PR description
  harder to trust in v1
- TS strict flag hardening layer — per PROJECT.md v2 milestone
- Per-file rollback on tsc regression — desirable but adds significant complexity in v1
- Idempotent re-run detection — important for production use; can be added in v1.1

**Defer indefinitely (anti-features above):**

- Error boundary migration, `getSnapshotBeforeUpdate`, `getDerivedStateFromProps` auto-fix

---

## Complexity Classification Detail

This feature appears in both React migration (tier routing) and TS hardening (flag ordering).
It is the most important correctness-gating feature in the system. Here is the criteria
recommended for the React migration classifier specifically.

**Simple (safe-auto):**
- Extends `React.Component` or `React.PureComponent`
- No `this.refs` usage
- No instance fields (only `this.state` and `this.props`)
- Lifecycle methods limited to: `constructor`, `render`, `componentDidMount`,
  `componentWillUnmount`
- No `getDerivedStateFromProps`, `getSnapshotBeforeUpdate`, `componentDidCatch`
- Props type is explicit (interface or type alias exists)
- No HOC wrapping at class level (e.g. `export default connect(...)(MyComponent)`)

**Medium (assisted):**
- Has `componentDidUpdate` (dep array inference required)
- Has one instance field (not `state` or `props`)
- Has `shouldComponentUpdate` (can become `React.memo` but needs review)
- HOC wrapping present
- Props type is implicit (needs inference)

**Complex (manual):**
- Error boundary: `componentDidCatch` present
- `getSnapshotBeforeUpdate` present
- `getDerivedStateFromProps` present
- Two or more instance fields
- `createRef` or callback ref (`ref={node => ...}`) usage
- Extends a non-React base class (e.g. a custom `BaseComponent`)
- Component body > 300 lines (heuristic: likely has irregular patterns)

**Confidence:** MEDIUM — these criteria are derived from training data knowledge of
React migration patterns established circa 2019-2024 (React Hooks RFC, react-codemod
project, community migration guides). The actual thresholds (e.g. "300 lines") should
be validated against the target codebase in the first pilot.

---

## PR Description Quality Requirements

The PR description is the primary UX. It must answer the following questions for a tech
lead reading it in under 60 seconds:

1. How many components were migrated automatically? (count by tier)
2. Did tsc get better, worse, or stay the same? (error delta as +N/-N/0)
3. Which files need human review? (assisted list with reason)
4. Which files were excluded? (manual list with reason — one line per file)
5. Are there any strict flags that are now newly enabled?
6. What is the branch name and how do I test it?

**Anti-pattern:** A PR description that is a wall of file paths with no context.
**Anti-pattern:** A PR description that claims "all migrations successful" without tsc delta.
**Pattern:** Keep the description under ~40 lines. Use collapsible sections for long file lists.

---

## Sources

- Codebase inspection: `/apps/backend/src/refactor_agent/` (direct read, HIGH confidence)
- Codebase inspection: `/packages/ts-morph-bridge/src/` (direct read, HIGH confidence)
- `.planning/PROJECT.md` (direct read, HIGH confidence)
- `.planning/codebase/ARCHITECTURE.md` (direct read, HIGH confidence)
- React Hooks lifecycle mapping: training data from React RFC, react-codemod repo, and
  community migration guides (MEDIUM confidence — verify against React 18/19 docs when
  implementing)
- TypeScript strict flag semantics and ordering: training data from TypeScript handbook
  and community migration guides (MEDIUM confidence — verify against current TS docs)
- Complexity classification criteria: synthesized from training data on jscodeshift,
  react-codemod, and known failure modes in class→hooks migrations (MEDIUM confidence)
- WebSearch unavailable: no real-time verification performed; flag for validation before
  implementation
