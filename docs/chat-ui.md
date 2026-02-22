# Chat UI (Chainlit)

Local dev UI for interactive refactoring. It is one of two surfaces that share the same [orchestrator](architecture.md) (tools + engines). Reads and writes `playground/` files directly — no Docker, no sync server needed.

```bash
make ui
```

Opens at `http://localhost:8000`. On start you pick a workspace language (Python or TypeScript) and a mode. The current mode is shown in the welcome message (**Ask | Edit (Auto) | Plan**); switch via the chat profile selector.

| Mode | Behaviour |
|------|-----------|
| **Ask** | Pauses for approval on collisions; for refactor schedules, shows schedule and asks before executing |
| **Auto** (Edit) | Applies renames without confirmation; executes refactor schedules immediately |
| **Plan** | Shows what would change without writing files; for schedules, displays the plan only |

**Single-step refactors:** Type a rename or similar command (e.g. `rename greet to greet_user`, `move symbol X from a.ts to b.ts`). The agent uses the orchestrator tools and applies changes according to mode.

**Multi-step refactor (schedule):** Ask for a plan or schedule (e.g. “Refactor this codebase to a vertical slice structure”, “Enforce frontend/backend boundary”). The agent can call `create_refactor_schedule` to produce a `RefactorSchedule`. The UI then shows the schedule and, in **Plan** mode, stops there; in **Auto** or **Ask** (after you confirm), it runs the [schedule executor](refactor-schedule/README.md) and reports results. See [Testing](testing/README.md) for how to use the DDD playgrounds to test this flow.
