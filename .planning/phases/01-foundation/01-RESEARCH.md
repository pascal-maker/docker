# Phase 1: Foundation - Research

**Researched:** 2026-04-01
**Domain:** Python exception handler typing, A2A executor request-scoped state, ts-morph React class component detection
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Bare exception handlers in engine subprocess path replaced with typed handlers and git rollback | Identified exact bare `except Exception` handlers in `orchestrator/agent.py` (lines 156, 183, 359); `SubprocessError` already defined and used in the typed path — bare handlers need to be narrowed to it |
| INFRA-02 | Module-level global state in `a2a/executor.py` replaced with request-scoped context | Module-level `_orchestrator_state: dict[str, OrchestratorStateEntry]` at line 55 of `a2a/executor.py` identified; `ASTRefactorAgentExecutor.__init__` already accepts an injected `StateStore`; default fallback to the module-level dict is the gap |
| CLASS-01 | System detects all React class components in a TypeScript workspace via AST analysis | ts-morph 25.0.1 already used in bridge; `sf.getClasses()` and `getBaseClass()` available; new `react.ts` handler and Python wrapper pattern confirmed in `ts_morph_engine.py` |

</phase_requirements>

## Summary

Phase 1 has three requirements. Two are infrastructure prerequisites (INFRA-01, INFRA-02) that fix existing technical debt; one is the first functional feature (CLASS-01). All three involve code additions or narrow targeted edits to existing modules — no new packages are needed.

INFRA-01 targets bare `except Exception` handlers specifically in the path that the migration engine will call: `orchestrator/agent.py` contains three such handlers. The typed exception type (`SubprocessError`) is already defined in `engine/subprocess_engine.py` and is already used correctly in `_rename_typescript()` and `show_file_skeleton`. The bare handlers in `_check_all_collisions()` and `_apply_renames_per_file()` use `except Exception as e:` to skip files — these are legitimate "skip on parse failure" patterns and should remain, but restricted to `SubprocessError` (engine errors) not `Exception`. The one in `show_file_skeleton` for Python parsing (`except Exception:` at line 359) wraps `EngineRegistry.create()` and is genuinely a "can't parse this file" guard — acceptable with a narrowed type and a log call.

INFRA-02 is a dependency injection fix. `ASTRefactorAgentExecutor.__init__` already accepts a `StateStore | None` parameter and correctly uses injected state when provided. The only issue is the default: when `state_store is None`, it falls back to `_orchestrator_state` — the module-level dict. Removing the fallback and requiring either injection or a fresh `StateStore()` per instance eliminates the shared state. The module-level dict `_orchestrator_state` itself can then be removed.

CLASS-01 requires a new TypeScript bridge handler (`list_react_class_components`) and a corresponding Python wrapper method on `TsMorphProjectEngine`. The extension pattern is fully established: add a handler function in `handlers.ts`, export it, register it in `index.ts`'s dispatch table, add a Python wrapper calling `self._call(...)` in `ts_morph_engine.py`. The ts-morph APIs needed (`sf.getClasses()`, `cls.getBaseClass()`, `cls.getMethods()`, `cls.getProperties()`) are already used in `ast.ts` and `handlers.ts`.

**Primary recommendation:** Implement INFRA-01 and INFRA-02 first (they are targeted edits to existing code), then CLASS-01 (pure additions). All three are self-contained within this phase.

---

## Project Constraints (from CLAUDE.md)

The following directives from CLAUDE.md govern all code written in this phase:

- No `Any` from typing. No `object` as return type or to paper over untyped boundaries.
- No `# type: ignore` comments.
- No `# noqa` suppressions (except existing ones already in place; do not add new ones without explicit task approval).
- No new entries in `pyproject.toml` per-file ignores.
- No broadening of existing mypy overrides.
- No `dict`, `Dict`, `TypedDict` in function signatures or return types. Use Pydantic `BaseModel` for structured data.
- Use `X | None` not `Optional[X]`.
- Use `list[X]`, `dict[K, V]` (builtin) not `List`, `Dict` from `typing`.
- No imports from `typing`: `List`, `Dict`, `Tuple`, `Set`.
- When hitting a type error that cannot easily be fixed: stop and describe the problem; propose a typed solution; do not suppress.
- Protected files — do NOT edit: `pyproject.toml` (lint/mypy sections), `.cursor/rules/*.mdc`, `CLAUDE.md`.
- If pre-commit fails, fix the underlying code; do not add ignores.
- Absolute imports only. Annotation-only imports in `TYPE_CHECKING` blocks with `from __future__ import annotations`.
- Google-style docstrings on all public functions and classes.
- Line length 88 characters (Python), enforced by ruff.
- Max function complexity 10 (mccabe), max statements 40, max args 6.
- Each new package needs a `logger.py` exporting `logger` created via `get_logger("refactor_agent.<package>")`.
- No `print()` in library code.
- pytest with `asyncio_mode = auto`; use `TestModel` for agent tests; warnings are errors.
- pnpm only for TypeScript; run `make ts-format-check`, `make ts-lint`, `make ts-typecheck` for TypeScript quality checks.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ts-morph | 25.0.1 (locked in pnpm-lock.yaml) | TypeScript AST read/write — React class detection | Already the sole engine; `sf.getClasses()`, `getBaseClass()`, `getMethods()` already in use in `ast.ts` |
| pydantic | 2.x (pinned) | All structured data models | Project-wide requirement; `BaseModel` for all return types |
| structlog | 24.1.0+ (locked) | Structured logging | Per-package `logger.py` pattern already established |
| SubprocessError | `engine/subprocess_engine.py` | Typed exception for bridge failures | Already defined and used in the typed handlers; bare handlers must be narrowed to this type |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest + pytest-asyncio | current (locked) | Test runner; asyncio_mode=auto | All new tests |
| pydantic-ai TestModel | 1.59.0+ | Agent test isolation | Any test touching an agent; never call real LLM in tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ts-morph for class detection | Babel / jscodeshift | Banned by PROJECT.md constraint; no TypeScript type awareness |
| SubprocessError narrowing | bare `except Exception` | Bare catch swallows all errors including programming mistakes; must narrow |
| Injected StateStore per instance | module-level global dict | Global dict is not Cloud Run safe; concurrent requests corrupt each other |

**Installation:** No new packages required. All needed capabilities exist in the locked dependency set.

---

## Architecture Patterns

### Recommended Project Structure for New Additions

```
apps/backend/src/refactor_agent/
└── migration/
    ├── __init__.py          # empty
    ├── logger.py            # get_logger("refactor_agent.migration")
    └── models.py            # Phase 1: ComponentInfo, ClassComponentList Pydantic models

packages/ts-morph-bridge/src/
├── react.ts                 # New: handleListReactClassComponents
└── handlers.ts              # (unchanged in Phase 1; react.ts is its own file)
```

Note: `index.ts` in the bridge will need one new import and one new dispatch entry.

### Pattern 1: Bridge Handler Extension

**What:** Add a new TypeScript handler in `packages/ts-morph-bridge/src/react.ts`, export it, register it in `index.ts`.

**When to use:** Any new bridge command that the Python engine needs to call.

**Example (existing pattern from `handlers.ts`):**
```typescript
// Source: packages/ts-morph-bridge/src/handlers.ts (handleGetDiagnostics)
export function handleGetDiagnostics(
  params: Record<string, unknown>
): DiagnosticEntry[] {
  const p = requireProject();
  const filePath = optionalString(params, "file_path");
  const diagnostics = filePath
    ? p.getSourceFile(filePath)?.getPreEmitDiagnostics() ?? []
    : p.getPreEmitDiagnostics();
  return diagnostics.map(d => ({ ... }));
}
```

New handler for CLASS-01 follows the same signature: receives `Record<string, unknown>` params, returns a typed array. Uses `p.getSourceFiles()` to walk the project and `sf.getClasses()` per file to find class declarations.

**Registration in `index.ts`:**
```typescript
// Add to import block:
import { handleListReactClassComponents } from "./react.js";

// Add to handlers map:
list_react_class_components: handleListReactClassComponents,
```

### Pattern 2: Python Engine Wrapper Method

**What:** Add a new `async def` method on `TsMorphProjectEngine` that calls `self._call(method_name, JsonRpcParams.model_validate({...}))` and maps the result to a typed Pydantic model.

**When to use:** Every new bridge command needs a corresponding Python wrapper.

**Example (existing pattern from `ts_morph_engine.py`):**
```python
# Source: apps/backend/src/refactor_agent/engine/typescript/ts_morph_engine.py
async def get_diagnostics(
    self,
    file_path: str | None = None,
) -> list[DiagnosticInfo]:
    """Return TypeScript diagnostics for a file or whole project."""
    result = await self._call(
        "get_diagnostics",
        JsonRpcParams.model_validate(
            {"file_path": file_path} if file_path is not None else {}
        ),
    )
    if not isinstance(result, list):
        return []
    return [
        DiagnosticInfo(
            file_path=item.get("file", ""),
            ...
        )
        for item in result
        if isinstance(item, dict)
    ]
```

The CLASS-01 wrapper follows this exact pattern: call `"list_react_class_components"`, receive a list of dicts, map to a new Pydantic model `ComponentInfo`.

### Pattern 3: Typed Exception Narrowing (INFRA-01)

**What:** Replace `except Exception as e:` with `except SubprocessError as e:` in the engine subprocess path.

**When to use:** Any handler that calls `EngineRegistry.create()` or a subprocess engine method.

**Current bare handlers to fix (all in `orchestrator/agent.py`):**

| Location | Current | Fix |
|----------|---------|-----|
| `_check_all_collisions()` line 156 | `except Exception as e:` | `except SubprocessError as e:` — engine creation/call failures only |
| `_apply_renames_per_file()` line 183 | `except Exception as e:` | `except SubprocessError as e:` — engine creation/call failures only |
| `show_file_skeleton` tool line 359 | `except Exception:` | `except (SubprocessError, ValueError) as e:` — parse failures + add `logger.debug(...)` |

Note: `schedule/executor.py` line 267 has `except Exception as e:` — this is a legitimate top-level schedule boundary handler (logs + returns `ScheduleResult(success=False, ...)`). It is NOT in the engine subprocess path and is acceptable as-is. Do not change it.

### Pattern 4: Request-Scoped State Injection (INFRA-02)

**What:** Remove the module-level `_orchestrator_state` fallback from `ASTRefactorAgentExecutor.__init__`. When `state_store` is `None`, create a fresh `StateStore()` instance per executor instance rather than falling back to the module-level dict.

**Current code (a2a/executor.py lines 55, 226–228):**
```python
# Module level — REMOVE:
_orchestrator_state: dict[str, OrchestratorStateEntry] = {}

# In __init__ — CHANGE:
self._state_store: dict[str, OrchestratorStateEntry] = (
    state_store.root if state_store is not None else _orchestrator_state
)
```

**Fixed pattern:**
```python
# __init__ — no fallback to module-level dict:
self._state_store: dict[str, OrchestratorStateEntry] = (
    state_store.root if state_store is not None else {}
)
```

This creates a fresh per-instance dict. The module-level `_orchestrator_state` can be deleted. Concurrent `ASTRefactorAgentExecutor` instances will each have isolated state.

Note: The `StateStore` wrapper type (`RootModel[dict[str, OrchestratorStateEntry]]`) already exists in `a2a/models.py`. No new types are needed.

### Anti-Patterns to Avoid

- **Bare `except Exception` in subprocess path:** Swallows programming errors (AttributeError, TypeError) alongside expected engine failures, making debugging impossible.
- **Using `_orchestrator_state` module-level dict as the default:** The A2A server runs on Cloud Run which may handle multiple requests with the same process; module-level state is shared across all requests.
- **Adding a second AST engine (Babel, jscodeshift) for CLASS-01:** Banned by PROJECT.md; ts-morph 25.0.1 already provides all needed APIs.
- **Putting React detection logic in Python rather than the TypeScript bridge:** The bridge has direct access to the TypeScript compiler API and can inspect `extends React.Component` heritage clauses accurately; Python string search cannot.
- **Using `dict` in the new `TsMorphProjectEngine.list_react_class_components()` return type:** Must return `list[ComponentInfo]` where `ComponentInfo` is a Pydantic `BaseModel`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TypeScript class declaration inspection | Python AST or regex scan of `.tsx` files | `sf.getClasses()` + `cls.getBaseClass().getText()` in ts-morph bridge | ts-morph has the TypeScript compiler's type resolver; Python string matching will produce false positives on `class Foo extends Bar<Component>` etc. |
| Per-request state isolation in A2A | Custom lock/sync mechanism | Fresh `StateStore` instance per `ASTRefactorAgentExecutor` | The instance already owns its `_state_store` dict; isolation is achieved by not sharing the module-level dict |
| Typed exception hierarchy for bridge | New exception classes | `SubprocessError` (already in `engine/subprocess_engine.py`) | Already defined, already imported in the files that need it |
| `React.Component` heritage detection | String matching on source text | `cls.getBaseClass()` or `cls.getImplements()` in ts-morph | ts-morph resolves type aliases; `Component` and `React.Component` both resolve correctly |

---

## Common Pitfalls

### Pitfall 1: Narrowing `except Exception` Too Aggressively

**What goes wrong:** If `_check_all_collisions()` and `_apply_renames_per_file()` are changed to only catch `SubprocessError`, but `EngineRegistry.create()` raises `ValueError` or `KeyError` for unrecognised language strings, those become uncaught and crash the orchestrator.

**Why it happens:** `EngineRegistry.create()` can raise non-`SubprocessError` exceptions for configuration errors distinct from subprocess failures.

**How to avoid:** Verify what `EngineRegistry.create()` can raise before narrowing. If it can raise `ValueError` for unsupported languages, catch that separately and log at debug level (same as currently). The fix is `except (SubprocessError, ValueError) as e:` not just `except SubprocessError as e:` if the registry can raise ValueError. Inspect `engine/registry.py` before writing the fix.

**Warning signs:** Tests start failing with `ValueError` or `KeyError` uncaught exceptions after the change.

### Pitfall 2: React Component Detection Misses `Component` (short form) Import

**What goes wrong:** A component file imports `{ Component }` from `"react"` and writes `class Foo extends Component`. The detection logic only checks for `extends React.Component` and misses this form.

**Why it happens:** Both forms are idiomatic React. A ts-morph check using only `getBaseClass().getText() === "React.Component"` will miss `extends Component`.

**How to avoid:** The bridge handler must check for both `extends React.Component<...>` and `extends Component<...>` (or `extends PureComponent<...>`). The simplest approach: check if `getBaseClass()?.getName()` is one of `["Component", "PureComponent"]` or if the full text matches `React.Component` / `React.PureComponent`.

**Warning signs:** A test workspace with `import { Component } from 'react'` returns zero results.

### Pitfall 3: INFRA-02 Fix Breaks the Pause/Resume A2A Flow

**What goes wrong:** After removing the module-level dict fallback, the A2A pause/resume flow stops working because resumption looks up `self._state_store.get(task_id)` and gets `None` — the state was stored in a previous executor instance's dict.

**Why it happens:** The A2A framework may construct a new `ASTRefactorAgentExecutor` instance per request if it is not a singleton.

**How to avoid:** Verify how `ASTRefactorAgentExecutor` is instantiated in `a2a/server.py` before removing the module-level dict. If a new instance is created per request, the pause/resume flow requires an external store (Firestore/Redis) or the module-level dict must be preserved for that specific use case. The research finding: check `a2a/server.py` to confirm whether the executor is a singleton or recreated per request. If it is a singleton (constructed once and reused), the per-instance `{}` fix works correctly.

**Warning signs:** Pause/resume test `test_executor_resumes_from_saved_state_on_second_call` fails after the fix.

### Pitfall 4: Bridge Handler Returns Partial Data When No React Classes Found

**What goes wrong:** The `handleListReactClassComponents` bridge handler returns an empty list `[]` for a project with no React class components, but Python code checks `if not result` and treats that as an error rather than a valid empty result.

**Why it happens:** `_call()` returns `object`; the Python wrapper must explicitly handle the empty list case.

**How to avoid:** The Python wrapper must handle `isinstance(result, list)` returning `True` with `len(result) == 0` as a success case (no components found), not an error.

---

## Code Examples

### React Class Component Detection (Bridge Handler, new `react.ts`)

```typescript
// Follows the pattern from packages/ts-morph-bridge/src/handlers.ts

import { requireProject } from "./state.js";

// Lifecycle methods that require detection for CLASS-01 inventory
const REACT_LIFECYCLE_METHODS = [
  "componentDidMount",
  "componentDidUpdate",
  "componentWillUnmount",
  "shouldComponentUpdate",
  "getSnapshotBeforeUpdate",
  "getDerivedStateFromProps",
  "componentDidCatch",
  "getDerivedStateFromError",
  "render",
];

const REACT_BASE_CLASSES = new Set(["Component", "PureComponent"]);

export function handleListReactClassComponents(
  _params: Record<string, unknown>
): ComponentEntry[] {
  const p = requireProject();
  const entries: ComponentEntry[] = [];

  for (const sf of p.getSourceFiles()) {
    for (const cls of sf.getClasses()) {
      const baseName = cls.getBaseClass()?.getName() ?? "";
      const baseText = cls.getExtends()?.getExpression().getText() ?? "";
      const isReactClass =
        REACT_BASE_CLASSES.has(baseName) ||
        baseText.startsWith("React.Component") ||
        baseText.startsWith("React.PureComponent");
      if (!isReactClass) continue;

      const lifecycleMethods = REACT_LIFECYCLE_METHODS.filter(
        (m) => cls.getMethod(m) !== undefined
      );
      const hasState = cls.getProperty("state") !== undefined;
      const hasRefs = cls
        .getProperties()
        .some((p) =>
          p.getInitializer()?.getText().includes("createRef")
        );

      entries.push({
        file_path: sf.getFilePath(),
        component_name: cls.getName() ?? "",
        lifecycle_methods: lifecycleMethods,
        has_state: hasState,
        has_refs: hasRefs,
        line: cls.getStartLineNumber(),
      });
    }
  }
  return entries;
}

interface ComponentEntry {
  file_path: string;
  component_name: string;
  lifecycle_methods: string[];
  has_state: boolean;
  has_refs: boolean;
  line: number;
}
```

### Python Wrapper Method on `TsMorphProjectEngine`

```python
# Source: follows exact pattern of get_diagnostics() in ts_morph_engine.py

async def list_react_class_components(self) -> list[ComponentInfo]:
    """Return all React class components found in the project.

    Returns:
        List of ComponentInfo for each class extending React.Component
        or React.PureComponent found across all project source files.
    """
    result = await self._call(
        "list_react_class_components",
        JsonRpcParams(),
    )
    if not isinstance(result, list):
        return []
    return [
        ComponentInfo(
            file_path=item.get("file_path", ""),
            component_name=item.get("component_name", ""),
            lifecycle_methods=item.get("lifecycle_methods", []),
            has_state=bool(item.get("has_state", False)),
            has_refs=bool(item.get("has_refs", False)),
            line=int(item.get("line", 0)),
        )
        for item in result
        if isinstance(item, dict) and item.get("component_name")
    ]
```

### Pydantic Model for CLASS-01 Output (`migration/models.py`)

```python
# Strict-typed per CLAUDE.md: no dict in signature, no Any, use | None
from __future__ import annotations
from pydantic import BaseModel


class ComponentInfo(BaseModel):
    """A single React class component found in the workspace."""

    file_path: str
    component_name: str
    lifecycle_methods: list[str]
    has_state: bool
    has_refs: bool
    line: int


class ClassComponentList(BaseModel):
    """Result of scanning a workspace for React class components."""

    workspace: str  # str not Path — Pydantic serialization safety
    components: list[ComponentInfo]

    @property
    def count(self) -> int:
        """Total number of detected class components."""
        return len(self.components)
```

### Typed Exception Handler Fix (INFRA-01)

```python
# Source: apps/backend/src/refactor_agent/orchestrator/agent.py

# BEFORE (bare — swallows all exceptions):
try:
    engine = EngineRegistry.create(deps.language, source)
except Exception as e:
    logger.debug("Skip file", path=str(fp), error=str(e))
    continue

# AFTER (narrowed — only expected engine-creation failures):
from refactor_agent.engine.subprocess_engine import SubprocessError

try:
    engine = EngineRegistry.create(deps.language, source)
except (SubprocessError, ValueError) as e:
    # SubprocessError: bridge process error
    # ValueError: unsupported language or invalid source
    logger.debug("Skip file", path=str(fp), error=str(e))
    continue
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All Python code | Available | 3.14.3 | — |
| Node.js 24+ | ts-morph bridge subprocess | Available | 24.10.0 | — |
| pnpm | Bridge package management | Available | 10.12.1 | — |
| ts-morph 25.0.1 | React class detection handler | Available (locked in pnpm-lock.yaml) | 25.0.1 | — |
| pytest + pytest-asyncio | All Python tests | Available (locked in pyproject.toml) | current | — |

No missing dependencies. Phase 1 can execute immediately.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio (asyncio_mode = auto) |
| Config file | `apps/backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd apps/backend && python -m pytest tests/test_a2a/ tests/test_engine/ -x -q` |
| Full suite command | `cd apps/backend && python -m pytest -x -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `_check_all_collisions` and `_apply_renames_per_file` catch `SubprocessError` and `ValueError` only, not bare `Exception`; a `TypeError` propagates | unit | `cd apps/backend && python -m pytest tests/test_orchestrator/ -x -q` | Existing dir; new test needed |
| INFRA-01 | `show_file_skeleton` Python path logs and returns error string on parse failure, not swallowing | unit | `cd apps/backend && python -m pytest tests/test_orchestrator/ -x -q` | Existing dir; new test needed |
| INFRA-02 | Two `ASTRefactorAgentExecutor` instances do not share state; storing in instance A is not visible to instance B | unit | `cd apps/backend && python -m pytest tests/test_a2a/ -x -q` | `test_executor.py` exists; new test case needed |
| CLASS-01 | `list_react_class_components()` returns all class components (including `extends Component` short form) from a test workspace | integration | `cd apps/backend && python -m pytest tests/test_engine/test_ts_morph_project_engine.py -x -q` | `test_ts_morph_project_engine.py` exists; new test case needed |
| CLASS-01 | `list_react_class_components()` returns empty list (not error) for workspace with no React class components | unit | `cd apps/backend && python -m pytest tests/test_engine/test_ts_morph_project_engine.py -x -q` | `test_ts_morph_project_engine.py` exists; new test case needed |
| CLASS-01 | `ComponentInfo` and `ClassComponentList` Pydantic models validate correctly | unit | `cd apps/backend && python -m pytest tests/ -k "migration" -x -q` | New test file needed |

### Sampling Rate

- **Per task commit:** `cd apps/backend && python -m pytest tests/test_a2a/ tests/test_engine/ -x -q`
- **Per wave merge:** `cd apps/backend && python -m pytest -x -q`
- **Phase gate:** Full suite green + `make ts-typecheck` passes before final verification

### Wave 0 Gaps

- [ ] `tests/test_orchestrator/test_exception_narrowing.py` — covers INFRA-01 (new tests for narrowed exception handlers)
- [ ] New test case in `tests/test_a2a/test_executor.py` — covers INFRA-02 (instance isolation)
- [ ] New test cases in `tests/test_engine/test_ts_morph_project_engine.py` — covers CLASS-01 (component detection)
- [ ] `apps/backend/src/refactor_agent/migration/` package with `__init__.py`, `logger.py`, `models.py` — `ComponentInfo` and `ClassComponentList` models needed before tests can import them

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Module-level global state in `_orchestrator_state` | Per-instance `StateStore` (already injected in tests) | This phase (INFRA-02) | Concurrent A2A jobs no longer corrupt each other's context |
| Bare `except Exception` in file-skip paths | Narrowed `except (SubprocessError, ValueError)` | This phase (INFRA-01) | Partial transform failures surface as explicit errors instead of silent skips |
| No React class detection | `list_react_class_components` bridge command + Python wrapper | This phase (CLASS-01) | Phase 2 classifier can enumerate all migration targets |

---

## Open Questions

1. **Does `ASTRefactorAgentExecutor` get instantiated once (singleton) or once per request?**
   - What we know: `a2a/server.py` uses `build_app()` to wire up the A2A application; the executor is passed in.
   - What's unclear: Whether `build_app()` creates the executor once or the A2A framework recreates it per request.
   - Recommendation: Read `a2a/server.py` before implementing INFRA-02. If it is a singleton, per-instance `{}` works. If recreated per request, the pause/resume flow requires an external state store — a larger change than this phase intends. If singleton confirmed: proceed with INFRA-02 as scoped. If not singleton: narrow INFRA-02 scope to removing the module-level dict export only (making the fallback a fresh local `{}` per instance), which still prevents shared state across concurrent executors but preserves the singleton's resume behaviour if it exists.

2. **Can `EngineRegistry.create()` raise exceptions other than `SubprocessError`?**
   - What we know: `engine/registry.py` exists and is the factory for `LibCSTEngine` and `TsMorphProjectEngine`.
   - What's unclear: Exact exception types on unsupported language or invalid source.
   - Recommendation: Read `engine/registry.py` before finalising the exception narrowing in INFRA-01. Add the correct exception types to the `except` clause.

---

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection: `apps/backend/src/refactor_agent/a2a/executor.py` — module-level `_orchestrator_state` at line 55; `ASTRefactorAgentExecutor.__init__` fallback pattern at lines 226–228
- Direct codebase inspection: `apps/backend/src/refactor_agent/orchestrator/agent.py` — bare `except Exception` at lines 156, 183, 359
- Direct codebase inspection: `apps/backend/src/refactor_agent/engine/subprocess_engine.py` — `SubprocessError` definition; typed `_call()` method
- Direct codebase inspection: `apps/backend/src/refactor_agent/engine/typescript/ts_morph_engine.py` — `TsMorphProjectEngine.get_diagnostics()` as the canonical wrapper pattern
- Direct codebase inspection: `packages/ts-morph-bridge/src/handlers.ts` — `handleGetDiagnostics` and `handleInitProject` as canonical handler patterns; `sf.getClasses()` usage
- Direct codebase inspection: `packages/ts-morph-bridge/src/index.ts` — dispatch table registration pattern
- Direct codebase inspection: `packages/ts-morph-bridge/src/ast.ts` — `sf.getClasses()`, `Node.isClassDeclaration()` already in use
- Direct codebase inspection: `apps/backend/tests/test_a2a/test_executor.py` — existing test patterns for A2A executor
- Direct codebase inspection: `apps/backend/tests/test_engine/test_ts_morph_project_engine.py` — existing engine test patterns
- Direct codebase inspection: `apps/backend/pyproject.toml` — pytest configuration (asyncio_mode, filterwarnings=error)
- Direct codebase inspection: `.planning/codebase/CONCERNS.md` — bare exception handler inventory, module-level global state in A2A executor documented
- Prior research: `.planning/research/STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `SUMMARY.md` — HIGH confidence (all based on direct codebase inspection)

### Secondary (MEDIUM confidence)

- Training knowledge: ts-morph `ClassDeclaration.getBaseClass()`, `getExtends()`, `getMethod()`, `getProperties()` APIs — stable since ts-morph v10; consistent with usage patterns visible in `ast.ts`
- Training knowledge: React `Component` and `PureComponent` as the two base class names for class components — React 18/19 stable

### Tertiary (LOW confidence)

None identified. All claims in this research are grounded in direct codebase inspection or stable library APIs.

---

## Metadata

**Confidence breakdown:**
- INFRA-01 (exception narrowing): HIGH — exact file locations and line numbers confirmed by grep; `SubprocessError` type already exists and is used correctly in adjacent code
- INFRA-02 (state isolation): HIGH — module-level dict and `__init__` fallback confirmed by direct reading; one open question (singleton vs per-request instantiation) documented
- CLASS-01 (bridge handler): HIGH for the extension pattern; MEDIUM for the exact React class detection logic (ts-morph API behaviour verified only through existing usage in `ast.ts`, not against ts-morph v25 docs)
- Models (`migration/models.py`): HIGH — `BaseModel` pattern is project-wide and well-established

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable stack; no external dependencies)
