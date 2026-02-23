# Coding rules and guidelines

This document summarizes the repo’s coding rules, where they are intentionally relaxed or violated (and why), and the standards/resources they are based on.

**Canonical source:** [CLAUDE.md](../../CLAUDE.md) (root). Cursor uses the same via [.cursor/rules/coding-guidelines.mdc](../../.cursor/rules/coding-guidelines.mdc).  
**Audit:** [audit.md](audit.md).

---

## 1. Coding rules summed up in this repo

### General

- **Typing:** Strict typing everywhere; no untyped defs; no `Any` without justification.
- **Pre-commit:** Run `make check` (format-check, lint, typecheck, test) before every commit; all four must pass. CI runs them as separate jobs.
- **Formatting:** Line length 88 (ruff). Double quotes, spaces. No relative imports; absolute only.
- **Docstrings:** Google-style on public functions and classes; skip module/package/`__init__`.
- **Suppressions:** Never suppress linter/type-checker without a short comment explaining why.
- **Complexity:** Max function complexity 10 (mccabe), max statements 40, max args 6.

### Types and APIs

- **Python:** ≥ 3.12. Use modern syntax: `X | Y`, `list[...]`, `dict[...]` (not `List`/`Dict`/`Tuple`).
- **Signatures:** No `dict`/`Dict`/`TypedDict` in function parameters or return types; use Pydantic (`BaseModel` or `RootModel`) instead. One documented exception: third-party callbacks that require dict in/out (e.g. monkey-patches).
- **Refinement:** Prefer type narrowing over `cast()` or `as Type`; avoid `cast` except for context managers or exception handling.
- **Pydantic:** Use `ConfigDict(extra="allow")` only when needed for open-ended payloads; document why.
- **Attribute access:** Prefer strict typing over `getattr`/`hasattr`/`setattr`/`delattr`; use model attributes. Use `getattr`/`hasattr` only on untyped third-party objects, with a short comment.

### Imports

- Annotation-only imports go in `TYPE_CHECKING` blocks (with `from __future__ import annotations`). Exception: runtime-needed imports for Pydantic resolution → `# noqa: TC001` and comment.
- Third-party used only in annotations → `TYPE_CHECKING` unless needed at runtime (e.g. TypedDict without `from __future__ import annotations`) → `# noqa: TC002` and comment.

### Logging

- **Module loggers:** Per package that needs logging, define `logger.py` (not `logging.py`), export `logger`, use `refactor_agent._log_config.get_logger("refactor_agent.<package>")`.
- **Setup:** Call `configure_logging()` once at app startup. JSON to stderr; Sentry for errors when `SENTRY_DSN` is set.
- **No bare output:** No `print()` in `src/` or `tests/`. Scripts may use `print()`. UI uses module logger only; frontend errors via Sentry or backend logging.

### Testing

- pytest with `asyncio_mode = auto`. Use PydanticAI’s `TestModel` for agent tests; never call a real LLM. Warnings are errors. Tests may access private members (SLF001 ignored for tests).

### Infrastructure and data

- For vector DBs (e.g. Qdrant): push logic into the DB; do not reimplement similarity/filtering in application code.

### CI and tooling

- Format, lint, typecheck, and test are separate pipeline jobs. Per-file lint ignores only where framework or convention requires it; prefer fixing code.
- **Package manager (JS/TS):** Use **pnpm only**; no npm. The repo is a **pnpm workspace**: a single root `pnpm-lock.yaml` and `pnpm-workspace.yaml` list the TS packages (dashboard-ui, bridge, vscode-extension). Run `pnpm install` at repo root (or `make ts-install`) to install all TS deps; CI uses one install and caches the lockfile.
- **TypeScript (except playground):** All TypeScript code follows **analogous** coding guidelines and checks to Python: format (Prettier), lint (ESLint), typecheck (tsc). These run **locally** (via `make ts-format-check`, `make ts-lint`, `make ts-typecheck` or per-package `pnpm run format-check` / `lint` / `typecheck`) and **in CI** as separate jobs (`ts-format-check`, `ts-lint`, `ts-typecheck`). Packages:
  - **dashboard-ui/** (React SPA): `format`, `format-check`, `lint`, `typecheck`. See [dashboard.md](../dashboard.md).
  - **src/refactor_agent/engine/typescript/bridge/** (ts-morph JSON-RPC bridge): `format`, `format-check`, `lint`, `typecheck`. From repo root: `make ts-engine-check` runs typecheck only; `make ts-format-check`, `make ts-lint`, `make ts-typecheck` run checks across all TS packages.
  - **vscode-extension/** (VS Code extension): `format`, `format-check`, `lint`, `typecheck`; `vscode:prepublish` runs `pnpm run compile`.
  Playground and other one-off or demo TS are excluded from these checks.

---

## 2. Coding rules violated in the codebase and why

These are intentional exceptions or necessary relaxations; each is documented in code and/or in CLAUDE.md.

| Rule | Where | Why |
|------|--------|-----|
| **No dict in function signatures** | `_compat._patched(schema: dict[str, object]) -> dict[str, object]` | The patched function replaces pydantic_ai’s `check_object_json_schema`; the library passes and expects a dict. The callback contract is fixed by the third party. Comment in code and exception in CLAUDE.md. |
| **No getattr/hasattr** | A2A executor, sync server, observability/langfuse_config, schedule/planner, orchestrator/runner, ui/app, dashboard/auth, engine/python/libcst_engine, tests (A2A event) | Accessing **untyped third-party** objects (A2A RequestContext, websockets/Starlette, Langfuse prompt/observation, PydanticAI messages/run/span, Chainlit session, Starlette `app.state`, LibCST scope metadata). Each use has a short comment (e.g. “A2A RequestContext has no typed stub”). |
| **Suppressions without comment** | (None) | All `# noqa` and `# type: ignore` have a brief explanation (e.g. “signature required by Chainlit”, “lazy optional dep”, “used at runtime”). |
| **Per-file lint ignores** | `pyproject.toml` → `[tool.ruff.lint.per-file-ignores]` | **Tests:** assert (S101), fixtures (ARG), docstrings (D), etc., as per pytest/convention. **Scripts/playground:** relaxed docs and complexity for one-off tools. **Specific modules:** TC001/TC002/TC003 for runtime imports (Pydantic, FastAPI, A2A SDK); C901/PLR0911/PLR0912 where dispatch or language guards add branches; ASYNC240 for acceptable sync I/O; FBT001/FBT002 for boolean tool flags; N802 for LibCST callback names; etc. All documented in pyproject comments. |
| **Mypy overrides** | `pyproject.toml` → `[[tool.mypy.overrides]]` | `langfuse.*`, `pydantic_ai.*`, `anthropic.*`, `libcst.*`, `fastmcp.*`, `a2a.*`, `chainlit.*`: `ignore_missing_imports = true` (no stubs or incomplete stubs). `refactor_agent.ui.*`: `disallow_untyped_calls = false`, `disallow_untyped_defs = false` (Chainlit has no type stubs). |

No other deliberate violations; the rest of the codebase follows the rules above.

---

## 3. How to overcome these exceptions (optional)

Ways to reduce or remove the documented relaxations, based on current tooling and practice.

| Issue | Approach | Notes |
|-------|----------|--------|
| **Dict in function signatures** (`_compat._patched`) | **1.** Keep the documented exception — the callback contract is fixed by pydantic_ai; this is the allowed “third-party dictates dict” case. **2.** If pydantic_ai ever adds a typed hook (e.g. `(schema: SomeSchemaModel) -> SomeSchemaModel` or a Protocol), switch to that and remove the dict signature. **3.** You can still validate inside the patch: parse the incoming `dict` into a Pydantic model (e.g. a model for the JSON Schema subset you care about), do logic, then `.model_dump()` back to `dict` for the return — but the outer signature still has to be `dict` to satisfy the library. | No way to remove `dict` from the *signature* without an upstream API change. |
| **getattr / hasattr on untyped third-party** | **1.** **Protocols:** Define a `Protocol` with the attributes you need (e.g. `class RequestContextLike(Protocol): request_id: str; ...`) and type the third-party object as that protocol where you receive it; then use normal attribute access. **2.** **Stubs:** Add stubs (see “Mypy overrides” below) so the third-party types are known; then replace `getattr`/`hasattr` with direct attribute access. **3.** **Local stubs:** Use `mypy stubgen -p <package>` to generate draft `.pyi` files, put them in a `stubs/` dir, set `MYPYPATH=stubs`, and refine the stubs so your code can use typed attribute access. | Protocols give structural typing without changing the library; stubs (local or published) let the type checker see real attribute names. |
| **Suppressions without comment** | (None to fix.) Keep the rule: every `# noqa` and `# type: ignore` must have a brief comment. | — |
| **Per-file lint ignores** | **1.** **Reduce branches:** Refactor dispatch/language-guard code (e.g. split by language or use lookup tables) to bring complexity under limits so C901/PLR0911/PLR0912 can be removed. **2.** **Stubs:** Once third-party modules have stubs, you can drop TC001/TC002/TC003 for “runtime import” in those call sites. **3.** **Tests/scripts:** Test and script ignores are conventional (assert, fixtures, docstrings); keep them unless you change style (e.g. full docstrings in tests). | Prefer fixing code over adding ignores; use stubs to remove type-checking-related ignores. |
| **Mypy overrides** (`ignore_missing_imports`, `disallow_untyped_*`) | **1.** **Use or add stubs:** Check PyPI for `types-<package>` (e.g. `types-requests`). For packages with no stubs (e.g. `langfuse`, `pydantic_ai`, `chainlit`, `a2a`, `libcst`, `fastmcp`), either install a community stub package if one appears, or generate and maintain local stubs: `mypy stubgen -p langfuse` etc., save under `stubs/` (or a dedicated repo), and set `MYPYPATH` or install as a local stub package. **2.** **Contribute stubs:** Contribute `.pyi` to [typeshed](https://github.com/python/typeshed) or upstream so everyone benefits; then you can remove the override and optionally depend on `types-<package>`. **3.** **UI overrides:** For `refactor_agent.ui.*`, once Chainlit (or its ecosystem) has stubs, remove `disallow_untyped_calls` / `disallow_untyped_defs` overrides. | [PEP 561](https://peps.python.org/pep-0561/) and [mypy installed packages](https://mypy.readthedocs.io/en/stable/installed_packages.html): stubs can be inline, in the package, or in a separate `types-*` package. |

**References:** PEP 484 (type hints), PEP 561 (packaging type information), [mypy stubgen](https://mypy.readthedocs.io/en/stable/stubgen.html), [mypy creating stubs](https://github.com/python/mypy/wiki/Creating-Stubs-For-Python-Modules), [typing Protocol](https://mypy.readthedocs.io/en/stable/protocols.html).

---

## 4. Coding rules and guidelines resources used

### In-repo

- **[CLAUDE.md](../../CLAUDE.md)** — Canonical coding guidelines (source of truth).
- **[.cursor/rules/coding-guidelines.mdc](../../.cursor/rules/coding-guidelines.mdc)** — Same content for Cursor (always apply).
- **[audit.md](audit.md)** — Audit results and changes made to align with the guidelines.
- **[pyproject.toml](../../pyproject.toml)** — Ruff (lint/format), mypy, pytest, pydocstyle, per-file ignores, and rule references.

### Style and formatting

- **PEP 8** — Style guide for Python (line length overridden to 88; double quotes).
- **PEP 484** — Type hints.
- **PEP 585** — Built-in generics (`list[...]`, `dict[...]`).
- **Google Python Style Guide** — Docstring convention (pydocstyle `convention = "google"`).
- **Ruff** — Linting and formatting; rule sets include pyflakes (F), pycodestyle (E/W), isort (I), pep8-naming (N), pyupgrade (UP), flake8-annotations (ANN), flake8-type-checking (TC), mccabe (C90), pydocstyle (D), pylint (PL), and many others (see `[tool.ruff.lint]` in pyproject).

### Types and validation

- **Pydantic** — Data validation and settings; `BaseModel`, `RootModel`, `Field`, `ConfigDict`; used for all structured API data and no-dict-in-signatures rule.
- **Mypy** — Static type checking; strict mode; pydantic plugin; overrides for third-party modules without stubs.

### Logging and observability

- **structlog** — Structured (JSON) logging; stdlib integration; used via `_log_config`.
- **Sentry** — Error reporting when `SENTRY_DSN` is set; logging integration.

### Testing

- **pytest** — Test runner; asyncio mode; strict markers; warnings as errors.
- **pytest-asyncio** — Async tests.
- **PydanticAI TestModel** — Agent tests without calling a real LLM.

### Frameworks and SDKs (conventions only; some lack stubs)

- **PydanticAI** — Agent/tool patterns; `RunContext`, tool decorators.
- **Chainlit** — UI callbacks and session (untyped in our usage).
- **A2A SDK** — RequestContext, handlers (untyped).
- **Langfuse** — Prompts and observations (untyped).
- **Starlette / FastAPI** — Request, app.state, routing.

These resources underpin the rules in CLAUDE.md and the configuration in `pyproject.toml` and CI.
