# Technology Stack

**Project:** refactor-agent — Migration Orchestrator (React class→hooks + TypeScript strict mode)
**Researched:** 2026-04-01
**Scope:** Stack dimension only — what libraries, AST APIs, and tooling to use for the new migration capability, mapped against the existing infrastructure.

---

## Constraint Recap (from PROJECT.md)

The project mandate imposes two hard constraints that govern every decision below:

1. **Must use existing TsMorphProjectEngine** — do not introduce a second TypeScript AST engine.
2. **Must follow CLAUDE.md typing rules** — all new Python code: no `Any`, no `dict` in signatures, Pydantic models, Python 3.12 syntax.

---

## What the Existing Infrastructure Already Covers

Understanding what already exists prevents duplicate work and forces the right decision on what actually needs to be added.

### Already provided — do NOT re-implement

| Capability | Existing component | Notes |
|---|---|---|
| TypeScript AST read/write | `TsMorphProjectEngine` (Python) + `ts-morph-bridge` (TS) | Full project mode, `init_project`, `get_diagnostics`, `rename_symbol`, `remove_node`, `move_symbol`, `apply_changes` |
| TypeScript diagnostics (pre-emit) | `TsMorphProjectEngine.get_diagnostics()` | Returns `list[DiagnosticInfo]` via existing bridge handler `handleGetDiagnostics` — wraps `project.getPreEmitDiagnostics()` |
| Class/function/interface AST queries | `ts-morph-bridge/src/ast.ts` | `sf.getClasses()`, `sf.getFunctions()`, `sf.getInterfaces()`, full declaration walk |
| Toposort + operation scheduling | `schedule/executor.py` + `schedule/models.py` | `RefactorSchedule` with `depends_on`, Kahn's algorithm already implemented |
| Complexity triage agent | `agentic/triage.py` | PydanticAI agent returning `TriageResult(category, confidence, scope_spec)` |
| Git branch creation and commits | `agentic/git.py` | `ensure_refactor_branch`, `commit_checkpoint`, `reset_to_last_commit` — all via subprocess `git` |
| GitHub OAuth user auth | `auth/github_auth.py`, `auth/oauth.py`, `functions/shared/src/github_api.ts` | Direct HTTP to `api.github.com`, no SDK, bearer token model |
| MCP server | `mcp/server.py` via `fastmcp>=2.14.0` | Currently exposes only `rename_symbol` for Python; needs migration tools added |
| A2A endpoint | `a2a/server.py` | CloudEvents over WebSocket/HTTP, already deployed |
| Structured logging | `structlog` + per-package `logger.py` pattern | JSON to stderr, Sentry integration |
| Agent framework | `pydantic-ai>=1.59.0` with `anthropic>=0.78.0` | `Agent[Deps, OutputType]`, `TestModel` for tests |

---

## New Stack Additions Required

These are the genuine gaps — infrastructure that must be added to support the migration capability.

### 1. React Class Component AST Analysis

**What is needed:** Detection of React class components (extends `React.Component` / `Component`), lifecycle method enumeration (`componentDidMount`, `componentDidUpdate`, `componentWillUnmount`, `shouldComponentUpdate`, `getSnapshotBeforeUpdate`), state shape extraction (`this.state`, `this.setState`), `props` type extraction, instance field detection, ref detection (`createRef`, callback refs), and complexity scoring.

**Decision: Extend the ts-morph bridge in TypeScript — do NOT add Babel, jscodeshift, or a second AST engine.**

Rationale:
- `TsMorphProjectEngine` is already the execution backbone for all TypeScript transforms. Introducing Babel or jscodeshift alongside it creates two separate AST representations that can disagree on type information, import resolution, and source positions.
- ts-morph wraps the TypeScript compiler's own AST (`ts.Node`) via `ClassDeclaration`, `MethodDeclaration`, `PropertyDeclaration`, and `HeritageClause` — precisely what is needed for class component analysis.
- The existing bridge already calls `sf.getClasses()` (visible in `ast.ts:buildSkeletonForFile`) and returns class metadata. React-specific detection is an incremental extension of this pattern, not a new system.
- ts-morph version 25.0.1 (confirmed in `pnpm-lock.yaml`) has full support for all required node types.

**What to add to `ts-morph-bridge/src`:**

New handler file `react.ts` (or additions to `handlers.ts`) exposing JSON-RPC commands:

| New bridge command | Purpose | ts-morph API used |
|---|---|---|
| `classify_react_component` | Returns complexity tier for one class component file | `sf.getClasses()`, `cls.getBaseClass()`, `cls.getMethods()`, `cls.getProperties()` |
| `list_react_class_components` | Scans project, returns all class component paths with names | Project-wide `getClasses()` walk |
| `get_component_lifecycle_map` | Returns which lifecycle methods are present | `cls.getMethod(name)` for each known lifecycle name |
| `get_component_state_shape` | Returns state initializer text + `setState` call sites | Property declaration for `state`, descendant call expression walk |
| `apply_hooks_transform` | Applies the class→function transform for a single component | Full rewrite: remove class, add function component, hoist state to `useState`, map lifecycles to `useEffect` |

**Confidence:** HIGH — ts-morph's class introspection APIs have been stable since v10; current version 25.0.1 supports all required node types. The extension pattern (add handler → expose via bridge JSON-RPC → call from Python) is already established by all existing handlers.

**Why not jscodeshift:** jscodeshift operates on Recast's AST (Babel parser by default), which is untyped. It cannot resolve TypeScript types, generics, or cross-file references. The react-codemod repo (the most widely cited class→hooks codemod) is built on jscodeshift and is documented as handling only simple cases; it does not handle TypeScript generics in state/props types, which are common in production codebases. It would require a second process and second AST model alongside ts-morph.

**Why not Babel:** Same fundamental problem — a second AST layer, no TypeScript type awareness.

### 2. TypeScript Strict Mode Diagnostics (Before/After Gate)

**What is needed:** A before-check (snapshot of tsc error count before any transformation) and an after-check (post-transform tsc error count), with hard exit if error count increases. Also needed: incremental strict flag enumeration for the hardening layer (adding `noImplicitAny`, `strictNullChecks`, etc. one flag at a time and measuring impact).

**Decision: Use `TsMorphProjectEngine.get_diagnostics()` for the before/after gate — do NOT shell out to `tsc` CLI separately.**

Rationale:
- `get_diagnostics()` already wraps `project.getPreEmitDiagnostics()`, which is the same diagnostic set that `tsc --noEmit` produces. The bridge is already running with the project's tsconfig, so compiler options (including strict flags) are respected.
- Adding a separate `tsc` CLI subprocess would create two separate TypeScript compiler instances that can disagree on configuration resolution, especially with path aliases and project references. Keeping a single `TsMorphProjectEngine` instance across the before/after snapshot is architecturally cleaner.
- Incremental strict flag testing: pass modified `compilerOptions` to `new Project({ compilerOptions: { ...base, noImplicitAny: true } })` inside the bridge. This is an extension to `handleInitProject` — add a `compiler_options_override` param.

**What to add to bridge:**

| New bridge param/command | Purpose |
|---|---|
| `compiler_options_override` on `init_project` | Accepts partial `CompilerOptions` JSON to layer strict flags for the hardening layer |
| `get_diagnostic_summary` (new) | Returns `{ error_count, warning_count, by_code: {...} }` Pydantic model — avoids shipping full diagnostics list across the bridge for the gate check |

**Python side:** New Pydantic model `DiagnosticSummary(error_count: int, warning_count: int, by_code: dict[int, int])` in `engine/base.py` (or a new `engine/typescript/models.py`). Note: `dict[int, int]` is acceptable as a Pydantic field type — the prohibition is on `dict` in *function signatures*, not in model fields.

**Confidence:** HIGH — `project.getPreEmitDiagnostics()` is the canonical programmatic equivalent of `tsc --noEmit`. This is a well-documented ts-morph capability already used in the existing bridge.

**tsc CLI — when to use it:** Use `tsc --noEmit --pretty false` via subprocess only as a fallback verification when the user explicitly requests a "clean tsc output" string for the PR description. Use Python `subprocess.run(["tsc", "--noEmit", "--pretty", "false"], cwd=workspace, capture_output=True)` wrapped in a new `run_tsc_check(workspace: Path) -> TscCheckResult` function in `engine/typescript/`. The `TscCheckResult` Pydantic model holds `returncode: int`, `stdout: str`, `stderr: str`, `error_count: int` (parsed from stdout). This is used only for the PR description generation, not as the gate.

### 3. PR Creation — GitHub REST API (Python)

**What is needed:** Push the migration branch to remote, open a PR via GitHub API, apply labels.

**Decision: Use direct HTTP calls to GitHub REST API from Python — match the existing pattern in `auth/github_auth.py` and `functions/shared/src/github_api.ts`.**

The repo already makes direct GitHub API calls without any SDK (`github_api.ts` uses `fetch` directly; `github_auth.py` uses `urllib`). Consistency with this pattern is important — introducing `PyGithub`, `ghapi`, or `pygithub` would add a dependency for a narrow use case.

**Decision: Do NOT use `gh` CLI via subprocess.**

Rationale: `gh` CLI availability cannot be guaranteed in Cloud Run containers, which is the production deployment target (Cloud Run, per `INTEGRATIONS.md`). The A2A server runs on Cloud Run. Python HTTP is portable.

**New Python module:** `agentic/github_pr.py`

| Function | Signature | Purpose |
|---|---|---|
| `push_branch` | `(workspace: Path, branch: str, remote: str = "origin") -> PushResult` | `git push origin <branch>` subprocess call |
| `create_pull_request` | `(token: str, owner: str, repo: str, request: PrRequest) -> PrResult` | POST `https://api.github.com/repos/{owner}/{repo}/pulls` |
| `add_labels` | `(token: str, owner: str, repo: str, pr_number: int, labels: list[str]) -> None` | POST `https://api.github.com/repos/{owner}/{repo}/issues/{number}/labels` |

Pydantic models:
```
class PrRequest(BaseModel):
    title: str
    body: str
    head: str       # branch name
    base: str       # target branch (main/master)
    draft: bool = False

class PrResult(BaseModel):
    number: int
    url: str
    html_url: str

class PushResult(BaseModel):
    success: bool
    error: str | None = None
```

**GitHub token:** The user's GitHub OAuth token (already in the auth flow as `UserRecord`) scopes must include `repo` for push access. This needs documentation in the PR creation flow — the existing OAuth app may need scope expansion. Note this as a deployment consideration, not a code change.

**Confidence:** HIGH for HTTP pattern (matches existing code). MEDIUM for token scope — the existing OAuth scope is not explicitly listed in the inspected code; verify `GITHUB_OAUTH_CLIENT_ID` app configuration includes `repo` scope before shipping.

### 4. Migration Operation Types (New Schedule Models)

**What is needed:** The existing `RefactorSchedule` operations (`RenameOp`, `MoveSymbolOp`, etc.) do not cover "convert class component to function component." The migration orchestrator needs new operation types.

**Decision: Add new Pydantic `_BaseOp` subclasses to `schedule/models.py`.**

New ops:

```python
class MigrateClassToHooksOp(_BaseOp):
    op: Literal["migrate_class_to_hooks"] = "migrate_class_to_hooks"
    file_path: str
    component_name: str
    complexity: Literal["simple", "medium"]

class EnableStrictFlagOp(_BaseOp):
    op: Literal["enable_strict_flag"] = "enable_strict_flag"
    flag: str   # e.g. "noImplicitAny", "strictNullChecks"
    files_affected: list[str] = Field(default_factory=list)
```

The `RefactorOperation` union and `execute_schedule` dispatch in `executor.py` must be extended to handle these. The executor calls the new bridge command `apply_hooks_transform` for `MigrateClassToHooksOp`.

**Confidence:** HIGH — this is a straightforward extension of an established pattern in the codebase.

### 5. Component Complexity Classification (Triage Extension)

**What is needed:** The existing triage agent classifies refactors as `trivial/structural/paradigm_shift/ambiguous`. The migration orchestrator needs React-specific classification: `simple/medium/complex` per component.

**Decision: Extend `agentic/triage.py` — add a `create_migration_triage_agent` factory function alongside the existing `create_triage_agent`.**

A new `MigrationTriageResult(BaseModel)` with:
```python
class ComponentComplexity(BaseModel):
    file_path: str
    component_name: str
    tier: Literal["simple", "medium", "complex", "manual"]
    rationale: str
    lifecycle_methods: list[str]
    has_refs: bool
    has_context: bool

class MigrationTriageResult(BaseModel):
    components: list[ComponentComplexity]
    summary: str
```

The agent's tools call `list_react_class_components` and `get_component_lifecycle_map` from the new bridge commands. The AI model (Claude) makes the judgment call for edge cases. Heuristic pre-classification in the bridge (returnable as metadata) provides grounding.

**Complexity tiers (to be encoded as bridge heuristics, not AI-only):**

| Tier | Heuristics |
|---|---|
| `simple` | Only `componentDidMount` (no cleanup), no `componentDidUpdate`, no `shouldComponentUpdate`, no instance fields beyond `state`, no `createRef`, no context, no error boundary methods |
| `medium` | `componentDidUpdate` present, or `componentWillUnmount`, or context consumer, but no instance fields, no `getSnapshotBeforeUpdate`, no error boundary |
| `complex` → `manual` | `getSnapshotBeforeUpdate`, `getDerivedStateFromProps`, error boundary methods, irregular lifecycle (both `componentDidMount` + complex `componentDidUpdate`), instance fields beyond state, `createRef` assigned to `this` |

**Confidence:** MEDIUM — the tier boundary heuristics are based on established React migration practice. Exact boundary cases (e.g. `getDerivedStateFromProps` with simple usage) may need tuning after running against real codebases.

### 6. Git Branch Push — Existing `agentic/git.py` + New Push Function

The existing `git.py` covers local branch creation (`ensure_refactor_branch`) and commits (`commit_checkpoint`). What is missing is `git push origin <branch>`. This is a one-function addition to `agentic/git.py`:

```python
def push_branch(workspace: Path, branch: str, remote: str = "origin") -> str | None:
    """Push branch to remote. Returns error string or None on success."""
```

This is consistent with the existing subprocess pattern — no new library needed.

**Confidence:** HIGH.

---

## Libraries to Explicitly NOT Use

| Library | Why not |
|---|---|
| `jscodeshift` | Untyped Babel AST, no TypeScript type resolution, second engine — violates PROJECT.md constraint |
| `@babel/parser` / `@babel/traverse` | Same reason as jscodeshift |
| `react-codemod` (npm) | Built on jscodeshift; handles only simple JS cases, not typed TSX |
| `PyGithub` / `ghapi` / `pygithub` | New Python dependency for narrow use case; existing direct-HTTP pattern is sufficient and already proven |
| `gh` CLI via subprocess | Not guaranteed in Cloud Run containers |
| Separate `tsc` process as gate | Creates two compiler instances; `project.getPreEmitDiagnostics()` is equivalent and already wired |
| `@octokit/rest` (npm) | Not needed on the Node side — PR creation is Python-side; the TS bridge handles only AST operations |

---

## Complete Stack for the Migration Capability

| Layer | Component | Version | Status |
|---|---|---|---|
| TypeScript AST engine | ts-morph | 25.0.1 (locked) | Existing — extend only |
| Bridge runtime | tsx | 4.19.0 (locked) | Existing — no change |
| Bridge package manager | pnpm workspace | locked | Existing — no change |
| React AST analysis | ts-morph (new handlers in bridge) | 25.0.1 | New addition to bridge |
| TypeScript diagnostics | `project.getPreEmitDiagnostics()` via existing bridge | 25.0.1 | Existing — extend |
| tsc gate (PR description only) | `tsc --noEmit` subprocess | system tsc (from tsconfig target repo) | New thin wrapper in Python |
| Agent framework | pydantic-ai | 1.59.0+ (locked) | Existing — extend |
| Claude model | anthropic | 0.78.0–0.79.x (pinned) | Existing — no change |
| Migration triage | New `MigrationTriageResult` agent | pydantic-ai | New factory in `agentic/triage.py` |
| Git branch management | subprocess `git` | system git | Existing — add `push_branch` |
| PR creation | Direct HTTP to `api.github.com` | REST API v3 (2022-11-28 version header) | New Python module `agentic/github_pr.py` |
| Schedule models | Pydantic BaseModel | pydantic 2.x | Extend `schedule/models.py` |
| Schedule executor | `schedule/executor.py` | — | Extend dispatch for new op types |
| MCP migration tools | fastmcp | 2.14.0+ (locked) | Extend `mcp/server.py` |
| Logging | structlog | 24.1.0+ (locked) | Existing pattern — new logger.py per new package |

---

## Installation — What Changes

No new Python packages required. All needed Python capabilities are already available through the existing stack.

No new npm packages required. ts-morph 25.0.1 exposes all needed class introspection APIs.

Changes are purely code additions within existing packages:

**TypeScript (packages/ts-morph-bridge/src/):**
- New `react.ts` — React-specific bridge handlers
- Extend `handlers.ts` — register new commands (`classify_react_component`, `list_react_class_components`, `get_component_lifecycle_map`, `get_component_state_shape`, `apply_hooks_transform`, `get_diagnostic_summary`)
- Extend `index.ts` dispatch table

**Python (apps/backend/src/refactor_agent/):**
- `engine/typescript/models.py` (new) — `DiagnosticSummary`, `TscCheckResult`
- `engine/typescript/ts_morph_engine.py` (extend) — new bridge call wrappers for React commands, `get_diagnostic_summary`, `compiler_options_override` param on `__aenter__`
- `agentic/git.py` (extend) — `push_branch`
- `agentic/github_pr.py` (new) — `PrRequest`, `PrResult`, `PushResult`, `create_pull_request`, `add_labels`
- `agentic/triage.py` (extend) — `MigrationTriageResult`, `ComponentComplexity`, `create_migration_triage_agent`
- `schedule/models.py` (extend) — `MigrateClassToHooksOp`, `EnableStrictFlagOp`
- `schedule/executor.py` (extend) — dispatch for new op types
- `mcp/server.py` (extend) — new migration tool registrations

---

## Confidence Assessment

| Area | Confidence | Basis |
|---|---|---|
| ts-morph class introspection APIs | HIGH | APIs confirmed in existing `ast.ts` + `handlers.ts`; version 25.0.1 confirmed in lockfile |
| ts-morph as single engine (no Babel) | HIGH | Explicit PROJECT.md constraint + architectural consistency |
| `project.getPreEmitDiagnostics()` as tsc gate | HIGH | Already implemented in existing bridge `handleGetDiagnostics` |
| Direct HTTP for GitHub PR creation | HIGH | Matches established repo pattern in `github_api.ts` and `github_auth.py` |
| Git push via subprocess | HIGH | Matches established pattern in `agentic/git.py` |
| Complexity tier heuristics | MEDIUM | Based on React community migration practice; boundary cases need real-codebase validation |
| GitHub OAuth scope (`repo`) for push | MEDIUM | Token scoping not verified from inspected code; needs confirmation before shipping |
| `apply_hooks_transform` correctness for `medium` tier | MEDIUM | Class→hooks transform for `componentDidUpdate` with dependency arrays is non-trivial; test coverage needed |

---

## Sources

- Codebase inspection: `packages/ts-morph-bridge/src/ast.ts`, `handlers.ts`, `state.ts`, `types.ts`, `index.ts` — confirmed ts-morph 25.0.1 API usage (HIGH confidence)
- Codebase inspection: `apps/backend/src/refactor_agent/engine/typescript/ts_morph_engine.py` — confirmed existing bridge command set and `get_diagnostics` implementation (HIGH confidence)
- Codebase inspection: `apps/backend/src/refactor_agent/agentic/git.py` — confirmed subprocess git pattern (HIGH confidence)
- Codebase inspection: `functions/shared/src/github_api.ts` — confirmed direct-HTTP GitHub API pattern (HIGH confidence)
- Codebase inspection: `packages/ts-morph-bridge/package.json` + `pnpm-lock.yaml` — confirmed ts-morph@25.0.1 (HIGH confidence)
- Codebase inspection: `apps/backend/src/refactor_agent/schedule/models.py`, `executor.py` — confirmed extension pattern for new op types (HIGH confidence)
- Training knowledge: ts-morph class declaration API (`getClasses()`, `getMethods()`, `getProperties()`, `getBaseClass()`, `getImplements()`) — MEDIUM confidence (no external verification available; stable API since ts-morph v10 but not verified against v25 docs)
- Training knowledge: React lifecycle method names and hooks equivalence mapping — MEDIUM confidence (React 18/19 stable API; hooks are not changing)
- Training knowledge: GitHub REST API `POST /repos/{owner}/{repo}/pulls` endpoint — MEDIUM confidence (API stable since 2020; version header `2022-11-28` matches existing code)

*Note: WebSearch and WebFetch were unavailable during this research session. All "external" claims are from training data (cutoff August 2025) and are marked MEDIUM confidence. Codebase-derived claims are HIGH confidence.*
