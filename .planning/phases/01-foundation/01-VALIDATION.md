---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-asyncio (asyncio_mode = auto) |
| **Config file** | `apps/backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd apps/backend && python -m pytest tests/test_a2a/ tests/test_engine/ -x -q` |
| **Full suite command** | `cd apps/backend && python -m pytest -x -q` |
| **Estimated runtime** | ~30 seconds (quick), ~90 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd apps/backend && python -m pytest tests/test_a2a/ tests/test_engine/ -x -q`
- **After every plan wave:** Run `cd apps/backend && python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite green + `make ts-typecheck` passes
- **Max feedback latency:** ~90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-xx-01 | TBD | 1 | INFRA-01 | unit | `cd apps/backend && python -m pytest tests/test_orchestrator/ -x -q` | New test needed | ⬜ pending |
| 1-xx-02 | TBD | 1 | INFRA-01 | unit | `cd apps/backend && python -m pytest tests/test_orchestrator/ -x -q` | New test needed | ⬜ pending |
| 1-xx-03 | TBD | 1 | INFRA-02 | unit | `cd apps/backend && python -m pytest tests/test_a2a/ -x -q` | `test_executor.py` exists; new test case | ⬜ pending |
| 1-xx-04 | TBD | 2 | CLASS-01 | integration | `cd apps/backend && python -m pytest tests/test_engine/test_ts_morph_project_engine.py -x -q` | Exists; new test case | ⬜ pending |
| 1-xx-05 | TBD | 2 | CLASS-01 | unit | `cd apps/backend && python -m pytest tests/test_engine/test_ts_morph_project_engine.py -x -q` | Exists; new test case | ⬜ pending |
| 1-xx-06 | TBD | 2 | CLASS-01 | unit | `cd apps/backend && python -m pytest tests/ -k "migration" -x -q` | New test file needed | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_orchestrator/test_exception_narrowing.py` — stubs for INFRA-01 (narrowed exception handlers)
- [ ] New test case in `tests/test_a2a/test_executor.py` — INFRA-02 (instance isolation)
- [ ] New test cases in `tests/test_engine/test_ts_morph_project_engine.py` — CLASS-01 (component detection)
- [ ] `apps/backend/src/refactor_agent/migration/__init__.py`, `migration/logger.py`, `migration/models.py` — `ComponentInfo` and `ClassComponentList` models needed before tests can import them

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TypeScript bridge handler returns correct JSON for a real workspace with mixed React class/function components | CLASS-01 | Requires a real TypeScript workspace on disk; mocking defeats the point | Run `node packages/ts-morph-bridge/dist/index.js` with a JSON command payload pointing to a fixture workspace; verify response shape |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
