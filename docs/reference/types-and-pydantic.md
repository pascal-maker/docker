# Types and Pydantic

Reference for our typing conventions: why we avoid `dict` in function signatures, when to use `BaseModel` vs `RootModel`, and how exceptions are documented.

---

## Why avoid dict in signatures?

- **Validation:** Pydantic models validate at parse time; bare `dict` does not.
- **Discoverability:** Model fields are explicit; callers see the shape.
- **Refactoring:** Renaming a field fails at type-check time instead of runtime.
- **Tooling:** IDEs and mypy understand models; `dict[str, Any]` is opaque.

---

## When to use what

| Use case | Use | Example |
|----------|-----|---------|
| Structured payload with known fields | `BaseModel` | `MessageSendPayload(source, old_name, new_name)` |
| JSON-RPC / arbitrary dict wrapper | `RootModel[dict[str, Any]]` | `JsonRpcResponse` for `{"jsonrpc":"2.0","id":...,"result":...}` |
| HTTP headers | `RootModel[dict[str, str]]` | `HttpHeaders` |
| Third-party callback dictates dict | Keep `dict`; add `# no-dict-sig` | ASGI `receive() -> dict`, Pydantic settings `__call__ -> dict` |

---

## Exceptions (third-party callbacks)

When a third-party API requires `dict` in or out, we document the exception with `# no-dict-sig` and a short comment:

```python
def _patched(schema: dict[str, object]) -> dict[str, object]:  # no-dict-sig: pydantic_ai callback
    ...
```

Current exceptions:

- `_compat._patched` — pydantic_ai monkey-patch contract
- `a2a/method_logging` — A2A SDK expects dict in/out; ASGI `receive`/`send` messages
- `a2a/probe_settings` — PydanticBaseSettingsSource `__call__` API
- `functions/*` — GitHub API, Firestore, Flask response headers (third-party contracts)

---

## Enforcement

- **`make check-no-dict-sig`** — Custom AST checker; fails on any function with `dict`/`Dict`/`TypedDict` in params or return type, unless `# no-dict-sig` is present.
- **Ruff `banned-api`** — Bans `typing.Dict` and `typing.TypedDict` imports.
- **CI** — Both run before lint/typecheck; pipeline fails on violations.

---

## References

- [CLAUDE.md](../../CLAUDE.md) — Canonical guidelines
- [awesome-python-typing](https://github.com/typeddjango/awesome-python-typing) — Curated typing resources
