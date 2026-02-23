# Chat UI (Chainlit)

Local dev UI for interactive refactoring. It is one of two surfaces that share the same [orchestrator](../guides/architecture.md) (tools + engines). Reads and writes `playground/` files directly — no Docker, no sync server needed.

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

**Multi-step refactor (schedule):** Ask for a plan or schedule (e.g. “Refactor this codebase to a vertical slice structure”, “Enforce frontend/backend boundary”). The agent can call `create_refactor_schedule` to produce a `RefactorSchedule`. The UI then shows the schedule and, in **Plan** mode, stops there; in **Auto** or **Ask** (after you confirm), it runs the [schedule executor](../contributing/refactor-schedule/README.md) and reports results. See [Testing](../contributing/testing/README.md) for how to use the DDD playgrounds to test this flow.

## Persistence, environments, and sharing

Chat history, resume, and thread sharing require **persistence** and **authentication**.

- **Postgres (Docker):** The app expects Postgres to be run via Docker. Start it with `docker compose up postgres` (or `docker compose up postgres chainlit` to run the UI in Docker too). Use `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` in `.env` (see `.env.example`). Data is stored in the `postgres_data` volume for local, staging, and prod.
- **Persistence:** Set `DATABASE_URL` to a Postgres URL with scheme `postgresql://` (e.g. `postgresql://user:pass@host:5432/dbname`). Do not use `postgresql+asyncpg://` — Chainlit’s data layer passes the URL to asyncpg, which expects `postgresql://` or `postgres://`. When using `make ui` on the host use `localhost:5432`; in Docker the compose file sets `DATABASE_URL` accordingly.
- **Auth:** Set `CHAINLIT_AUTH_SECRET` (e.g. run `chainlit create-secret`). Optional: `CHAINLIT_AUTH_USER` and `CHAINLIT_AUTH_PASSWORD` for the login form (default: `dev` / `dev`). The UI may show “Email” for the first field; enter your **username** there (e.g. `dev`), and your password in the second field.
- **Environments:** Set `CHAINLIT_ENVIRONMENT` (e.g. `dev`, `staging`, `prod`). For multiple environments, run **one Chainlit instance per environment** (each with its own URL and env vars); threads are tagged with this value and the sidebar shows only that instance’s threads.
- **Sharing:** Click “Share conversation” in the welcome message to mark the thread as shared; others with the share link can view it (read-only) after logging in. Sharing is enabled in `src/.chainlit/config.toml` (`allow_thread_sharing = true`).

**Database schema:** Chainlit’s tables (`User`, `Thread`, `Step`, etc.) are created automatically on **first** Postgres start: `docker/chainlit-schema.sql` is mounted into the Postgres image’s init directory and runs when the data directory is empty. If you already had a Postgres volume without the schema (e.g. you see `relation "User" does not exist`), apply the schema once:

```bash
docker compose exec -T postgres psql -U chainlit -d chainlit < docker/chainlit-schema.sql
```

Or start from a clean DB: `docker compose down -v` then `docker compose up -d postgres chainlit` (this deletes existing DB data).

**If you get "Not Found":** Open the app at the root URL: **http://localhost:8000** (no path like `/chat` or `/app`). If you use a reverse proxy with a subpath, set `CHAINLIT_ROOT_PATH` to that path (e.g. `/chainlit`) and visit `http://your-host/chainlit`. When using Docker, ensure the `chainlit` service is running (`docker compose ps`) and rebuild after config changes: `docker compose build chainlit && docker compose up -d chainlit`.
