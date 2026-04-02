---
phase: 2
slug: classifier-and-tsc-gate
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-asyncio (asyncio_mode = auto) |
| **Config file** | `apps/backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd /Users/pascal-maker/refactor-agent/apps/backend && python -m pytest tests/test_migration/ -x -q` |
| **Full suite command** | `cd /Users/pascal-maker/refactor-agent/apps/backend && python -m pytest -x -q` |
| **Estimated runtime** | ~15 seconds (quick), ~45 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd /Users/pascal-maker/refactor-agent/apps/backend && python -m pytest tests/test_migration/ -x -q`
- **After every plan wave:** Run `cd /Users/pascal-maker/refactor-agent/apps/backend && python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite green + `make ts-typecheck` (bridge extension) before verify
- **Max feedback latency:** ~45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-xx-01 | TBD | 1 | CLASS-02, CLASS-03, CLASS-04, CLASS-05 | unit | `cd apps/backend && python -m pytest tests/test_migration/test_classifier.py -x -q` | Wave 0 | ⬜ pending |
| 02-xx-02 | TBD | 1 | TSC-01, TSC-02, TSC-03, TSC-04, TSC-05 | unit | `cd apps/backend && python -m pytest tests/test_migration/test_tsc_gate.py -x -q` | Wave 0 | ⬜ pending |
| 02-xx-03 | TBD | 1 | CLASS-02 bridge ext | ts-typecheck | `cd /Users/pascal-maker/refactor-agent && make ts-typecheck` | New files | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/backend/tests/test_migration/test_classifier.py` — stubs for CLASS-02 through CLASS-05
- [ ] `apps/backend/tests/test_migration/test_tsc_gate.py` — stubs for TSC-01 through TSC-05
- [ ] `apps/backend/src/refactor_agent/migration/classifier.py` — new module stub
- [ ] `apps/backend/src/refactor_agent/migration/tsc_gate.py` — new module stub
- [ ] Extended `ComponentInfo` model fields: `has_force_update`, `instance_field_count`, `extends_pure_component`
- [ ] New models: `MigrationTier`, `ComponentClassification`, `MigrationScope`, `TscSnapshot`, `TscGateResult`
- [ ] Extended `react.ts` bridge handler (if bridge extension approach for `forceUpdate`/instance fields)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Classifier AI rationale is meaningful (not boilerplate) | CLASS-05 | LLM output quality is subjective | Run classifier on a real workspace with mixed component types; inspect rationale strings in result |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
