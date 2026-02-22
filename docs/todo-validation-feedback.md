# Todo: Validation + feedback refinement pattern

**Idea:** We can validate planner/agent outputs with code and feed errors back to the LLM for a small, surgical fix instead of failing the whole run.

**Examples of what we can check in code:**

- **Schedule / remove_node:** Before running `remove_node`, resolve `symbol_name` against the file (e.g. list declarations in the TS bridge). If not found, we have a concrete error: “Declaration ‘X’ not found. In this file the declarations are: A, B, C.” That can be sent back to the planner (or a small “fix-up” LLM call) to correct just that op (e.g. change `symbol_name` to one of A/B/C or drop the op).
- **Paths / move_file:** Validate that source/target paths exist or are valid before execution; on failure, return a short message the model can use to fix the schedule.
- **RefactorSchedule shape:** We already validate with Pydantic; we could add semantic checks (e.g. “operations reference file X but X is not in the codebase structure”) and feed that back.

**Pattern:** Run cheap validation (no heavy execution), collect a small list of issues, then either:

1. **Feedback refinement:** One short LLM round with “Here’s the schedule; validation failed: [issues]. Suggest minimal edits to the schedule (only the affected ops).” and parse the patch, or  
2. **Inline in executor:** Before executing an op, validate its args; on failure, return a structured error and (future) allow a refinement step.

**Why “surgical edit”:** Avoid re-planning the whole schedule. Only fix the invalid parts (wrong symbol name, bad path, etc.) using code-verified feedback so the model gets high-signal, low-noise correction.

**Next steps (when we pick this up):**

- Add a validation pass over a `RefactorSchedule` (e.g. “all symbol_names resolvable”, “all file_paths present”) before execution.
- Define a small “schedule patch” format or a single LLM prompt that takes schedule + validation errors and outputs minimal corrections.
- Optionally: TS bridge (or executor) returns “candidates” when a declaration is not found (e.g. “Did you mean: entityManagerProvider, userProviderForQuote?”) so the feedback is directly actionable.
