---
title: `Explore: LLM-generated codemods for complex cross-codebase transformations`
labels: `enhancement`, `exploration`, `future`
---

## Context

The current refactoring agent uses **predefined structural operations** (rename, move symbol, remove node, etc.) that the LLM selects via tool calls. This works well for common refactors but hits a ceiling for complex, pattern-based migrations — e.g., migrating from `requests` to `httpx`, upgrading a framework API, or applying a custom org-wide coding convention across hundreds of files.

An alternative (or complementary) approach: have the LLM **generate a codemod program** on the fly, then execute it deterministically across the codebase.

## The idea

Instead of:
```
LLM → edit file 1 → edit file 2 → ... → edit file N
```

Do:
```
LLM → generate codemod → apply codemod to all files → validate
```

This is what teams like React and Next.js do for migrations (e.g., [react-codemod](https://github.com/reactjs/react-codemod)), except they write codemods by hand. LLMs could generate them dynamically for arbitrary transformations.

Related pattern: Anthropic and others have observed that for large-scale changes, having an LLM generate a *program* that performs the work outperforms having the LLM perform the work directly — the generated program is consistent, reviewable, and deterministic.

## Why this is interesting

- **Consistency**: a codemod applies the exact same transformation everywhere. File-by-file LLM editing drifts across large codebases.
- **Scale**: one LLM call to produce the codemod vs. N calls for N files. Orders of magnitude more efficient for broad migrations.
- **Reviewability**: review a 50-line transform instead of a 2000-line diff. The codemod *is* the intent.
- **Determinism**: once generated, re-running the codemod produces identical results.
- **Composability**: codemods can be chained, versioned, and shared.

## Possible implementation paths

### TypeScript (ts-morph / jscodeshift)

The existing ts-morph bridge already loads a project-level AST. A new `apply_transform` handler could accept a generated ts-morph script (or jscodeshift transform) and `eval` it against the loaded project:

```typescript
// LLM generates something like:
export default function transform(project: Project) {
  for (const sourceFile of project.getSourceFiles()) {
    // find all `requests.get(...)` calls, replace with `httpx.get(...)`
    // update imports, handle async conversion, etc.
  }
}
```

### Python (LibCST)

[LibCST](https://github.com/Instagram/LibCST) provides a CST (Concrete Syntax Tree) that preserves formatting, plus a codemod framework. The LLM would generate a `CSTTransformer` subclass:

```python
# LLM generates something like:
class MigrateRequestsToHttpx(cst.CSTTransformer):
    def leave_Call(self, original, updated):
        # transform requests.get() → httpx.get()
        ...
```

Reference: [Refactoring a Python Codebase with LibCST](https://engineering.instawork.com/refactoring-a-python-codebase-with-libcst-fc645ecc1f09)

## Key challenges to explore

1. **Correctness of generated codemods** — CST visitors are structurally complex. Edge cases (e.g., `requests.get()` vs `session.get()` vs a local `get()`) are easy to miss. Needs a generate → test → refine loop.
2. **Sandboxing** — executing LLM-generated code requires sandboxing. Evaluate in a subprocess with no filesystem write access; only return the transformed AST.
3. **Validation loop** — after applying the codemod, run type-checking / diagnostics to catch regressions, then feed errors back to the LLM to refine the transform. This iterative loop is the hard part.
4. **Scope detection** — deciding *when* to use a codemod vs. a simple tool call. For renaming a single function, a predefined tool is better. For migrating a library across 200 files, a codemod is better. The agent needs heuristics (or the user states intent).
5. **Partial application & dry-run** — apply to a subset of files first, validate, then expand. Similar to how manual codemod workflows work.

## Relationship to current work

This would layer on top of the existing architecture, not replace it:

- **Tier 1** (current plan): predefined refactoring ops via tool calls — rename, move, remove, etc.
- **Tier 2** (this issue): LLM-generated codemods for complex/custom transformations.

The ts-morph bridge and project-level AST loading being built now would serve as the runtime for generated codemods.

## Prior art & references

- [react-codemod](https://github.com/reactjs/react-codemod) — hand-written React migration codemods
- [jscodeshift](https://github.com/facebook/jscodeshift) — Facebook's JS/TS codemod toolkit
- [LibCST codemods](https://libcst.readthedocs.io/en/latest/codemods_tutorial.html) — Instagram's Python CST codemod framework
- [Bowler](https://pybowler.io/) — safe Python refactoring built on LibCST
- [putout](https://github.com/coderaiser/putout) — pluggable JS/TS linter & codemod tool
- [Refactoring a Python Codebase with LibCST](https://engineering.instawork.com/refactoring-a-python-codebase-with-libcst-fc645ecc1f09)
