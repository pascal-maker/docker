# Cursor plan agent prompt: Deploy sync engine for alpha (corrected)

**Use this as the full user prompt for a Cursor plan agent in Plan mode.** The agent should produce a detailed, actionable plan (no code yet). Copy everything below the line into the agent.

---

## Context and corrections to the previous sync deploy plan

A previous local plan (`deploy_and_secure_sync_server_fdcfbc62`) exists, but it is **outdated**. Key corrections:

1. **Auth is GitHub OAuth, not API keys.** We completed a full auth overhaul: `GitHubTokenMiddleware` (Starlette `BaseHTTPMiddleware`) validates GitHub Bearer tokens via `api.github.com/user` with TTL cache, then checks user status in Firestore (pending/active/banned), enforces rate limits, and writes audit logs. The same middleware is already applied to both A2A and sync (`src/refactor_agent/sync/app.py` already has `GitHubTokenMiddleware`). There is NO `ApiKeyMiddleware` or `A2A_API_KEYS` — those were superseded. Local dev fallback: `A2A_API_KEY` env var bypasses GitHub for local development only.

2. **Workspace-in-JSON is not supported.** The extension does NOT send workspace inline. It always uses sync + `use_replica: true`. The inline `workspace` field in the executor is legacy and should be removed. Sync is the **only** path to supply workspace to the A2A executor.

3. **Git clone is part of sync.** On first sync, the server runs `git clone` using the user's GitHub token (which has `repo` scope). The extension sends `repo_url` + only dirty/unsaved files (from `git status --porcelain`). The server clones into `REPLICA_DIR`, switches to the correct branch, then overlays the dirty files. This is already partially implemented in `src/refactor_agent/sync/server.py` (`_clone_repo` and `_handle_bootstrap`).

4. **Replicas are ephemeral with TTL.** `REPLICA_DIR` lives on the Cloud Run instance filesystem. After a period of inactivity (no messages for N minutes), the replica should be cleaned up. On reconnect or instance eviction, the extension re-syncs (re-clone + re-overlay). No persistent storage needed.

5. **Chainlit is out of scope.** Chainlit is a dev/test surface that calls the orchestrator directly in-process. It does not use A2A or sync. Hosted Chainlit is not required for alpha. Do not plan for it.

6. **Alpha onboarding mode.** Users authenticate with GitHub OAuth. New users get `status="pending"` in Firestore and must be manually approved before gaining access. This is already implemented and enforced by the middleware. The sync deploy plan does not need to change auth — just ensure the existing `GitHubTokenMiddleware` is applied to all sync endpoints (it already is in `sync/app.py`).

## Current state

- **A2A on Cloud Run:** Deployed. GitHub OAuth enforced. CI security tests verify unauthenticated POST returns 401.
- **Sync on Cloud Run:** NOT deployed. `entrypoint-cloudrun.sh` runs only `run_ast_refactor_a2a.py`.
- **Sync app (`src/refactor_agent/sync/app.py`):** Exists with `GitHubTokenMiddleware` already applied. Has `POST /sync/workspace` and `WebSocket /`.
- **Git clone in sync:** Partially implemented in `src/refactor_agent/sync/server.py`. The `_handle_bootstrap` function accepts `github_token` and `repo_url`; `_clone_repo` runs `git clone` with the token.
- **Extension:** Always pushes to sync first (POST /sync/workspace with Bearer token, repo_url, and dirty files), then sends A2A request with `use_replica: true`.
- **Auth middleware:** `GitHubTokenMiddleware` in `src/refactor_agent/a2a/auth_middleware.py`. Already applied to both A2A app and sync app. Validates GitHub token, checks Firestore user record, rate limits, audit log.

## Your task

Create a plan to **deploy the sync engine alongside A2A on Cloud Run** for alpha. Specifically:

### 1. Combined ASGI app (single service, single port)

Cloud Run exposes one port. Build a combined ASGI app that routes by path and request type:

| Path | Method / type | Handler | Auth |
|------|--------------|---------|------|
| `/.well-known/agent-card.json` | GET | A2A | None (public) |
| `/` | POST | A2A (JSON-RPC) | GitHubTokenMiddleware |
| `/` | WebSocket upgrade | Sync | GitHubTokenMiddleware |
| `/sync/workspace` | POST | Sync | GitHubTokenMiddleware |

The existing `run_ast_refactor_a2a.py` builds the A2A app and wraps it with method logging. The sync app is built by `build_sync_app()` in `sync/app.py`. Both already have `GitHubTokenMiddleware`. The combined app needs a router that dispatches by path and scope type.

**Important:** WebSocket upgrades do not go through Starlette's `BaseHTTPMiddleware`. The sync app already handles this (middleware is on the Starlette app), but verify that auth works for WebSocket in the combined routing — the token must be extracted from WebSocket upgrade headers.

### 2. Git clone and ephemeral replica

- `REPLICA_DIR` is set in the container env (e.g. `/workspace` or `/tmp/replica`). It is writable on Cloud Run.
- On first sync (POST /sync/workspace with `repo_url`), the server clones the repo into `REPLICA_DIR` using the user's GitHub token. This is already in `_handle_bootstrap` / `_clone_repo`.
- Dirty files (modified/untracked) are overlaid on top of the cloned HEAD.
- After refactor, updated files are in `REPLICA_DIR`; A2A returns them as artifacts.
- **TTL cleanup:** Add a background task or check that cleans up `REPLICA_DIR` after N minutes of inactivity. Cloud Run instances may be evicted anyway, but explicit cleanup prevents disk bloat on long-lived instances.
- **Multi-user:** For alpha with few users, one replica at a time per instance is acceptable. For future scale, consider per-user replica directories (e.g. `REPLICA_DIR/<user_id>/`).

### 3. Entrypoint and Terraform

- New entrypoint script (e.g. `scripts/backend/run_refactor_backend.py`) that builds the combined app and runs uvicorn on `PORT`.
- Update `docker/entrypoint-cloudrun.sh` to run the new script.
- Add `REPLICA_DIR` env var to `infra/cloudrun_a2a.tf`.
- No new Cloud Run service or secret. Same image, same auth.

### 4. Remove workspace-in-JSON from executor

- Remove `WorkspaceRenameParams` and `SingleFileRenameParams` from `src/refactor_agent/a2a/models.py`.
- Remove the `_build_workspace_dir` function and inline workspace parsing from `src/refactor_agent/a2a/executor.py`.
- The executor should ONLY support `use_replica: true` (reading from `REPLICA_DIR`).
- Update tests accordingly.

### 5. Extension: sync URL = A2A URL

- For hosted use, the sync URL and A2A URL are the **same** Cloud Run URL. The extension should use one URL for both. Update `refactorAgent.syncUrl` default or derive it from `refactorAgent.a2aBaseUrl`.
- The extension already sends Bearer token on sync requests. No auth changes needed.

### 6. Docs

- Update `docs/infra/gcp.md`: Remove "Sync not deployed" section. State that sync is deployed with A2A on the same URL.
- Update `docs/clients/sync-service.md`: Document git clone flow, ephemeral replica, TTL.
- Update `docs/infra/architecture-schematic.md` section 5 "Cloud Run — today" to reflect the deployed state.

## Out of scope

- Chainlit (dev/test only, calls orchestrator directly, no sync needed)
- Multi-user replica directories (alpha = one user at a time per instance)
- Persistent storage for replicas (ephemeral is fine; re-clone on reconnect)
- Email notifications for onboarding (separate task)
- Branch switching detection (extension can re-sync; server just re-clones)

## Key files

- `src/refactor_agent/sync/app.py` — Sync Starlette app (already has auth middleware)
- `src/refactor_agent/sync/server.py` — WebSocket handler, `_clone_repo`, `_handle_bootstrap`
- `src/refactor_agent/a2a/auth_middleware.py` — `GitHubTokenMiddleware`
- `scripts/a2a/run_ast_refactor_a2a.py` — Current A2A entrypoint (build app, method logging, uvicorn)
- `docker/entrypoint-cloudrun.sh` — Current Cloud Run entrypoint (A2A only)
- `docker/entrypoint.sh` — Local entrypoint (sync + A2A, two processes)
- `infra/cloudrun_a2a.tf` — Cloud Run Terraform
- `vscode-extension/src/extension.ts` — Extension (sync + A2A calls)
- `docs/infra/architecture-schematic.md` — Architecture documentation

## Deliverable

A concise, actionable plan with specific file changes, routing logic, TTL strategy, and implementation order. Do not implement — plan only.
