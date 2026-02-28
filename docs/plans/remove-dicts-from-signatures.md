# Remove dicts from function signatures — migration plan (archived)

This plan was implemented to enforce and migrate away from `dict`/`Dict`/`TypedDict` in function signatures across the repo. The migration is complete; this doc archives the design and history.

---

## Summary

- **Enforcement:** Ruff `banned-api` (typing.Dict, TypedDict) + custom AST checker (`scripts/lint/check_no_dict_sig.py`).
- **Allowlist:** `# no-dict-sig` on the def line or line before; path-based allowlist for `refactor_agent/_compat.py:_patched`.
- **Migration:** Replaced dict signatures with Pydantic models where possible; documented exceptions for third-party callbacks (ASGI, A2A SDK, Pydantic settings, GitHub/Firestore/Flask in functions).

---

## Enforcement design

| Approach | Pros | Cons |
|----------|------|------|
| Ruff banned-api | No deps; catches typing.Dict/TypedDict imports | Does not catch builtin `dict` in annotations |
| Custom AST checker | No deps; full control; catches all forms | Must implement and maintain |
| Semgrep | Industry standard | New dep; pattern coverage may need tuning |

**Chosen:** Ruff banned-api + custom AST checker.

---

## Allowlist format

- **Inline:** `# no-dict-sig` (or `# no-dict-sig: reason`) on the def line or the line immediately before.
- **Path-based:** `refactor_agent/_compat.py:_patched` in checker config (default allowlist).

---

## Migration phases (completed)

1. **Phase 0** — Ruff banned-api; AST checker; `make check-no-dict-sig`; pre-commit; CI.
2. **Phase 1** — ASGI: use Starlette `Scope`, `Receive`, `Send` where possible; noqa for ASGI message dicts.
3. **Phases 2–4** — Migrated executor, probe_settings, scripts, functions to Pydantic models or documented exceptions.
4. **Phase 5** — Docs: CLAUDE.md, no-dict-signatures.mdc, types-and-pydantic.md, audit, plan archive.

---

## References

- [CLAUDE.md](../../CLAUDE.md) — Canonical guidelines
- [docs/reference/types-and-pydantic.md](../reference/types-and-pydantic.md) — Reference doc
- [docs/contributing/coding/audit.md](../contributing/coding/audit.md) — Audit and exceptions
