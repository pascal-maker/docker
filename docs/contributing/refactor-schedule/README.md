---
title: Refactor schedule
context: |
  Multi-step refactors (e.g. enforce frontend/backend boundary, DDD → vertical slice)
  need many operations. Agent emits a schedule; scheduler optimizes and executes.
  Planning trusts LLM ordering first; optimization (DAG, waves, parallel) comes last.
  Structural rewrites only — ts-morph manifold. See [ideas/vision.md](../../roadmap/ideas/vision.md) for algebraic
  framing (commutativity, confluence, manifold boundary).
---

# Refactor schedule

**Schedule** = unordered set of refactor operations. Agent outputs intent; scheduler derives execution order from static analysis (affected spans, conflict graph). Not a "plan" with human phases — waves fall out of the DAG.

## Pipeline

```
Agent (tools: list_files, skeleton, find_references)
  → RefactorSchedule (operations + optional dependsOn)
  → Validate (files/symbols exist, no cycles)
  → Enrich (ts-morph: affected spans per op)     ← optimization only
  → DAG → waves → Execute (reparse between waves)
```

**MVP:** Skip enrichment. Trust LLM ordering; executor runs steps in topo order of `dependsOn`. Add DAG/wave optimization later.

## Manifold

**In scope:** Rename, move symbol, move file, remove node, organize imports. If a junior can do it with find-references + IDE move/rename across many files, we can automate it.

**Out of scope:** Cross-library migration (ORM→ORM), API shape changes, logic refactors. Requires semantic rewriting, not structural.

## Data model

- `RefactorSchedule`: `goal`, `operations: list[RefactorOperation]`
- Operations: discriminated union — `move_symbol`, `move_file`, `rename`, `remove_node`, `organize_imports`, `create_file`
- Each op: ids, paths, symbol locations (file + position for compiler grounding), optional `rationale`, optional `dependsOn` (MVP: scheduler uses it; later: scheduler recomputes from spans)

## Steps to PoC (logical order)

1. **Fixture** — Boundary-violation playground (backend-in-frontend, shared types misplaced). **Done:** `playground/python/` and `playground/typescript/` use a DDD layout with intentional violations (see playground READMEs).
2. **Models** — Pydantic `RefactorSchedule` + operation variants; hand-written JSON fixture parses. **Done:** `src/refactor_agent/schedule/models.py`; fixture `tests/fixtures/refactor_schedule.json`.
3. **Executor** — Naive: topo sort by `dependsOn`, dispatch each op to ProjectEngine. No rollback yet. **Done:** `src/refactor_agent/schedule/executor.py` (TypeScript only in PoC).
4. **Planner agent** — Structured output `RefactorSchedule`, read-only tools. **Done:** `src/refactor_agent/schedule/planner.py`.
5. **Wire** — Chat agent tool calls planner, shows schedule; Plan mode = display only, Auto = executor runs. **Done:** Orchestrator tool `create_refactor_schedule`; Dev UI applies mode (Plan / Auto / Ask) after run.
6. **Validate** — Pre-execution: paths/symbols resolve, valid IDs, no cycles. Fail fast. **Done:** in executor.
7. **Checkpoint** — Snapshot before run; rollback on failure or bad diagnostics.
8. **Diagnostics** — Post-exec `get_diagnostics()`; optional repair loop (planner again with errors).
9. **Optimization** — Enrich (spans per op), conflict graph, waves, parallel within wave.

Steps 1–6 = implemented. 7–9 = future.
