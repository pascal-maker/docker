You are working in a strict-typing Python codebase. These rules are absolute. Violations are bugs, not style issues.

### You MAY NOT do any of the following without explicit written approval in the task:

- Use `Any` from typing
- Add `# type: ignore` comments
- Add `# noqa` suppressions
- Add new entries to `pyproject.toml` per-file ignores
- Broaden existing mypy overrides in `pyproject.toml`
- Use `dict`, `Dict`, `TypedDict` in function signatures or return types
- Use `Optional[X]` (use `X | None`)
- Import from `typing`: `List`, `Dict`, `Tuple`, `Set` (use built-ins)

### When you hit a type error you CANNOT easily fix:

1. Stop and describe the problem to the user
2. Propose a proper typed solution (new Pydantic model, Protocol, TypeVar, etc.)
3. Do NOT suppress it and move on

### Protected files — do NOT edit these without being explicitly asked:

- `pyproject.toml` (the `[tool.ruff.lint.per-file-ignores]` and `[tool.mypy]` sections)
- `.cursor/rules/*.mdc`
- `CLAUDE.md`

### Pre-commit is not something to fix by suppressing rules

If pre-commit fails, fix the underlying code. Adding ignores to make it pass is not fixing it.

---

# Coding guidelines

Canonical repo-wide quality rules. Cursor uses the same content via `.cursor/rules/coding-guidelines.mdc` (always apply).

---

# General

* Strict typing across the entire repository; no untyped defs, no `Any` without justification.
* Run `make pre-commit-install` once after clone to enable git hooks. Hooks run ruff, TS format/lint/typecheck, and mypy. For full checks including tests, run `make check` before pushing. CI runs format, lint, typecheck, and test as separate jobs.
* Line length 88 characters (Python); enforced by ruff.
* Google-style docstrings on all public functions and classes; skip module, package, and `__init__` docstrings.
* No relative imports; use absolute imports only.
* Never suppress linter or type-checker warnings without a short comment explaining why.
* Max function complexity 10 (mccabe), max statements 40, max args 6.

---

# Types and APIs

* Python ≥ 3.12; use modern syntax: `X | Y` unions, `list[...]` not `List[...]`, `dict[...]` not `Dict[...]` in annotations.
* All code is mypy-strict. No `Any` without justification.
* **No dict in signatures:** Do not use `dict`, `Dict`, or `TypedDict` in function parameters or return types. Use Pydantic `BaseModel` for structured data; `RootModel[dict[str, X]]` for JSON-RPC–style payloads. Exception: third-party callbacks that require dict in/out (e.g. ASGI messages, monkey-patches, Pydantic settings sources)—add `# no-dict-sig` and a short comment. Enforcement: `make check-no-dict-sig` and ruff `banned-api`; CI fails on violations.
* **Common pitfall:** When adding new functions, never use `dict`/`Dict`/`TypedDict` in params or return types; use Pydantic models instead.
* Prefer proper type narrowing or refactors over `cast()` or `as Type` assertions; avoid `cast` and `as ...` except where required by context managers or exception handling.
* Pydantic: use `ConfigDict(extra="allow")` only when needed for open-ended payloads; document why.
* Prefer strict typing over `getattr`, `hasattr`, `setattr`, `delattr`: use Pydantic model attributes and explicit types. Use `getattr`/`hasattr` only when accessing untyped third-party objects (e.g. SDKs without stubs); add a short comment in that case.

---

# Imports

* Imports used only in type annotations go inside `TYPE_CHECKING` blocks; the file must have `from __future__ import annotations`. Exception: imports required at runtime for Pydantic model resolution — mark with `# noqa: TC001` and a comment.
* Third-party imports used only in annotations go in `TYPE_CHECKING` unless the type is needed at runtime (e.g. TypedDict in a file without `from __future__ import annotations`); then use inline `# noqa: TC002` with a comment.

---

# Logging

* Module-level loggers: for each package (directory with `__init__.py`) that needs logging, define `logger.py` (not `logging.py`, to avoid colliding with the stdlib) and export a `logger` from it. Other files in that package import it: `from refactor_agent.<package>.logger import logger`. The package logger is created via `refactor_agent._log_config.get_logger("refactor_agent.<package>")`.
* Structured logging: use the repo-wide `refactor_agent._log_config`. Call `configure_logging()` once at app startup (e.g. in `__main__` or when the app module loads). Logging is JSON to stderr; if `SENTRY_DSN` is set, error-level logs go to Sentry.
* No bare output in library code: no `print()` or similar in `src/` or `tests/`. Scripts in `scripts/` may use `print()` for CLI output. Frontend/UI code (e.g. Chainlit) must use the module logger only; for user-facing errors, show messages in the UI and log with `logger.exception` / `logger.error`. Frontend error monitoring: use Sentry’s JS SDK (or similar) in the browser and/or ensure backend errors are logged and sent to Sentry.

---

# Testing

* pytest with `asyncio_mode = auto`; no manual `@pytest.mark.asyncio` needed (but allowed).
* Use PydanticAI’s `TestModel` for agent tests — never call a real LLM in tests.
* Warnings are errors (`filterwarnings = ["error"]`).
* Tests may access private members (`SLF001` ignored for tests).

---

# Infrastructure and data

* For vector databases (e.g. Qdrant): push logic into the DB where possible; do not reimplement similarity or filtering in application code when the vector DB can do it directly.

---

# CI and tooling

* Format check, lint, typecheck, and test are separate pipeline jobs; each reports its own pass/fail.
* Per-file lint ignores are only where framework or convention requires it; prefer fixing code over adding ignores.
* **JS/TS:** Use **pnpm only**; no npm. Repo is a **pnpm workspace**: one root `pnpm-lock.yaml`, `pnpm-workspace.yaml` lists apps/dashboard, apps/site, apps/vscode-extension, packages/design-system, packages/ts-morph-bridge. Run `pnpm install` at root (or `make ts-install`); CI runs one install and caches the lockfile.
* **TypeScript (except playground):** Same quality bar as Python: format (Prettier), lint (ESLint), typecheck (tsc). Run locally via `make ts-format-check`, `make ts-lint`, `make ts-typecheck` (or per-package `pnpm run …`); CI runs jobs `ts-format-check`, `ts-lint`, `ts-typecheck` for apps/dashboard, apps/site, apps/vscode-extension, packages/design-system, and packages/ts-morph-bridge.
