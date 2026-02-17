# Coding guidelines

## General
- Strict typing is paramount across frontend, API and backend.
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
- `dataclass` for internal state objects (pipeline state, parsed elements) that don't need Pydantic validation.
- Agent creation goes through factory functions (`create_*_agent()`) in `agents/`. Prompts live in `prompts/` and are seeded to Langfuse.
- Pipeline nodes are `pydantic_graph.BaseNode` subclasses in `pipeline/nodes.py`. Keep node `run()` methods thin — delegate to helpers.
- Preprocessing helpers must not import agent code. Agent code must not import pipeline code. One-way dependency: pipeline → agents → models.

## API layer (`api/`)
- FastAPI with async endpoints. Return explicit `JSONResponse` with correct status codes.
- Long-running work uses background tasks with job polling (202 Accepted pattern).
- Docstring and type-annotation rules from ruff are relaxed for `api/` (per-file ignores: `D`, `ANN`, `T20`, `FBT`). Still maintain type hints on function signatures.

## Frontend (`ui/`)
- SvelteKit 5 + TypeScript strict mode + Tailwind CSS 4.
- Run `pnpm check` from `ui/` before committing frontend changes. Must produce 0 errors, 0 warnings.
- Keep types in `lib/types.ts` in sync with Python backend models.
- Components in `lib/components/`. One component per file.
- Use Svelte 5 runes (`$props`, `$state`, `$derived`) — not legacy `export let` or `$:` reactive declarations.

## Testing
- pytest with `asyncio_mode = auto`. No manual `@pytest.mark.asyncio` needed (but allowed).
- Use PydanticAI's `TestModel` for agent tests — never call real LLM in tests.
- Warnings are errors (`filterwarnings = ["error"]`).
- Tests can access private members (`SLF001` ignored for tests).
