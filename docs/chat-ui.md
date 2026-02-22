# Chat UI (Chainlit)

Local dev UI for interactive refactoring. It is one of two surfaces that share the same [orchestrator](architecture.md) (tools + engines). Reads and writes `playground/` files directly — no Docker, no sync server needed.

```bash
make ui
```

Opens at `http://localhost:8000`. On start you pick a workspace language (Python now; TypeScript coming soon) and a mode:

| Mode | Behaviour |
|------|-----------|
| **Ask** | Pauses for approval when a rename would cause a name collision |
| **Auto** | Applies renames without confirmation |
| **Plan** | Shows what would change without writing files |

Type a rename command in the chat:

- `rename greet to greet_user`
- `rename foo to bar in scope main`
- `{"old_name": "greet", "new_name": "greet_user"}`

The UI scans all files in the active workspace, applies the rename to every file that references the symbol, and shows a step-by-step breakdown of what changed.
