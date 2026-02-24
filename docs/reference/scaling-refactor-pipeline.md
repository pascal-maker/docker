# Scaling the refactor pipeline: findings and next steps

This doc summarizes observed behavior and failure modes when running the planning + execution pipeline on larger codebases, and outlines directions for prompt engineering and agentic patterns so the pipeline scales without fitting into a single PR.

## Trace and run context

### Trace `f95cc283acf508a65f9c3cac1c8e8820` (Langfuse)

- **Input:** "Refactor this codebase to a vertical slice structure."
- **Output:** Plan described as **66 operations**, target layout `Shared/` + `Feature/Quote/` and `Feature/User/` (vertical slices with Shared/ per feature), ApiGateway and Provider unchanged but imports updated.
- **Timing:** chat-agent ~162s total; refactor-planner ~60s; schedule-executor ~42s. All observations `level: DEFAULT`, no `statusMessage` errors.
- **Planner:** Single planner run, `max_tokens: 32768`; plan produced and schedule executed.
- **Repo outcome:** Partial. `Shared/` created and used (e.g. `Shared/Database` in `app.module.ts`), `Feature/Quote` and `Feature/User` used in app, but legacy dirs (Module, Common, Database, Provider, ApiGateway, etc.) remained. No `Slice/`; no full cleanup of legacy paths.

So this trace shows a **successful** run from the pipeline’s perspective (no exception, executor finished), but the **resulting repo is hybrid**: new structure partially adopted, legacy structure not removed, and target layout (e.g. “only Shared + Slice”) not fully reached.

### Other observed failure modes (from earlier runs / terminal)

1. **APITimeoutError** – Planner HTTP requests timing out (originally 60s). Fixed by increasing `PLANNER_REQUEST_TIMEOUT` to 300s for large-context runs.
2. **PlannerLimitExceededError** – Planner hitting `MAX_PLANNER_TOOL_CALLS_PER_RUN` (22) or `MAX_PLANNER_LLM_ROUNDS` (7) unpredictably. Addressed by budget awareness (e.g. `get_planning_budget` tool) and graceful degradation (return partial plan when possible).
3. **move_file "Target file already exists"** – Executor failed and stopped when a move targeted an existing path (e.g. re-run or duplicate op). Fixed by making that case a no-op in the TS bridge.
4. **Executor stop-on-first-failure** – If any op fails (or threw before the move_file no-op), the executor returns immediately and does not run the rest of the schedule. So one bad op leaves the repo in a half-migrated state.

---

## Findings

### 1. Plan vs execution gap

- The **plan** (66 ops in the trace) describes a clear target (e.g. Shared + Feature layout, imports updated).
- **Execution** either runs to completion with a different effective target (e.g. Feature instead of Slice, no removal of legacy dirs) or stops early on first failure. There is no guarantee that the executed ops exactly match the described end state (e.g. legacy removal, barrel updates, diagnostics).
- So “success” in the trace can still mean a **partial or inconsistent** repo relative to the intended design.

### 2. Scaling limits

- **Codebase size:** Injected codebase structure is capped at `MAX_CODEBASE_STRUCTURE_CHARS` (150k). Larger codebases get a truncated view; the planner may miss files or boundaries, leading to incomplete or wrong plans.
- **Plan size:** Schedules of 60–90 ops are common. Planner budget (22 tool calls, 7 LLM rounds) and token/time limits make it hard to both explore the codebase and output a single, correct, large schedule in one shot.
- **Single-shot execution:** The executor runs one linear (topologically ordered) list of ops. There is no checkpointing, no “run phase 1 then re-plan,” and no automatic retry or alternative path on failure. So scaling is limited by “one plan, one run.”

### 3. Resilience

- **All-or-nothing:** One failed op (before the move_file no-op fix) aborted the whole schedule and left the repo in a partial state. Even with that fix, other op types can still fail and stop the run.
- **No iterative refinement:** When the run is partial, there is no built-in “continue from here” or “re-plan given current repo state.” Manual reset (e.g. `make reset-playground`) and re-run is the current approach.

### 4. Prompt and plan consistency

- Different runs with the same user prompt (“vertical slice structure”) can produce different target layouts (e.g. **Feature/** vs **Slice/**) and different op counts (66 vs 87). That suggests the planner’s output is sensitive to context (codebase snapshot, tool usage, and remaining budget), not a deterministic function of the prompt alone. Good prompt engineering and constraints (e.g. canonical folder names, phase ordering) could reduce variance and align plans with what the executor and codebase can handle.

---

## Possible next steps (for future work)

These are directions, not a single PR. Prioritization and scoping can be done separately.

### Prompt engineering

- **Canonical target schema:** Define a single, documented target layout (e.g. `Shared/` + `Slice/<Feature>/`) and reference it in the refactor-planner prompt and operation-types docs so the model prefers consistent structure and naming.
- **Phasing in the prompt:** Encourage the planner to emit plans in explicit phases (e.g. “Phase 1: move to Shared; Phase 2: move to Slice; Phase 3: rewire app.module; Phase 4: remove legacy”) so that future support for phase-by-phase execution or re-planning is easier.
- **Scope and size:** Add instructions or tooling so the planner stays within budget (e.g. “prefer fewer, high-impact moves” or “output a minimal viable plan first”). Optionally surface codebase size or structure size in the prompt so the model can adapt (e.g. suggest smaller scope on large codebases).

### Agentic patterns

- **Multi-phase execution:** Run a subset of ops (e.g. “Phase 1” only), then re-run the planner with the current repo state and a prompt like “Continue from current state to complete the vertical slice refactor.” The planner could then emit a follow-up schedule that assumes Phase 1 is already done.
- **Iterative refinement:** When the executor hits a failure or when the run is marked partial (e.g. from graceful degradation), persist the current schedule and repo state and offer “Refine plan” or “Retry from here” that re-invokes the planner with the partial outcome as context.
- **Chunked planning:** For very large codebases, split by domain or directory: e.g. “Plan refactor for `src/Module/Quote` only,” then “Plan for `src/Module/User`,” then a final “Wire app.module and remove legacy” step. This keeps each plan within budget and allows incremental execution.

### Executor and pipeline resilience

- **Continue-on-error mode:** Optional flag to record failed ops but continue running the rest of the schedule, then report which ops failed so the user or a follow-up agent can fix or re-plan.
- **Checkpointing:** Persist “schedule + index of last successful op” so a run can be resumed after a crash or manual fix, instead of re-running from scratch.
- **Validation and rollback:** After execution, run a quick validation (e.g. TypeScript build or lint). On failure, optionally restore from a pre-execution snapshot (e.g. git stash or a copy of the playground) so the user always has a clean reset path.

### Observability and tuning

- **Trace analysis:** Use Langfuse (or similar) to compare traces where the repo ended in a good vs partial state: prompt version, codebase size, op count, tool-call distribution, and failure points. Use that to tune limits, prompts, and where to add agentic loops.
- **Budget and limits:** Revisit `MAX_PLANNER_TOOL_CALLS_PER_RUN`, `MAX_PLANNER_LLM_ROUNDS`, and `PLANNER_REQUEST_TIMEOUT` as codebases grow; consider making them configurable per run or per workspace size.

---

## References

- [Testing (refactor schedule, playgrounds)](../contributing/testing/README.md) – manual and automated testing of the plan/execute flow.
- [Refactor schedule (data model, executor)](../contributing/refactor-schedule/README.md) – schedule format and executor contract.
- [Chat UI](../clients/chat-ui.md) – modes (Plan / Ask / Auto) and how the schedule is produced and executed.
- `scripts/dev/reset-playground.sh` / `make reset-playground` – reset the NestJS playground to a clean state after partial runs.
