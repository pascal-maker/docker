# Playground: Python (DDD fixture)

**Purpose:** Fixture for testing the refactor agent: single-step renames and **multi-step refactor schedules** (e.g. enforce frontend/backend boundary, refactor to vertical slice). Not part of the main app or test suite.

## Layout (Domain Driven Design)

- **`domain/`** — Entities and value objects:
  - `entities/order.py`, `entities/product.py`
  - `value_objects/money.py`, `value_objects/order_id.py`
- **`application/`** — Use cases:
  - `use_cases/create_order.py`, `use_cases/get_order.py`
- **`infrastructure/`** — Adapters:
  - `repositories/order_repository.py`
- **`frontend/`** — **Intentional boundary violation:** backend use case placed in frontend:
  - `frontend/get_order.py` — `get_order_handler` should live in `application/use_cases/`; refactoring to enforce frontend/backend boundary would move it and update imports.

Top-level `greeter.py`, `caller.py`, `extra.py` remain for single-symbol rename testing (e.g. MCP `rename_symbol`).

## Example prompts for refactor schedule testing

- “Refactor this codebase to a vertical slice structure.”
- “Enforce frontend/backend boundary: move backend use cases out of the frontend folder.”
- “Create a plan to reorganize the project so that the frontend layer does not contain domain logic.”

## Running the playground

From the repo root with `PYTHONPATH` including the repo root:

```bash
uv run python -c "from playground.python.caller import main; main()"
uv run python -c "from playground.python.extra import main; main()"
```

No extra dependencies; uses only the standard library.
