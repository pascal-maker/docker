# Coding guidelines

## General
- Strict typing is paramount across the entire repository.
- Run `make check` (format, lint, typecheck, test) before every commit. All four must pass.
- Line length limit is 88 characters (Python). Enforced by ruff.
- Google-style docstrings on all public functions and classes. Skip module, package, and `__init__` docstrings.
- No relative imports anywhere. Use absolute imports only.
- Imports used only in type annotations go inside `TYPE_CHECKING` blocks (file must have `from __future__ import annotations`). Exception: imports required at runtime by Pydantic model resolution — mark those with `# noqa: TC001` and a comment explaining why.
- Never suppress linter/type-checker warnings without a comment explaining why.
- Max function complexity: 10 (mccabe). Max statements per function: 40. Max args: 6.

## Python backend (`src/`)
- Python >= 3.12. Use modern syntax: `X | Y` unions, `list[...]` not `List[...]`, `dict[...]` not `Dict[...]`.
- All code is mypy-strict. No `Any` without justification. No untyped defs.
- Pydantic models for all data shapes. Use `BaseModel` for structured data, `RootModel` for wrapper types.

## Testing
- pytest with `asyncio_mode = auto`. No manual `@pytest.mark.asyncio` needed (but allowed).
- Use PydanticAI's `TestModel` for agent tests — never call real LLM in tests.
- Warnings are errors (`filterwarnings = ["error"]`).
- Tests can access private members (`SLF001` ignored for tests).
