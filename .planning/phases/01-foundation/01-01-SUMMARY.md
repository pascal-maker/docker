---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [exception-handling, subprocess, a2a, pydantic-ai, state-isolation]

# Dependency graph
requires: []
provides:
  - Narrowed exception handlers in orchestrator subprocess path (SubprocessError, KeyError only)
  - Per-instance isolated state in ASTRefactorAgentExecutor (no shared module-level dict)
affects: [phase-03-executor, phase-04-pr-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "except (SubprocessError, KeyError) for engine subprocess path — TypeError propagates as programmer error"
    - "Per-instance dict{} fallback in executor __init__ instead of module-level shared state"

key-files:
  created:
    - apps/backend/tests/test_orchestrator/test_exception_narrowing.py
  modified:
    - apps/backend/src/refactor_agent/orchestrator/agent.py
    - apps/backend/src/refactor_agent/a2a/executor.py
    - apps/backend/tests/test_a2a/test_executor.py

key-decisions:
  - "Use (SubprocessError, KeyError) not (SubprocessError, ValueError) — KeyError verified from EngineRegistry.create source, not ValueError as RESEARCH.md inconsistently stated"
  - "Delete module-level _orchestrator_state entirely rather than leave it unused — nothing else referenced it"

patterns-established:
  - "Engine subprocess path: catch only (SubprocessError, KeyError), let TypeError propagate as unhandled programmer error"
  - "A2A executor state: always use per-instance {} as fallback, never module-level shared dict"

requirements-completed: [INFRA-01, INFRA-02]

# Metrics
duration: 5min
completed: 2026-04-01
---

# Phase 01 Plan 01: Infrastructure Prerequisites Summary

**Narrowed three bare `except Exception` handlers in orchestrator to `(SubprocessError, KeyError)` and replaced module-level shared state in `ASTRefactorAgentExecutor` with per-instance isolation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-01T22:29:02Z
- **Completed:** 2026-04-01T22:34:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Lines 156, 183, and 359 in `agent.py` now use `except (SubprocessError, KeyError)` — `TypeError` (programming mistake) propagates uncaught as intended
- `ASTRefactorAgentExecutor.__init__` now uses a fresh `{}` dict per instance; the module-level `_orchestrator_state` dict is deleted entirely
- 9 new tests in `test_exception_narrowing.py` covering all three caught/propagated paths
- 2 new tests in `test_executor.py` confirming state isolation and injected-store behavior
- All 23 tests across `test_orchestrator/` and `test_a2a/` pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Narrow bare exception handlers in orchestrator/agent.py (INFRA-01)** - `aa4a3b3` (feat)
2. **Task 2: Eliminate module-level shared state in A2A executor (INFRA-02)** - `b8702a1` (feat)

_Note: Both tasks used TDD — tests written first (RED), production code fixed to pass (GREEN)._

## Files Created/Modified

- `apps/backend/src/refactor_agent/orchestrator/agent.py` - Three `except Exception` handlers narrowed to `(SubprocessError, KeyError)`
- `apps/backend/src/refactor_agent/a2a/executor.py` - Module-level `_orchestrator_state` deleted; `__init__` fallback changed to `{}`
- `apps/backend/tests/test_orchestrator/test_exception_narrowing.py` - New: 9 tests for INFRA-01 (SubprocessError caught, KeyError caught, TypeError propagates — for all three handlers)
- `apps/backend/tests/test_a2a/test_executor.py` - Added `test_executor_instances_have_isolated_state` and `test_executor_uses_injected_state_store`

## Decisions Made

- **`(SubprocessError, KeyError)` not `(SubprocessError, ValueError)`:** RESEARCH.md inconsistently referenced `ValueError` but `EngineRegistry.create()` source (line 45) raises `KeyError` for unsupported languages. Verified from source and used `KeyError`.
- **Delete `_orchestrator_state` entirely:** Only referenced in `executor.py` itself. Removing it eliminates the risk of future accidental re-use and keeps the fix clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pydantic_ai Agent tool accessor API differs from plan's assumed `_function_tools`**
- **Found during:** Task 1 (show_file_skeleton test RED phase)
- **Issue:** Plan suggested accessing `agent._function_tools` but pydantic_ai exposes `agent._function_toolset.tools` (dict keyed by name, values are `Tool` objects with `.function` attribute)
- **Fix:** Used `getattr(agent, "_function_toolset").tools["show_file_skeleton"].function` with `getattr` per CLAUDE.md guidance for untyped third-party SDK internals
- **Files modified:** `tests/test_orchestrator/test_exception_narrowing.py`
- **Verification:** All 9 tests pass
- **Committed in:** `aa4a3b3` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking, wrong private API name in plan)
**Impact on plan:** Minor — only affected test helper, not production code. No scope creep.

## Issues Encountered

None beyond the deviation documented above.

## Next Phase Readiness

- INFRA-01 and INFRA-02 are complete — the orchestrator subprocess path no longer silently swallows `TypeError` programming mistakes
- Per-instance state isolation in the A2A executor is a prerequisite for the transactional migration executor in Phase 3
- No blockers for Plan 02

---
*Phase: 01-foundation*
*Completed: 2026-04-01*
