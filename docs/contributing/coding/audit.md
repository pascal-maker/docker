# Coding guidelines audit

Audit of the repository against **CLAUDE.md** (and `.cursor/rules/coding-guidelines.mdc`). Each guideline group was checked across `src/`, `tests/`, and `scripts/` where relevant.

---

## General

| Guideline | Status | Notes |
|-----------|--------|--------|
| Strict typing; no untyped defs; no `Any` without justification | ✅ | mypy-strict in pyproject; no `Any` or untyped defs found in signatures. |
| `make check` (format, lint, typecheck, test) before commit | ✅ | CI runs four separate jobs. |
| Line length 88 | ✅ | Enforced by ruff. |
| Google-style docstrings on public APIs | ✅ | Spot-checked; per-file ignores only where needed. |
| No relative imports | ✅ | Grep found no `from .` or `from ..` in `src/` or `tests/`. |
| No suppressions without comment | ✅ | All `# noqa` and `# type: ignore` now have short explanations (see changes below). |
| Complexity / statements / args limits | ✅ | Enforced via ruff (mccabe, pylint); some per-file ignores with comments. |

---

## Types and APIs

| Guideline | Status | Notes |
|-----------|--------|--------|
| Python ≥ 3.12; modern syntax | ✅ | pyproject `requires-python = ">=3.12"`; no `List`/`Dict`/`Tuple` in annotations. |
| No `dict`/`Dict`/`TypedDict` in function signatures | ✅ with exception | Only exception: `_compat._patched(schema: dict[str, object]) -> dict[str, object]` — required by pydantic_ai monkey-patch contract. Documented in code and in CLAUDE.md. |
| Prefer narrowing over `cast`/`as` | ✅ | No `cast()` in `src/`; one justified `type: ignore[no-any-return]` in `_log_config.get_logger`. |
| `ConfigDict(extra="allow")` only when needed | ✅ | Used for open-ended payloads (e.g. JSON-RPC, tool args) with models. |

---

## Imports

| Guideline | Status | Notes |
|-----------|--------|--------|
| Annotation-only imports in `TYPE_CHECKING` | ✅ | Per-file TC001/TC002/TC003 only where runtime needed (Pydantic, A2A SDK, etc.), with comments. |
| Third-party in `TYPE_CHECKING` unless runtime | ✅ | Orchestrator uses inline TC002 for AnthropicModelSettings (no `from __future__ annotations`). |

---

## Logging

| Guideline | Status | Notes |
|-----------|--------|--------|
| Module-level `logger.py` per package that logs | ✅ | `agent`, `engine`, `sync`, `orchestrator`, `schedule`, `ci`, `ui` have `logger.py`; dashboard has no logging. |
| Structured logging via `_log_config` | ✅ | `configure_logging()` called from sync/__main__, ci/__main__, ui/app. |
| No `print()` in `src/` or `tests/` | ✅ | No `print(` in `src/`; tests only use `print` inside string literals (test data). |

---

## Testing

| Guideline | Status | Notes |
|-----------|--------|--------|
| pytest asyncio_mode = auto | ✅ | pyproject.toml. |
| TestModel for agent tests; no real LLM | ✅ | CI/planner tests mock `run_planner`; no Agent creation with real model in tests. |
| Warnings are errors | ✅ | `filterwarnings = ["error"]`. |
| Tests may access private members | ✅ | SLF001 in per-file-ignores for tests. |

---

## Infrastructure and data

| Guideline | Status | Notes |
|-----------|--------|--------|
| Vector DB logic in DB, not app | N/A | No vector DB usage in current codebase. |

---

## CI and tooling

| Guideline | Status | Notes |
|-----------|--------|--------|
| Format, lint, typecheck, test as separate jobs | ✅ | `.github/workflows/ci.yml` has four jobs. |
| Per-file ignores only where required | ✅ | All current per-file-ignores are documented in pyproject; no blanket suppressions. |

---

## Changes made during audit

1. **CLAUDE.md / .cursor/rules**
   - Documented exception for dict in signatures when implementing a third-party callback (e.g. monkey-patch). Same text in CLAUDE.md and coding-guidelines.mdc.

2. **`_compat.py`**
   - Added comment above `_patched` explaining that pydantic_ai requires dict in/out for the patched callback.

3. **Suppression comments**
   - **a2a/executor.py**: Comments for C901/PLR0911/PLR0912 (dispatch + validation; message dispatch and artifact handling); ASYNC240 (sync rglob/Path check in executor).
   - **a2a/bridge.py**, **a2a/server.py**: TC002 — “used at runtime”.
   - **orchestrator/agent.py**: PLR0911 (scope and file-handling branches); FBT001/FBT002 (boolean flag for force rename); I001, PLC0415 (lazy import to avoid circular deps).
   - **mcp/server.py**: ASYNC240 — “sync I/O in MCP handler”.
   - **`_rename_python`**: Moved to module top level (was incorrectly nested under `_is_reply_no` after an edit) so it is defined and callable correctly.

---

## Summary

- **One documented exception**: `dict` in/out in `_compat._patched` for the pydantic_ai callback; guideline and code both explain it.
- **No new violations** introduced; all suppressions reviewed and given short explanations where missing.
- **Guidelines** are reflected in CLAUDE.md and the Cursor rule; audit is recorded in this file for future reference.

---

## Dict-in-signatures migration (2025)

Enforcement and migration completed per [docs/plans/remove-dicts-from-signatures.md](../../plans/remove-dicts-from-signatures.md):

1. **Enforcement:** Ruff `banned-api` for `typing.Dict` and `typing.TypedDict`; custom AST checker `scripts/lint/check_no_dict_sig.py`; `make check-no-dict-sig`; pre-commit hook; CI job.
2. **Allowlist:** `# no-dict-sig` on def line (or line before); path allowlist for `_compat._patched`.
3. **Migrated:** executor (`PromptOnlyPayload`), scripts (`HttpHeaders`, `MessageSendPayload`, `JsonRpcResponse`), ASGI (`Scope`, `Receive`, `Send`).
4. **Documented exceptions:** A2A method_logging (SDK/ASGI), probe_settings (Pydantic API), functions (GitHub/Firestore/Flask).
5. **Docs:** [types-and-pydantic.md](../../reference/types-and-pydantic.md), [no-dict-signatures.mdc](../../../.cursor/rules/no-dict-signatures.mdc), CLAUDE.md and coding-guidelines.mdc updated.
