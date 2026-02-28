# Refactor issues dashboard

Centralized dashboard (Sentry/Aikido-style) for refactor/architecture check results: CI sends structured reports to an ingestion API, and users view issues by org/repo in a React (TypeScript) web UI.

## Overview

- **Ingestion**: CI jobs `POST` check results to `POST /api/ingest/check-result` (optional when env vars are set).
- **Persistence**: SQLite (default `dashboard.db`); schema: organizations, repositories, check_runs, check_run_operations.
- **Query API**: `GET /api/orgs/{org_id}/issues` (list with filters), `GET /api/orgs/{org_id}/issues/{run_id}` (detail).
- **UI**: React + Vite + TypeScript SPA in `dashboard-ui/` (TanStack Query, Tailwind). List and detail at `/` and `/orgs/{org_id}/issues`.

## Running the dashboard

### Development (backend + frontend)

1. **Backend** (API only, port 8000):

   ```bash
   # From repo root
   make dashboard
   # or
   uv run python -m refactor_agent.dashboard
   ```

2. **Frontend** (Vite dev server, port 5173; proxies `/api` to backend):

   ```bash
   cd dashboard
   pnpm install
   pnpm dev
   ```

   Open http://localhost:5173. Enter an organization ID to view issues, or go to `/orgs/<org_id>/issues`. CORS is enabled for `http://localhost:5173` and `http://127.0.0.1:5173`.

### Local preview with sample data

To populate the local DB with example check runs (so you can see the list and detail views):

```bash
make dashboard-seed
# or: uv run --directory apps/backend python scripts/seed/seed_dashboard.py
```

Uses `REFACTOR_AGENT_DASHBOARD_DB` if set, otherwise `dashboard.db` in the current directory. Then open the UI and select org **demo** or **acme**.

### Production (single origin)

1. Build the SPA:

   ```bash
   cd dashboard
   pnpm install
   pnpm build
   ```

2. Run the backend from repo root. If `dashboard-ui/dist` exists, the app serves the built SPA at `/` and `/orgs/...` and the API at `/api/...`:

   ```bash
   uv run python -m refactor_agent.dashboard
   ```

   Open http://localhost:8000 (or your port).

### Frontend scripts (dashboard-ui)

| Script        | Description              |
|---------------|--------------------------|
| `pnpm dev`    | Start Vite dev server    |
| `pnpm build`  | Typecheck + production build |
| `pnpm preview`| Preview production build |
| `pnpm format` | Format with Prettier     |
| `pnpm lint`   | Run ESLint               |
| `pnpm typecheck` | Run `tsc --noEmit`   |

Environment variables (backend, optional):

| Variable | Description |
|----------|-------------|
| `REFACTOR_AGENT_DASHBOARD_DB` | Path to SQLite DB (default: `dashboard.db`) |
| `REFACTOR_AGENT_DASHBOARD_PORT` | Port (default: 8000) |
| `REFACTOR_AGENT_INGEST_API_KEY` | If set, ingestion requires `X-API-Key` or `Authorization: Bearer <key>` |

## Ingestion API contract

**Endpoint**: `POST /api/ingest/check-result`

**Headers** (when `REFACTOR_AGENT_INGEST_API_KEY` is set):

- `X-API-Key: <key>` or `Authorization: Bearer <key>`

**Body** (JSON):

```json
{
  "org_id": "my-org",
  "repo_id": "my-org/my-repo",
  "branch": "main",
  "pr_number": 42,
  "preset_id": "ddd-boundaries",
  "goal": "Enforce frontend/backend boundary",
  "status": "failed_with_suggestions",
  "operations": [
    {
      "file_path": "frontend/get_order.py",
      "op_type": "move_symbol",
      "rationale": "Backend use case belongs in application layer"
    }
  ],
  "timestamp": "2025-02-22T12:00:00Z"
}
```

- `timestamp` is optional; server uses current time if omitted.
- `pr_number` is optional.
- `operations` is a list of `{ file_path, op_type, rationale? }`.

**Response**: `201 Created` with `{ "id": "<run_uuid>", "status": "created" }`.

## CI integration

In your CI workflow (e.g. after the refactor check produces a report):

1. Set `REFACTOR_AGENT_INGEST_URL` to the dashboard base URL (e.g. `https://dashboard.example.com`).
2. Set `REFACTOR_AGENT_INGEST_API_KEY` to the same value configured on the dashboard.
3. After generating the report, `POST` the payload above to `{REFACTOR_AGENT_INGEST_URL}/api/ingest/check-result`.

Payload can be built from your check's structured output (goal, status, and a list of operations with file_path, op_type, rationale).

## Query API

- **List**: `GET /api/orgs/{org_id}/issues?repo_id=&preset_id=&since=&until=&limit=50&offset=0`
- **Detail**: `GET /api/orgs/{org_id}/issues/{run_id}`

Both return JSON. The React UI uses these endpoints via TanStack Query.
