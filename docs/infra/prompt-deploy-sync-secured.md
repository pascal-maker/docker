# Cursor plan agent prompt: Deploy sync server and secure it from day one

**Use this as the full user prompt for a separate Cursor plan agent in Plan mode.** The agent should produce a detailed, actionable plan (no code yet). Copy the entire section below into the agent.

---

## Context

We have two components that work in tandem:

1. **A2A agent** — HTTP server (agent card + JSON-RPC message/send). Already deployed on Cloud Run. Auth hotfix for it is in progress separately (API key for POST /).
2. **Sync server** — WebSocket (/) + POST /sync/workspace; writes client workspace to a **replica directory** (`REPLICA_DIR`). The A2A executor reads from `REPLICA_DIR` when the client sends `use_replica: true`. Today the sync server is **not** deployed on Cloud Run; only the A2A server is. Docs currently tell users to use “workspace-in-JSON” for hosted use, but that strategy is **not feasible** (large workspaces, bad UX). We need the sync server **deployed** so clients can sync then call A2A with `use_replica: true` as in local/Docker flows.

**Critical constraint:** A2A and sync must share the **same** `REPLICA_DIR` (same filesystem) so that when a client syncs files and then calls A2A with `use_replica: true`, the A2A executor can read the replica. So they must run in the same container (or use shared storage; prefer same container for a first deployment).

**Unified auth:** A2A and sync are one backend and are always used together. They must use the **same** API key and auth mechanism — no separate `SYNC_API_KEY`. Use the same secret as the A2A auth hotfix (e.g. `refactor-agent-a2a-api-key` / `A2A_API_KEY` env). Clients send `Authorization: Bearer <key>` or `X-API-Key` for both sync (WebSocket + POST /sync/workspace) and A2A (POST /). One credential for the whole refactor backend.

## Your task

Create a **plan** to:

1. **Deploy the sync server** in staging/production alongside the A2A server so that:
   - Clients can push workspace via sync (WebSocket or POST /sync/workspace) then call A2A with `use_replica: true`.
   - A2A and sync share `REPLICA_DIR` (e.g. single Cloud Run service with one process that runs both apps, or two processes in one container with a gateway on the single exposed port; or one combined ASGI app that routes by path).
   - Existing Terraform and Cloud Run patterns are reused where possible.

2. **Secure the sync server from the get-go** (no period where it is deployed without auth):
   - Require authentication for **all** sync endpoints: WebSocket upgrade (e.g. `Authorization: Bearer <key>` or `X-API-Key` in headers or query) and POST /sync/workspace.
   - Unauthenticated requests must receive **401**. Use the **same** API key as A2A (same env var `A2A_API_KEY`, same Secret Manager secret). Same pattern as the A2A auth hotfix: single shared key, constant-time compare. Do **not** introduce a separate `SYNC_API_KEY`.

3. **Update clients and docs** so that:
   - Hosted sync URL is documented and configurable (e.g. env or extension setting).
   - VS Code extension (and any other client) can point to the deployed sync URL and send the API key when connecting.
   - Docs no longer recommend “workspace-in-JSON” as the primary strategy for hosted use; sync is the canonical path.

## Key files to consider

- **Sync app:** [src/refactor_agent/sync/app.py](src/refactor_agent/sync/app.py) — Starlette app with WebSocket at `/`, POST `/sync/workspace`. No auth today.
- **Sync server logic:** [src/refactor_agent/sync/server.py](src/refactor_agent/sync/server.py) — WebSocket message handling, replica writes.
- **A2A entrypoint (Cloud Run):** [docker/entrypoint-cloudrun.sh](docker/entrypoint-cloudrun.sh) — currently runs only A2A (`run_ast_refactor_a2a.py`). No sync.
- **Local entrypoint (both):** [docker/entrypoint.sh](docker/entrypoint.sh) — runs sync in background, A2A in foreground (two processes, two ports).
- **A2A executor and REPLICA_DIR:** [src/refactor_agent/a2a/executor.py](src/refactor_agent/a2a/executor.py) — reads `REPLICA_DIR` from env when `use_replica` is true.
- **Sync protocol:** [docs/clients/sync-service.md](docs/clients/sync-service.md).
- **Infra:** [infra/cloudrun_a2a.tf](infra/cloudrun_a2a.tf), [infra/secrets.tf](infra/secrets.tf).

## Out of scope for this plan

- Implementing the A2A auth hotfix (handled elsewhere).
- Rate limiting or abuse protection beyond auth.
- Multiple API keys or per-client keys (single shared key is fine for the plan).

## Deliverable

A concise, actionable plan that:

- Describes the deployment architecture (single service vs multiple, routing, REPLICA_DIR).
- Lists code changes (auth middleware or dependency for sync, gateway/combined app if needed, Terraform/infra).
- States how WebSocket and POST /sync/workspace are protected and how the key is supplied (header, query, etc.).
- Updates docs and client configuration so hosted sync is the default path and secured from the get-go.
