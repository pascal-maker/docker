# Playground: TypeScript (DDD fixture)

**Purpose:** Fixture for testing the refactor agent: single-step renames and **multi-step refactor schedules** (e.g. enforce frontend/backend boundary, refactor to vertical slice). Not part of the main app or test suite.

## Layout (Domain Driven Design)

- **`src/domain/`** — Entities and value objects:
  - `entities/Order.ts`, `entities/Product.ts`
  - `value_objects/Money.ts`, `value_objects/OrderId.ts`
- **`src/application/`** — Use cases:
  - `use_cases/CreateOrder.ts`, `use_cases/GetOrder.ts`
- **`src/infrastructure/`** — Adapters:
  - `repositories/OrderRepository.ts`
- **`src/frontend/`** — **Intentional boundary violation:** backend use case placed in frontend:
  - `src/frontend/GetOrder.ts` — `getOrderHandler` should live in `application/use_cases/`; refactoring to enforce frontend/backend boundary would move it and update imports.

Top-level `greeter.ts`, `caller.ts`, `extra.ts` remain for single-symbol rename testing.

## Example prompts for refactor schedule testing

- “Refactor this codebase to a vertical slice structure.”
- “Enforce frontend/backend boundary: move backend use cases out of the frontend folder.”
- “Create a plan to reorganize the project so that the frontend layer does not contain domain logic.”

## Build

From the playground directory or repo root:

```bash
npx tsc -p playground/typescript
```

Or from repo root with tsconfig at `playground/typescript/tsconfig.json`.
