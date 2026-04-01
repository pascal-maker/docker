---
phase: 01-foundation
plan: 02
subsystem: migration
tags: [react, ts-morph, typescript, pydantic, class-components, ast]

# Dependency graph
requires: []
provides:
  - handleListReactClassComponents TypeScript bridge handler in react.ts
  - ComponentInfo and ClassComponentList Pydantic models in migration/models.py
  - list_react_class_components method on TsMorphProjectEngine
  - migration Python package with structured logger
affects: [02-classifier, 03-executor, migration-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ts-morph bridge handler registered in index.ts dispatch table
    - React class detection via baseTextRoot stripping (handles short import forms without type resolution)
    - Python wrapper calling bridge via self._call() returning list[ComponentInfo]
    - Package logger pattern: migration/logger.py exports get_logger("refactor_agent.migration")

key-files:
  created:
    - packages/ts-morph-bridge/src/react.ts
    - apps/backend/src/refactor_agent/migration/__init__.py
    - apps/backend/src/refactor_agent/migration/logger.py
    - apps/backend/src/refactor_agent/migration/models.py
    - apps/backend/tests/test_migration/__init__.py
    - apps/backend/tests/test_migration/test_models.py
  modified:
    - packages/ts-morph-bridge/src/index.ts
    - apps/backend/src/refactor_agent/engine/typescript/ts_morph_engine.py
    - apps/backend/tests/test_engine/test_ts_morph_project_engine.py

key-decisions:
  - "baseTextRoot detection (stripping type params) added to handle Component/PureComponent short-import forms when react types are not resolvable in tmp workspaces"
  - "ComponentInfo import uses noqa: TC001 annotation — runtime Pydantic model construction requires import outside TYPE_CHECKING block"

patterns-established:
  - "React class detection: check both getBaseClass().getName() (type-resolved) and baseTextRoot from getExpression().getText() (syntactic) to handle both installed and uninstalled @types/react workspaces"
  - "Bridge handler registration: new handlers added to index.ts dispatch table in same task as handler file creation (atomic)"

requirements-completed: [CLASS-01]

# Metrics
duration: 6min
completed: 2026-04-01
---

# Phase 01 Plan 02: React Class Component Detection Summary

**React class component scanner: ts-morph bridge handler + Python wrapper returning typed `list[ComponentInfo]`, detecting React.Component, Component, and PureComponent across all source files**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-01T22:29:23Z
- **Completed:** 2026-04-01T22:35:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Created `migration` Python package with strict-typed `ComponentInfo` and `ClassComponentList` Pydantic models (no `Any`, no `dict` in signatures)
- Created `packages/ts-morph-bridge/src/react.ts` bridge handler that scans all project source files and returns React class component entries
- Registered `list_react_class_components` in the ts-morph bridge dispatch table in `index.ts`
- Added `list_react_class_components` async method on `TsMorphProjectEngine` returning `list[ComponentInfo]`
- 10 tests passing: 5 model unit tests + 5 integration tests covering all detection paths

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration package models, bridge handler, and dispatch registration** - `591976a` (feat)
2. **Task 2: Python wrapper on TsMorphProjectEngine with integration tests** - `42f1aab` (feat)

_Note: TDD tasks had RED (import error / AttributeError) confirmed before GREEN implementation._

## Files Created/Modified

- `packages/ts-morph-bridge/src/react.ts` - Bridge handler; scans project source files for React class components
- `packages/ts-morph-bridge/src/index.ts` - Added import and dispatch table entry for list_react_class_components
- `apps/backend/src/refactor_agent/migration/__init__.py` - Package init (empty)
- `apps/backend/src/refactor_agent/migration/logger.py` - Package logger via get_logger("refactor_agent.migration")
- `apps/backend/src/refactor_agent/migration/models.py` - ComponentInfo and ClassComponentList Pydantic models
- `apps/backend/src/refactor_agent/engine/typescript/ts_morph_engine.py` - Added list_react_class_components method
- `apps/backend/tests/test_migration/__init__.py` - Test package init (empty)
- `apps/backend/tests/test_migration/test_models.py` - 5 model validation tests
- `apps/backend/tests/test_engine/test_ts_morph_project_engine.py` - 5 integration tests for react detection

## Decisions Made

- **baseTextRoot detection strategy:** `getBaseClass()?.getName()` relies on type resolution; without `@types/react` installed in the test workspace, it returns `undefined` for short-import forms. Added `baseTextRoot` (strip `<...>` from `getExpression().getText()`) to detect `"Component"` and `"PureComponent"` syntactically without needing type resolution. This makes the scanner robust against workspaces that don't have react types installed.
- **ComponentInfo import placement:** Per CLAUDE.md, imports used only in type annotations go in `TYPE_CHECKING` blocks. However, `ComponentInfo` is used at runtime for Pydantic model construction (`ComponentInfo(...)`), so it is placed outside `TYPE_CHECKING` with `# noqa: TC001` annotation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed React short-import form detection failure**
- **Found during:** Task 2 (integration test for ShortForm extends Component)
- **Issue:** `getBaseClass()?.getName()` returns `undefined` for `extends Component` when `@types/react` is not installed in the test workspace (tmp dir). `REACT_BASE_CLASSES.has(baseName)` check with empty string always fails, so short-import components were not detected.
- **Fix:** Added `baseTextRoot = baseText.replace(/<.*$/, "").trim()` and `REACT_BASE_CLASSES.has(baseTextRoot)` check, making detection syntactic (not dependent on type resolution).
- **Files modified:** `packages/ts-morph-bridge/src/react.ts`
- **Verification:** All 5 integration tests pass, TypeScript compiles cleanly
- **Committed in:** `42f1aab` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Essential for correctness — the short-import form detection was a core requirement (CLASS-01 truths). No scope creep.

## Issues Encountered

- `make ts-typecheck` fails at the repo level due to an NX project graph conflict between worktree agent directories (`MultipleProjectsWithSameNameError`). This is a parallel-agent worktree infrastructure issue, not caused by this plan's changes. Verified TypeScript correctness by running `pnpm exec tsc --noEmit` directly in `packages/ts-morph-bridge`.

## Known Stubs

None — all detection logic is wired end-to-end. `list_react_class_components()` calls the bridge and returns real data from the project source files.

## Next Phase Readiness

- `list_react_class_components()` is callable from Python and returns typed `list[ComponentInfo]`
- Phase 2 (classifier) can import `ComponentInfo` and `ClassComponentList` from `refactor_agent.migration.models`
- The `migration` package is initialized with a logger ready for future modules
- Bridge dispatch table is open for additional react-related handlers (e.g., transformation handlers in Phase 3)

---
*Phase: 01-foundation*
*Completed: 2026-04-01*
