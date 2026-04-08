# Phase 2: Classifier and tsc Gate - Research

**Researched:** 2026-04-01
**Domain:** React component complexity classification, PydanticAI agent patterns, per-file tsc fingerprint gating
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLASS-02 | Hard-block rules: `getSnapshotBeforeUpdate`, `componentDidCatch`, `forceUpdate` → `manual` unconditionally before AI runs | `ComponentInfo.lifecycle_methods` list (from Phase 1) already enumerates these; Python blocklist check against that list before classifier agent runs |
| CLASS-03 | AI triage agent assigns each remaining component a tier: `safe-auto`, `assisted`, or `manual`, with rationale string | New `create_migration_classifier_agent()` factory; `ComponentClassification` output type; same PydanticAI `Agent[OrchestratorDeps, ...]` pattern as `triage.py` |
| CLASS-04 | Tier criteria: `safe-auto` = no `componentDidUpdate`, no instance fields, no refs, no HOC; `assisted` = one or two of those; `manual` = remainder | Heuristic pre-filter in `migration/classifier.py` before LLM call; LLM used for edge cases or explicit `assisted` boundary judgment |
| CLASS-05 | Classification result includes rationale per component | `ComponentClassification.rationale: str` field on Pydantic model; populated by both heuristic path (fixed rationale strings) and AI path |
| TSC-01 | tsc diagnostics snapshot taken before any transformation (Error category only) | `TsMorphProjectEngine.get_diagnostics()` already returns `list[DiagnosticInfo]` with `severity` field; filter to `severity == "error"` |
| TSC-02 | tsc diagnostics snapshot taken after all transformations complete | Same `get_diagnostics()` call post-transform; `TscGate` holds both snapshots |
| TSC-03 | Per-file `(file, line, code)` fingerprinting — not total error count | `frozenset[tuple[str, int, int]]` built from `DiagnosticInfo.file_path`, `.line`, `.code`; delta = after_fingerprints - before_fingerprints |
| TSC-04 | If new errors detected, PR not opened; error report preserved | `TscGateResult.passed: bool`; if `False`, caller aborts PR creation; report contains new-error tuples |
| TSC-05 | tsc gate uses workspace's actual `tsconfig.json` — never hardcoded defaults | `TsMorphProjectEngine` already accepts `tsconfig_path` param; migration runner must auto-discover `workspace/tsconfig.json` and pass it |

</phase_requirements>

## Summary

Phase 2 builds two independent, self-contained modules: `migration/classifier.py` and
`migration/tsc_gate.py`. Both can be implemented as pure additions to the existing
`migration/` package without modifying any established code paths.

The classifier has two layers: (1) a deterministic Python blocklist check that routes
any component with `getSnapshotBeforeUpdate`, `componentDidCatch`, `getDerivedStateFromError`,
`forceUpdate`, string refs (`this.refs.*`), or `getDerivedStateFromProps` to `manual`
unconditionally — before any LLM call — and (2) a PydanticAI `Agent` that classifies
remaining components using the same factory pattern as the existing `agentic/triage.py`.
The heuristic pre-filter in the Python layer handles the clear-cut `safe-auto` and obvious
`manual` cases, leaving a narrower population for the LLM to classify.

The tsc gate wraps the already-implemented `TsMorphProjectEngine.get_diagnostics()`,
which returns `list[DiagnosticInfo]` including `file_path`, `line`, `code`, and
`severity`. The gate's only new work is: (1) filtering to `severity == "error"` only,
(2) converting the filtered list to a `frozenset` of `(file_path, line, code)` tuples
as fingerprints, and (3) computing the set difference (after minus before) to identify
new errors. No new bridge handlers are needed for the tsc gate.

**Primary recommendation:** Implement the tsc gate first (pure Python, no LLM
dependency, fully testable without a bridge process), then the classifier (LLM
dependency requires `TestModel`-based tests).

---

## Project Constraints (from CLAUDE.md)

- No `Any` from typing; no `object` as return type or to paper over untyped boundaries.
- No `# type: ignore` comments. No `# noqa` suppressions without explicit task approval.
- No `dict`, `Dict`, `TypedDict` in function signatures or return types — use Pydantic `BaseModel`.
- Use `X | None` not `Optional[X]`; use `list[X]` / `dict[K, V]` (builtins) not `List` / `Dict`.
- No imports from `typing`: `List`, `Dict`, `Tuple`, `Set`.
- When hitting a type error that cannot easily be fixed: stop and describe; propose a typed solution; do not suppress.
- Protected files — do NOT edit: `pyproject.toml` (lint/mypy sections), `.cursor/rules/*.mdc`, `CLAUDE.md`.
- Pre-commit fails → fix the code; do not add ignores.
- Absolute imports only; annotation-only imports in `TYPE_CHECKING` blocks.
- Google-style docstrings on all public functions and classes.
- Line length 88 characters (Python), enforced by ruff.
- Max cyclomatic complexity: 10; max statements per function: 40; max args per function: 6.
- Each new package needs `logger.py` exporting `logger` via `get_logger("refactor_agent.<package>")`.
- No `print()` in library code; pytest with `asyncio_mode = auto`; use `TestModel` for agent tests; warnings are errors.
- pnpm only for TypeScript; run `make ts-format-check`, `make ts-lint`, `make ts-typecheck` for TypeScript quality.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.x (pinned) | All structured output models (`ComponentClassification`, `MigrationScope`, `TscGateResult`, etc.) | Project-wide requirement; no `dict` in signatures |
| pydantic-ai | 1.59.0+ (pinned) | `ReactClassifier` agent (`Agent[OrchestratorDeps, ComponentClassification]`) | Already the project's AI agent framework; `TestModel` available for tests |
| TsMorphProjectEngine | existing (engine/typescript/) | tsc gate: `get_diagnostics()` → `list[DiagnosticInfo]` | Already fully wired; `get_diagnostics` implemented end-to-end in bridge |
| structlog | 24.1.0+ (pinned) | Structured logging via `migration/logger.py` | Per-package logger pattern already established in Phase 1 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest + pytest-asyncio | locked | Test runner; `asyncio_mode = auto` | All tests; no manual `@pytest.mark.asyncio` needed |
| pydantic-ai TestModel | 1.59.0+ | Classifier agent test isolation | Any test exercising the classifier agent; never call a real LLM in tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Heuristic-then-LLM two-layer classifier | Pure LLM classification | LLM alone is slower, costlier, non-deterministic for the blocklist cases which have no ambiguity |
| `frozenset` fingerprint for tsc gate | Error count comparison | Count comparison is gameable (new error masked by removed error); fingerprints catch per-file regressions correctly |
| `TsMorphProjectEngine.get_diagnostics()` | Subprocess `tsc --noEmit` | Two separate compiler instances can disagree; bridge is already wired with the correct tsconfig |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure for New Additions

```
apps/backend/src/refactor_agent/migration/
├── __init__.py          # (existing)
├── logger.py            # (existing)
├── models.py            # (existing) — extend with new models
├── classifier.py        # NEW: blocklist check + ReactClassifier agent
└── tsc_gate.py          # NEW: TscGate with before/after snapshot and fingerprint comparison

apps/backend/tests/test_migration/
├── __init__.py          # (existing)
├── test_models.py       # (existing)
├── test_classifier.py   # NEW: classifier unit tests (TestModel)
└── test_tsc_gate.py     # NEW: tsc gate unit tests (no LLM)
```

No new TypeScript bridge handlers are required for Phase 2. All tsc gate logic uses the
existing `get_diagnostics` bridge command. The classifier calls
`list_react_class_components` (Phase 1) to obtain `ComponentInfo` objects and then
applies heuristics + LLM.

### Pattern 1: Blocklist Hard-Block (classifier.py)

**What:** Before the AI agent runs, a pure Python function checks `ComponentInfo.lifecycle_methods`
for unmigrateable patterns and checks for `forceUpdate` and string refs. Any match
returns a `ComponentClassification` with `tier=MigrationTier.MANUAL` and a fixed
rationale string immediately.

**When to use:** Always. This runs before any LLM token is consumed.

**Example:**
```python
# Source: pattern derived from PITFALLS.md Pitfall 1 (HIGH confidence)

_HARD_BLOCK_LIFECYCLE_METHODS: frozenset[str] = frozenset(
    {
        "getSnapshotBeforeUpdate",
        "componentDidCatch",
        "getDerivedStateFromError",
        "getDerivedStateFromProps",
    }
)

def _apply_hard_blocks(info: ComponentInfo) -> ComponentClassification | None:
    """Return manual classification if any hard-block pattern is detected.

    Returns None if no hard blocks apply (component is a candidate for AI
    classification).

    Args:
        info: Component info from Phase 1 bridge scan.

    Returns:
        ComponentClassification with manual tier if blocked, else None.
    """
    methods = set(info.lifecycle_methods)
    blocked = methods & _HARD_BLOCK_LIFECYCLE_METHODS
    if blocked:
        return ComponentClassification(
            file_path=info.file_path,
            component_name=info.component_name,
            tier=MigrationTier.MANUAL,
            rationale=f"Hard-blocked: contains {', '.join(sorted(blocked))}",
        )
    # forceUpdate is not a lifecycle method but a call site — checked separately
    return None
```

Note: `forceUpdate` is not a lifecycle method; it is a call site in the component body.
The bridge handler does not currently detect `forceUpdate` call sites. Phase 2 needs to
either (a) add a lightweight check in the Python classifier by having the LLM inspect
the skeleton for `forceUpdate` usage, or (b) add a `has_force_update` field to
`ComponentInfo` via a bridge update. Option (a) is lower risk for Phase 2 scope.
The recommended approach: during classification the agent tool `show_file_skeleton`
exposes the full class body; the system prompt instructs the agent to route any component
with `forceUpdate` call sites to `manual`. The heuristic pre-filter handles lifecycle
method blocklist; `forceUpdate` is caught by the LLM pass with explicit instruction.

### Pattern 2: Heuristic Pre-Classification (classifier.py)

**What:** After blocklist check, apply deterministic heuristics from CLASS-04 to
pre-assign `safe-auto` for the simplest components. Only components that fall into
genuinely ambiguous territory go to the LLM.

**CLASS-04 criteria (from REQUIREMENTS.md):**
- `safe-auto` = no `componentDidUpdate`, no instance fields (beyond `state`), no refs,
  no HOC wrapping
- `assisted` = one or two of those present
- `manual` = remainder

**Implementation:**
```python
def _apply_heuristics(info: ComponentInfo) -> MigrationTier:
    """Apply CLASS-04 heuristic criteria to assign a preliminary tier.

    Args:
        info: Component info from Phase 1 bridge scan.

    Returns:
        Preliminary MigrationTier based on structural signals.
    """
    signals: int = 0
    if "componentDidUpdate" in info.lifecycle_methods:
        signals += 1
    if info.has_refs:
        signals += 1
    # has_state covers instance state; instance fields beyond state require
    # bridge extension — treat has_refs as proxy for now; see Open Questions
    if signals == 0:
        return MigrationTier.SAFE_AUTO
    if signals <= 2:
        return MigrationTier.ASSISTED
    return MigrationTier.MANUAL
```

The heuristic produces a `preliminary_tier`. The AI agent receives both the component
skeleton and the preliminary tier as context, then either confirms or overrides with a
rationale.

### Pattern 3: ReactClassifier Agent (classifier.py)

**What:** A PydanticAI agent following the exact `create_<name>_agent()` factory pattern
from `agentic/triage.py`. It receives `OrchestratorDeps` (which carries the workspace
and engine), uses a `show_file_skeleton` tool to inspect each component's source, and
returns a `ComponentClassification` output type.

**Agent type signature:**
```python
# Source: follows pattern in agentic/triage.py (create_triage_agent)
def create_migration_classifier_agent(
    model: Model | None = None,
) -> Agent[OrchestratorDeps, ComponentClassification]:
    ...
```

**System prompt instruction for `forceUpdate`:**
The agent system prompt must include an explicit instruction:
> If the component body contains `this.forceUpdate()`, assign `manual` tier unconditionally.
> Do not attempt heuristic scoring for this component.

### Pattern 4: tsc Gate Fingerprint Comparison (tsc_gate.py)

**What:** `TscGate` takes snapshots before and after transformations using
`TsMorphProjectEngine.get_diagnostics()`, filters to error-severity only, builds
fingerprint sets, and computes the difference.

**Data flow:**
```python
# Source: patterns from ARCHITECTURE.md and PITFALLS.md Pitfall 3 (HIGH confidence)

class TscGate:
    """Before/after tsc error fingerprint gate."""

    def __init__(self, engine: TsMorphProjectEngine) -> None: ...

    async def snapshot_before(self) -> TscSnapshot:
        """Take the pre-transformation diagnostic snapshot."""
        diags = await self._engine.get_diagnostics()
        errors = [d for d in diags if d.severity == "error"]
        fingerprints = frozenset(
            (d.file_path, d.line, d.code) for d in errors
        )
        return TscSnapshot(error_count=len(errors), fingerprints=fingerprints)

    async def snapshot_after(self) -> TscSnapshot: ...

    def compare(
        self,
        before: TscSnapshot,
        after: TscSnapshot,
    ) -> TscGateResult:
        """Compute new errors introduced since before snapshot."""
        new_errors = after.fingerprints - before.fingerprints
        return TscGateResult(
            before=before,
            after=after,
            new_errors=list(new_errors),
            passed=len(new_errors) == 0,
        )
```

**Key design decision:** The gate compares `after.fingerprints - before.fingerprints`
(set difference), not a count delta. This means:
- A pre-existing error that moves to a different line produces one removed and one new
  fingerprint. Treat moved errors as new errors to be conservative.
- Errors removed by the migration do not affect the pass/fail decision.
- Only new `(file, line, code)` tuples that were absent in the before snapshot cause
  a gate failure.

### Pattern 5: New Pydantic Models to Add to migration/models.py

The existing `migration/models.py` has only `ComponentInfo` and `ClassComponentList`
(Phase 1). Phase 2 extends it with:

```python
# Source: ARCHITECTURE.md models section; adapted to Phase 2 scope

from enum import StrEnum

class MigrationTier(StrEnum):
    """Migration complexity tier assigned by the classifier."""
    SAFE_AUTO = "safe-auto"
    ASSISTED = "assisted"
    MANUAL = "manual"


class ComponentClassification(BaseModel):
    """Classification result for a single React class component."""
    file_path: str
    component_name: str
    tier: MigrationTier
    rationale: str  # required — populated by heuristic or LLM path


class MigrationScope(BaseModel):
    """All components classified for a workspace migration run."""
    workspace: str  # str not Path — Pydantic serialization safety
    components: list[ComponentClassification]

    @property
    def safe_auto(self) -> list[ComponentClassification]:
        """Components eligible for automated transformation."""
        return [c for c in self.components if c.tier == MigrationTier.SAFE_AUTO]

    @property
    def assisted(self) -> list[ComponentClassification]:
        """Components requiring developer review."""
        return [c for c in self.components if c.tier == MigrationTier.ASSISTED]

    @property
    def manual(self) -> list[ComponentClassification]:
        """Components that cannot be automatically migrated."""
        return [c for c in self.components if c.tier == MigrationTier.MANUAL]


class TscSnapshot(BaseModel):
    """Point-in-time snapshot of tsc errors for the workspace."""
    error_count: int
    # frozenset is not JSON-serializable; store as list, reconstruct for comparison
    error_fingerprints: list[tuple[str, int, int]]  # (file_path, line, code)

    @property
    def fingerprint_set(self) -> frozenset[tuple[str, int, int]]:
        """Return fingerprints as a frozenset for set operations."""
        return frozenset(self.error_fingerprints)


class TscGateResult(BaseModel):
    """Result of before/after tsc fingerprint comparison."""
    before: TscSnapshot
    after: TscSnapshot
    new_errors: list[tuple[str, int, int]]  # new (file_path, line, code) tuples
    passed: bool  # True only if new_errors is empty
```

**Note on `frozenset` in Pydantic:** `frozenset` is not natively JSON-serializable by
Pydantic v2 without a custom serializer. The recommendation is to store fingerprints as
`list[tuple[str, int, int]]` in the model and expose a `frozenset` via a property.
Alternatively, a `model_validator` can handle (de)serialization. The `list` approach
is simpler and avoids any custom validator complexity.

**Note on `tuple[str, int, int]` in Pydantic:** Pydantic v2 supports `tuple[X, Y, Z]`
as a typed fixed-length tuple annotation. This is valid without `Any`. Confidence: HIGH
(Pydantic v2 tuple support is documented and established).

### Anti-Patterns to Avoid

- **Running the LLM classifier on blocklist components:** The blocklist check must run
  in Python before any LLM call. Blocklist decisions are not judgment calls — they are
  unconditional.
- **Using error count delta as the tsc gate metric:** A new error in file A can be masked
  by a removed error in file B. Only per-file `(file, line, code)` fingerprinting is
  correct.
- **Initialising `TsMorphProjectEngine` without a `tsconfig_path`:** The engine's
  fallback compiler options (`strict: true`, `ES2022`) differ from real project settings.
  The migration runner must always discover and pass `workspace/tsconfig.json`.
- **Storing `TscSnapshot` with a `frozenset` field:** Pydantic v2 requires custom
  serializers for `frozenset`. Use `list[tuple[str, int, int]]` as the stored type and
  expose a `frozenset` property.
- **Mutating the same `TsMorphProjectEngine` instance across before and after snapshots:**
  The tsc gate must use the same in-context engine instance across both snapshots, not
  two separate `async with` blocks (which would load the project twice).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| React lifecycle method enumeration | Enumerate method names from source text | `ComponentInfo.lifecycle_methods` from Phase 1 bridge | Already done; bridge handler enumerates all 9 lifecycle methods per component |
| TypeScript diagnostic collection | Subprocess `tsc --noEmit` with stdout parsing | `TsMorphProjectEngine.get_diagnostics()` | Already fully wired; matches the same compiler instance that runs with the workspace tsconfig |
| Error fingerprint storage | Custom dict or database | `frozenset[tuple[str, int, int]]` set difference | Standard Python set operations; no persistence needed between before/after within a single run |
| LLM agent wiring (model, tools, output type) | Custom LLM call with JSON parsing | `Agent[OrchestratorDeps, ComponentClassification]` (pydantic-ai) | Project-wide pattern; output validation, retry, TestModel isolation all included |
| Per-component rationale strings | Template-based string building | `ComponentClassification.rationale: str` populated by heuristic (fixed strings) or LLM | Both paths produce a rationale — heuristic path uses deterministic strings, LLM path uses generated text |

**Key insight:** Both the classifier and tsc gate are thin wrappers over Phase 1
infrastructure. The hard work (AST scanning, diagnostic collection) is already done.
Phase 2 is primarily about composing those results correctly and avoiding the known
failure modes (count gaming, LLM for blocklist decisions, wrong tsconfig).

---

## Common Pitfalls

### Pitfall 1: forceUpdate Not in Lifecycle Method List

**What goes wrong:** The blocklist check uses `ComponentInfo.lifecycle_methods` from
Phase 1. `forceUpdate` is not a lifecycle method — it is a method call anywhere in the
class body. The Phase 1 bridge handler does not detect it, so a component with
`this.forceUpdate()` in an event handler passes the blocklist check silently.

**Why it happens:** The bridge handler enumerates lifecycle method declarations by name.
`forceUpdate` is not declared on the component — it is called on `this` as an inherited
method. It does not appear in `cls.getMethods()` unless the component overrides it.

**How to avoid (two options — choose one per plan):**
1. Extend the Phase 1 bridge handler (`react.ts`) to add a `has_force_update: boolean`
   field by checking for `this.forceUpdate()` call expressions in the class body. This
   is the cleanest solution and extends `ComponentInfo`.
2. As a fallback: include explicit instruction in the classifier agent's system prompt to
   flag any component containing `this.forceUpdate` in its skeleton as `manual`. This
   relies on the LLM reading the skeleton.

Option 1 (bridge extension) is recommended: it makes the detection deterministic and
independent of LLM judgment. It requires a small addition to `react.ts` and a new field
in `ComponentInfo`.

**Warning signs:** A test workspace with `this.forceUpdate()` in an event handler
receives `safe-auto` or `assisted` tier classification.

### Pitfall 2: tsconfig Not Found — Engine Falls Back to Defaults

**What goes wrong:** `TsMorphProjectEngine` accepts `tsconfig_path: Path | None`.
When `None`, the bridge's `handleInitProject` falls back to hardcoded compiler options
(`strict: true`, `ES2022`). The before/after tsc fingerprints are taken against a
different set of compiler flags than the workspace's actual configuration.

**Why it happens:** There is no auto-discovery in `TsMorphProjectEngine.__init__`.
The migration runner must explicitly pass the tsconfig path.

**How to avoid:** `migration/tsc_gate.py` must not accept a `TsMorphProjectEngine`
that was initialized without a tsconfig. Add a startup assertion or require the
workspace path as input to `TscGate` and perform auto-discovery internally:
```python
def _find_tsconfig(workspace: Path) -> Path:
    """Auto-discover tsconfig.json in workspace root.

    Args:
        workspace: Root directory of the TypeScript project.

    Returns:
        Path to tsconfig.json.

    Raises:
        FileNotFoundError: If no tsconfig.json is found in workspace root.
    """
    candidates = [workspace / "tsconfig.json", workspace / "tsconfig.base.json"]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"No tsconfig.json found in {workspace}. "
        "The tsc gate requires the workspace's real tsconfig."
    )
```

**Warning signs:** Before-snapshot error count is suspiciously different from running
`tsc` manually in the workspace. The bridge's `init_project` result logs no tsconfig
path.

### Pitfall 3: Heuristic Misses Instance Fields Beyond `state`

**What goes wrong:** CLASS-04 requires detecting "no instance fields beyond `state`"
for `safe-auto` tier. The Phase 1 `ComponentInfo` includes `has_state` and `has_refs`
(based on `createRef`), but does NOT detect arbitrary instance fields (e.g.,
`this.timer: ReturnType<typeof setTimeout>`, `this.subscription: Subscription`).

**Why it happens:** The bridge handler checks `cls.getProperty("state")` and looks for
`createRef` in property initializers. Other property declarations on the class body are
not enumerated as a `has_instance_fields` signal.

**Consequence:** A component with `this.subscription = observable.subscribe(...)` in
`componentDidMount` and `this.subscription.unsubscribe()` in `componentWillUnmount`
receives `safe-auto` from the heuristic but is actually `assisted` (subscription management
via `useRef` is non-trivial).

**How to avoid (two options):**
1. Extend `react.ts` to add `instance_field_count: number` — count of class properties
   that are not `state` or a `createRef`. Add this to `ComponentInfo`.
2. Include the component skeleton in the classifier agent's tool output, and instruct the
   agent to check for non-standard instance properties as an `assisted` signal.

Option 1 (bridge extension) is again the more deterministic approach. Both options are
acceptable for Phase 2; the plan should choose one explicitly.

### Pitfall 4: PureComponent Classified as safe-auto When It Should Be assisted

**What goes wrong:** `PureComponent` extends are detected correctly by Phase 1, but the
heuristic does not flag `PureComponent` as an `assisted` signal. `React.memo` (the
intended hooks equivalent) does shallow comparison on props only, not state. If the
optimization relied on state comparison, the migration changes semantics.

**Why it happens:** `ComponentInfo` does not carry a `is_pure_component: bool` flag; the
heuristic cannot distinguish `extends Component` from `extends PureComponent` without
checking the base class name.

**How to avoid:** Add `extends_pure_component: bool` to `ComponentInfo` (bridge
extension) or derive it from `ComponentInfo.component_name` heuristically. The simpler
fix: add `extends_pure_component` to the bridge handler — it already has access to
`baseText`/`baseTextRoot` and can check for `"PureComponent"`.

### Pitfall 5: Two TsMorphProjectEngine Instances for Before/After

**What goes wrong:** If the tsc gate opens two separate `async with TsMorphProjectEngine(...)`
contexts (one for before, one for after), the after snapshot does not see the transform
changes because each context loads a fresh in-memory project from disk.

**Why it happens:** After transforms are applied via `apply_changes()`, the changes are
written to disk but the bridge process that took the before snapshot has been shut down.
Opening a new `async with` block creates a new bridge process that reads the disk
state — which is correct if transformations were committed. However, if transformations
are in-memory only (not yet written), the second context sees the pre-transform state.

**How to avoid:** Document that Phase 2 tests the tsc gate with a single engine context
that takes both snapshots. In Phase 3 (when transforms run), the executor will own the
engine context and pass it to `TscGate` for the after snapshot. Phase 2 implementation
should accept the engine as an injected dependency (`TscGate.__init__(engine: TsMorphProjectEngine)`)
rather than creating it internally.

---

## Code Examples

### TscSnapshot Construction from get_diagnostics

```python
# Source: derived from DiagnosticInfo definition in engine/base.py (HIGH confidence)
# and PITFALLS.md Pitfall 3 (HIGH confidence)

async def snapshot(engine: TsMorphProjectEngine) -> TscSnapshot:
    """Build a tsc error snapshot for the current project state."""
    diags = await engine.get_diagnostics()
    errors = [d for d in diags if d.severity == "error"]
    fingerprints = [(d.file_path, d.line, d.code) for d in errors]
    return TscSnapshot(
        error_count=len(errors),
        error_fingerprints=fingerprints,
    )
```

### Gate Comparison (set difference)

```python
# Source: PITFALLS.md Pitfall 3 — per-file fingerprinting pattern (HIGH confidence)

def compare(before: TscSnapshot, after: TscSnapshot) -> TscGateResult:
    """Identify errors introduced since the before snapshot."""
    before_set = before.fingerprint_set
    after_set = after.fingerprint_set
    new_errors = sorted(after_set - before_set)
    return TscGateResult(
        before=before,
        after=after,
        new_errors=new_errors,
        passed=len(new_errors) == 0,
    )
```

### ComponentClassification Model

```python
# Source: ARCHITECTURE.md models section; adapted to Phase 2 requirements (HIGH confidence)

class ComponentClassification(BaseModel):
    """Classification result for a single React class component."""

    file_path: str
    component_name: str
    tier: MigrationTier
    rationale: str  # Required — explains tier assignment for PR description
```

### tsconfig Auto-Discovery

```python
# Source: PITFALLS.md Pitfall 10 — tsconfig scope mismatch (HIGH confidence)

def _find_tsconfig(workspace: Path) -> Path:
    """Discover the workspace tsconfig.json.

    Args:
        workspace: Root directory of the TypeScript project.

    Returns:
        Path to the discovered tsconfig file.

    Raises:
        FileNotFoundError: If no tsconfig.json is present.
    """
    for name in ("tsconfig.json", "tsconfig.base.json"):
        candidate = workspace / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No tsconfig.json found in {workspace}. "
        "The tsc gate requires the workspace's actual tsconfig."
    )
```

### ReactClassifier Agent Factory Pattern

```python
# Source: agentic/triage.py create_triage_agent (HIGH confidence — direct codebase)

def create_migration_classifier_agent(
    model: Model | None = None,
) -> Agent[OrchestratorDeps, ComponentClassification]:
    """Create the React component classifier agent.

    Args:
        model: Optional model override. If None, uses configured default.

    Returns:
        A configured Agent ready to classify a single component.
    """
    if model is None:
        model = _build_default_model()
    agent: Agent[OrchestratorDeps, ComponentClassification] = Agent(
        model,
        deps_type=OrchestratorDeps,
        output_type=ComponentClassification,
        instructions=_CLASSIFIER_INSTRUCTIONS,
    )
    _register_classifier_tools(agent)
    return agent
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Total error count comparison for tsc gate | Per-file `(file, line, code)` fingerprint set difference | Phase 2 | Eliminates error count gaming; catches per-file regressions masked by unrelated changes |
| Single-agent classification (LLM decides everything) | Two-layer: deterministic blocklist → LLM for ambiguous cases | Phase 2 | Blocklist patterns (`getSnapshotBeforeUpdate`, `componentDidCatch`) are class-only permanently per React docs; they must never reach the LLM for a probabilistic decision |

**Deprecated/outdated:**
- Error count delta as the tsc safety signal: replaced by fingerprint set difference.
- `Optional[X]` in signatures: replaced by `X | None` per project CLAUDE.md.

---

## Open Questions

1. **Should `forceUpdate` detection be a bridge extension (new `has_force_update` field on `ComponentInfo`) or an LLM-only detection?**
   - What we know: `forceUpdate` is not a lifecycle method; Phase 1 bridge does not detect it; it is a blocklist item per CLASS-02.
   - What's unclear: Whether a one-line bridge extension (check for `this.forceUpdate()` call expressions in the class body) is within Phase 2 scope, or whether the plan defers it to the LLM system prompt instruction.
   - Recommendation: Include the bridge extension in Plan 1 of Phase 2. The bridge already has access to `cls` and can walk descendant call expressions. Relying on the LLM to catch a deterministic blocker is fragile.

2. **Should `instance_field_count` (non-state, non-ref instance fields) be added to `ComponentInfo` via a bridge extension in Phase 2?**
   - What we know: CLASS-04 requires "no instance fields beyond `state`" for `safe-auto`. Phase 1 `ComponentInfo` has `has_state` and `has_refs` but not a general instance-field count.
   - What's unclear: Whether adding `instance_field_count` to the bridge handler is within Phase 2 scope, or whether the LLM skeleton inspection is sufficient.
   - Recommendation: Add `instance_field_count: int` (count of class properties that are not `state` and not a `createRef` initializer) to the bridge handler. This is a small addition to `react.ts` and makes the `safe-auto` heuristic correctly honour CLASS-04.

3. **Should `extends_pure_component: bool` be added to `ComponentInfo`?**
   - What we know: `PureComponent` → `React.memo` has different semantics for state-based optimization.
   - What's unclear: Whether this is a Phase 2 or Phase 3 concern.
   - Recommendation: Add `extends_pure_component: bool` to Phase 2's bridge extension task. The bridge already has `baseTextRoot` computed; adding this check is trivial.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All Python code | Available | 3.14.3 | — |
| Node.js 24+ | ts-morph bridge subprocess | Available | 24.10.0 | — |
| pnpm | Bridge package management | Available | 10.12.1 | — |
| ts-morph 25.0.1 | Bridge handlers (if extended) | Available (locked) | 25.0.1 | — |
| pytest + pytest-asyncio | All Python tests | Available (locked) | current | — |
| pydantic-ai TestModel | Classifier agent tests | Available (locked) | 1.59.0+ | — |

No missing dependencies. Phase 2 can execute immediately.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio (`asyncio_mode = auto`) |
| Config file | `apps/backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd apps/backend && python -m pytest tests/test_migration/ -x -q` |
| Full suite command | `cd apps/backend && python -m pytest -x -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLASS-02 | `_apply_hard_blocks()` returns `manual` tier for component with `getSnapshotBeforeUpdate` | unit | `cd apps/backend && python -m pytest tests/test_migration/test_classifier.py -x -q` | No — Wave 0 |
| CLASS-02 | `_apply_hard_blocks()` returns `manual` for `componentDidCatch` | unit | `cd apps/backend && python -m pytest tests/test_migration/test_classifier.py -x -q` | No — Wave 0 |
| CLASS-02 | Component with `forceUpdate` receives `manual` tier (via bridge extension or LLM instruction) | unit/integration | `cd apps/backend && python -m pytest tests/test_migration/test_classifier.py -x -q` | No — Wave 0 |
| CLASS-02 | Component with none of the hard-block patterns returns `None` from `_apply_hard_blocks()` | unit | `cd apps/backend && python -m pytest tests/test_migration/test_classifier.py -x -q` | No — Wave 0 |
| CLASS-03 | Classifier agent called via `TestModel` returns a `ComponentClassification` with correct structure | unit | `cd apps/backend && python -m pytest tests/test_migration/test_classifier.py -x -q` | No — Wave 0 |
| CLASS-04 | `_apply_heuristics()` returns `safe-auto` for component with no `componentDidUpdate`, no refs | unit | `cd apps/backend && python -m pytest tests/test_migration/test_classifier.py -x -q` | No — Wave 0 |
| CLASS-04 | `_apply_heuristics()` returns `assisted` for component with `componentDidUpdate` present | unit | `cd apps/backend && python -m pytest tests/test_migration/test_classifier.py -x -q` | No — Wave 0 |
| CLASS-05 | `ComponentClassification.rationale` is non-empty for both heuristic and AI classification paths | unit | `cd apps/backend && python -m pytest tests/test_migration/test_classifier.py -x -q` | No — Wave 0 |
| TSC-01 | `TscGate.snapshot_before()` filters to `severity == "error"` only; warnings excluded | unit | `cd apps/backend && python -m pytest tests/test_migration/test_tsc_gate.py -x -q` | No — Wave 0 |
| TSC-02 | `TscGate.snapshot_after()` produces a second snapshot from same engine | unit | `cd apps/backend && python -m pytest tests/test_migration/test_tsc_gate.py -x -q` | No — Wave 0 |
| TSC-03 | `TscGate.compare()` uses set difference, not count delta; a new error in file A is detected even when an error in file B is removed | unit | `cd apps/backend && python -m pytest tests/test_migration/test_tsc_gate.py -x -q` | No — Wave 0 |
| TSC-04 | `TscGateResult.passed` is `False` when `new_errors` is non-empty | unit | `cd apps/backend && python -m pytest tests/test_migration/test_tsc_gate.py -x -q` | No — Wave 0 |
| TSC-05 | `_find_tsconfig()` raises `FileNotFoundError` when no tsconfig.json present; returns correct path when present | unit | `cd apps/backend && python -m pytest tests/test_migration/test_tsc_gate.py -x -q` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `cd apps/backend && python -m pytest tests/test_migration/ -x -q`
- **Per wave merge:** `cd apps/backend && python -m pytest -x -q`
- **Phase gate:** Full suite green + `make ts-typecheck` (if bridge is extended) before final verification

### Wave 0 Gaps

- [ ] `apps/backend/tests/test_migration/test_classifier.py` — covers CLASS-02 through CLASS-05
- [ ] `apps/backend/tests/test_migration/test_tsc_gate.py` — covers TSC-01 through TSC-05
- [ ] `apps/backend/src/refactor_agent/migration/classifier.py` — new module
- [ ] `apps/backend/src/refactor_agent/migration/tsc_gate.py` — new module
- [ ] Extended `ComponentInfo` Pydantic model fields in `migration/models.py` (new: `has_force_update`, `instance_field_count`, `extends_pure_component`)
- [ ] Extended `react.ts` bridge handler (if bridge extension approach chosen for `forceUpdate` and instance fields)
- [ ] New models in `migration/models.py`: `MigrationTier`, `ComponentClassification`, `MigrationScope`, `TscSnapshot`, `TscGateResult`

---

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection: `apps/backend/src/refactor_agent/migration/models.py` — confirmed `ComponentInfo`, `ClassComponentList` from Phase 1; these are the inputs to Phase 2 classifier
- Direct codebase inspection: `packages/ts-morph-bridge/src/react.ts` — confirmed lifecycle method list, `has_state`, `has_refs` detection; identified missing `has_force_update` and `instance_field_count`
- Direct codebase inspection: `apps/backend/src/refactor_agent/engine/typescript/ts_morph_engine.py` — confirmed `get_diagnostics()` returns `list[DiagnosticInfo]` with `severity` field; confirmed `tsconfig_path` is optional (fallback to defaults if None)
- Direct codebase inspection: `apps/backend/src/refactor_agent/engine/base.py` — confirmed `DiagnosticInfo` dataclass with `file_path`, `line`, `code`, `severity` fields
- Direct codebase inspection: `packages/ts-morph-bridge/src/handlers.ts` (lines 257–284) — confirmed `getPreEmitDiagnostics()` returns all severity levels including suggestions; filter to error category is the caller's responsibility
- Direct codebase inspection: `apps/backend/src/refactor_agent/agentic/triage.py` — confirmed `create_triage_agent()` factory pattern, `Agent[OrchestratorDeps, TriageResult]` type, tool registration pattern; Phase 2 classifier follows this exactly
- Direct codebase inspection: `.planning/research/PITFALLS.md` — Pitfall 1 (false-positive safe-auto), Pitfall 3 (count gaming), Pitfall 10 (tsconfig mismatch); all HIGH confidence
- Direct codebase inspection: `.planning/REQUIREMENTS.md` — CLASS-02, CLASS-03, CLASS-04, CLASS-05, TSC-01 through TSC-05 verbatim requirements
- Phase 1 completion summaries: `01-01-SUMMARY.md`, `01-02-SUMMARY.md` — confirmed actual implementation patterns and decisions (KeyError not ValueError, baseTextRoot detection strategy, noqa: TC001 placement)

### Secondary (MEDIUM confidence)

- Training knowledge: `frozenset` set difference semantics in Python — standard Python; not verified against any external source but universally established
- Training knowledge: Pydantic v2 `tuple[str, int, int]` annotation support — stable feature; not live-verified against v2 docs
- Training knowledge: `StrEnum` as base class for `MigrationTier` — Python 3.11+ stdlib; Python 3.12 confirmed in environment

### Tertiary (LOW confidence)

None identified. All claims are grounded in direct codebase inspection or stable language features.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all technology decisions derived from direct inspection of Phase 1 implementation and existing codebase patterns
- Architecture: HIGH — classifier and tsc gate patterns derived from existing `triage.py` and `ts_morph_engine.py` code; no speculative components
- Pitfalls: HIGH — all sourced from PITFALLS.md (itself derived from react.dev and direct codebase inspection) plus one new pitfall (two-engine-context trap) identified from reading the implementation

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable stack; no external dependencies that change frequently)
