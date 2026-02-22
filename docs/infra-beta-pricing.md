# Beta infra and pricing (exploratory)

This doc captures the tradeoffs and options for **beta users** (VS Code extension against a hosted backend), with a focus on **maximal UX first**; scaling and cost levers can follow once the experience is right.

## Principles

- **UX first.** We’re unlikely to have many users at first. Prioritise the best possible experience immediately; optimise for scale and cost later. Unknown services get very few chances — first impression matters.
- **Sync must be fast.** Repo sync needs to be as fast as possible. After the first time, **incremental sync** (only changes) is the goal, subject to financial and technical feasibility.
- **Scale to demand.** The system should scale with usage (no single fixed server); we need a clear path to elasticity and, if we choose stateless, cold starts must be acceptable.

## Simple summary

**The problem:** Beta users use the VS Code extension against your hosted backend. You don’t want them to re-upload the whole repo on every new conversation (slow, annoying). You also have no budget.

**The idea:** Either (1) keep servers stateless but **store the last copy of the repo** (and a bit of agent memory) in cheap storage — so each new conversation only sends *changes* and the server rebuilds from storage — or (2) give each user a small **long-lived environment** (a machine or app that sleeps when idle) where the repo already lives, so sync is just “push changes” and no full upload.

**Options in a nutshell:** Stateless + storage = you build a sync protocol and a store; scale is automatic and you pay per use. Long-lived (Fly/Modal) = you run a sync service + agent on a machine per user; you pay for compute when it’s on and a bit for disk when it’s off. The table below compares them.

## Options comparison

|  | **Stateless, full sync each time** | **Stateless + persisted workspace** | **Fly.io (machine per user/repo)** | **Modal (snapshots)** |
|--|------------------------------------|-------------------------------------|------------------------------------|------------------------|
| **What it is** | Cloud Run (or Lambda); extension sends full workspace in the request body every time. | Same compute, but last workspace + agent memory live in R2/S3; extension sends only *deltas* after the first sync. | One Fly Machine per user/repo; repo on a disk (volume). Machine sleeps when idle, wakes on demand. | Agent runs on Modal; repo (and/or state) stored in a snapshot between runs. You sync at session start or into the snapshot. |
| **DX** | Easiest: reuse existing “workspace-in-JSON” path; no new backend. | New code: workspace store, incremental sync protocol, merge logic. Standard HTTP + storage APIs. | New code: sync server + A2A on Fly; machine lifecycle (create/wake/stop). Good docs and CLI. | New code: Modal app + snapshot usage. Python-native, good for agent code. |
| **Dev velocity** | Fastest to ship: deploy current A2A to Cloud Run, point extension at it. | Medium: need to design and implement store + protocol; then iterate on perf. | Medium: get sync + A2A into one image, learn Fly APIs, add lifecycle. | Medium: port agent to Modal, wire snapshots; different model than “always-on” sync. |
| **UX** | Poor for beta: every conversation = full upload. Slow for anything beyond tiny repos. | Good if we nail it: first sync full, then incremental; “Ready” in a few seconds. Cold start 1–5 s possible. | Good: repo already on disk; sync is incremental by nature. Wake ~1–2 s, then ready. | Good: fast snapshot restore; sync at start can be incremental if we store last state. |
| **Beta suitability** | Only for tiny repos or “demo” usage; not recommended for real beta. | Best fit if we can get “time to ready” low: scales with users, no machines to manage. | Very good: real filesystem, familiar “sync on save” model; need to manage machine count. | Good: pay per run, fast restores; sync story (when/how we fill the snapshot) needs design. |
| **Simplicity to implement** | Simplest: almost nothing new. | Moderate: storage layer + sync protocol + merge. No VMs. | Moderate: same app as today, but deployment + lifecycle (create/stop/cleanup) on Fly. | Moderate: different runtime (Modal), snapshot semantics, possibly “sync then run” per session. |
| **Price** | Very low: pay per request; free tier covers a lot. | Low: compute per request + storage (R2/S3 cheap; a few reads/writes per session). | Low when idle: pay for compute only when machine runs; volume ~\$0.15/GB/mo when stopped. | Low: pay per second of run + snapshot storage; free tier generous. |
| **Scale to demand** | Automatic (serverless). | Automatic (serverless). | Manual/scripted: more users = more machines; can add queue to cap concurrency. | Automatic (Modal scales); concurrency limits if needed. |

### Pros and cons by option

- **Stateless, full sync each time**  
  **Pros:** Easiest to implement and deploy; reuses current design; very cheap; scales automatically.  
  **Cons:** Bad UX for beta — full upload every conversation; only acceptable for tiny repos or demos.

- **Stateless + persisted workspace**  
  **Pros:** Good UX if incremental sync is fast; no VMs; scales automatically; pay per use; fits “no budget” well.  
  **Cons:** More to build (store + protocol); cold start can add 1–5 s; need to validate that “load from storage + apply deltas” is fast enough.

- **Fly.io (machine per user/repo)**  
  **Pros:** Great UX: repo on disk, incremental sync natural; wake time ~1–2 s; no full upload ever; predictable model.  
  **Cons:** Machine lifecycle to implement and operate; you pay for volume even when stopped; scaling = more machines (and possibly a queue).

- **Modal (snapshots)**  
  **Pros:** Fast restores; pay per second; good for bursty beta traffic; Python-friendly.  
  **Cons:** Different mental model (snapshot vs “always there” volume); sync flow (when we write into the snapshot) and optional agent memory need to be designed.

## Two phases

| Phase | Goal | Current plan |
|-------|-----|---------------|
| **Dev / self-test** | Stable hosted URL for extension and CI; you control usage | **GCP Terraform** (Cloud Run A2A, free tier). See [infra-gcp.md](infra-gcp.md) and [infra/README.md](../infra/README.md). |
| **Beta users** | Let others use the product (e.g. VS Code extension) with great UX and minimal cost | Separate track; see investigation path below. |

The GCP setup is **stateless**: no sync in cloud, extension uses **workspace-in-JSON** for hosted. That is fine for occasional self-testing. For beta users, sending the full repo on every conversation is bad UX. We want either **stateless + persisted memory** (if we can make it fast) or **non-stateless** (persistent workspace).

## Investigation path

### 1. Stateless + persisted memory (investigate first)

**Idea:** Keep compute stateless (e.g. Cloud Run / Lambda) but persist **workspace state** and optionally **agentic memory** in storage (R2, S3, or a small DB). At session start we don’t re-upload the full repo; we load last known state from storage and apply **incremental updates** from the client (deltas / changed files only). After the run we write back the updated workspace (and any memory snapshot).

- **Pros:** Scales to demand automatically (serverless). No long-lived VMs. Single code path for “sync” = read from blob + apply deltas.
- **What to investigate:**
  - **Workspace persistence:** Store last workspace snapshot (or file tree + contents) keyed by user/repo in R2/S3 (or Turso/Postgres for small metadata). Protocol: first sync = full upload; subsequent = client sends only changed files (path + content or delete). Server fetches last snapshot, applies diff, runs agent, writes new snapshot. Measure: time to “ready” (fetch + apply) vs. full upload.
  - **Agentic memory:** Persist the “very limited agentic memory” (e.g. summary or structured blob) in the same store or a cheap KV (Upstash, Turso). Load at session start, save at end. Keeps agent context across conversations without keeping a process alive.
- **Cold start:** With stateless, cold start = new instance. Mitigations: keep container image small; consider min instances (e.g. 1) only if traffic justifies it; otherwise accept occasional 1–5 s cold start and ensure the rest of the flow (sync from storage + incremental) is fast so total time-to-ready is good.
- **Outcome:** If we can get “session ready” (load persisted state + apply incremental sync) to be **fast enough** and the protocol is manageable, **deploy stateless** (e.g. Cloud Run + R2, or Lambda + S3/R2). Scale comes for free.

### 2. If stateless + memory isn’t good enough: non-stateless

If persisted workspace + incremental sync is too slow, too complex, or too expensive (e.g. large blobs, many small reads), then use **persistent-but-sleepy** compute so the repo lives on a real filesystem and sync is “push to existing process” (or to a volume that wakes with the process).

- **Model:** One Fly Machine (or Modal app) per user/repo; repo on Fly Volume (or Modal snapshot). Sync on save updates the volume; no full pull each conversation. Scale to demand = spawn more machines as users/repos grow; use queue or limits to cap concurrency if needed.
- **Cold start:** Wake time ~1–2 s (Fly with pre-pulled image). Mitigate with a small image and clear “starting…” UX so the user knows something is happening.
- **Deploy:** Implement sync endpoint + A2A on Fly (or Modal); document machine lifecycle (create on first use, stop after idle, optional cleanup). See “Non-stateless options” below for details.

## Sync: fast and incremental

- **First-time sync:** As fast as possible (e.g. efficient encoding, compression, optional chunking). For stateless, “first time” might mean upload to R2/S3 then server loads from there; for non-stateless, push to the running sync endpoint or the volume.
- **After the first time:** **Incremental sync** is the target: only changed files (or deltas) are sent. Feasibility depends on:
  - **Protocol:** Client tracks last-synced state (e.g. mtime or content hash per path); on sync, sends only modified/added/deleted paths + contents. Server merges into last known state (in blob store or on volume).
  - **Cost:** Storing last snapshot in R2/S3 is cheap; read/write per session is a few requests. For non-stateless, volume already has the tree; incremental = only write changed files.
- **UX:** Progress or “Syncing…” with a clear “Ready” so the user knows when they can start a conversation. Prefer sub-second incremental sync when possible.

## Cold start

- **Why it matters:** First request after idle (or first user) hits a cold instance. If that’s 5–10 s, the user may think the product is broken. We want either fast cold start or clear feedback (“Starting your environment…”).
- **Stateless (Cloud Run / Lambda):** Cold start = container init. Reduce image size (single stage, minimal deps), avoid heavy import-time work. Consider `min_instances = 1` only if you have steady traffic and budget; otherwise accept occasional cold and optimise the rest (load from storage + incremental sync) so total time-to-ready is acceptable.
- **Non-stateless (Fly / Modal):** “Cold” = machine wake or snapshot restore. Fly ~1–2 s with pre-pulled image; Modal snapshot restore is fast. Show a short “Waking up…” so the user isn’t left staring at a spinner with no explanation.

## Scale to demand

- **Stateless:** Cloud Run / Lambda scale out automatically with request count. No extra work beyond configuring concurrency and limits.
- **Non-stateless:** Scale by provisioning more machines (Fly) or more app instances (Modal) as users/repos grow. Use a queue or per-user concurrency limits if you need to cap cost while still serving demand.

## Non-stateless options (if we go that route)

Rough fit for your profile:

- **Agent**: 1–5 min per run, mostly LLM wait; **no arbitrary code execution** (only your tools). So you don’t need a heavy sandbox, just a process that can call APIs and hold session state.
- **State**: Code repo synced from client (e.g. on save). Persist between conversations so we don’t re-sync the whole repo each time.

### Fly.io Machines (sleep to zero)

- **Model**: One Fly Machine per user (or per repo). Repo on **Fly Volume**. Sync on save updates the volume; no full pull each conversation.
- **Billing**: Compute when running; volume ~\$0.15/GB/month when stopped.
- **Wake time**: ~1–2 s with pre-pulled image.
- **Complexity**: Machine lifecycle (create on first use, stop after idle, optional cleanup). Fly API is scriptable.

### Modal (snapshots, pay-per-second)

- **Model**: Agent as Modal app; **snapshots** persist filesystem (repo) between runs. Cold start after snapshot restore is fast.
- **Billing**: Per second of execution; generous free tier. Snapshot storage on top.
- **Fit**: Sync at session start from client into snapshot, then run; or keep a long-lived volume-like workflow if Modal supports it.

## Cost levers (when we care)

Once UX is solid, we can tune cost:

1. **Serialize or queue sessions** — Limit concurrency to keep compute flat.
2. **Sleep to zero** — With Fly (or similar), machines stop when idle.
3. **Volume / storage retention** — Prune or archive old/inactive repos.
4. **Usage caps** — Per-user limits (e.g. N conversations per day, max repo size); generous but capped.

## Investigate how and deploy

1. **Stateless + persisted memory**
   - Implement a **workspace store** (e.g. R2/S3 or Turso): key = `user_id` + `repo_id` (or workspace id). Value = last known file tree + contents (or compressed snapshot).
   - Define **incremental sync protocol**: client sends `{ added: [...], modified: [...], deleted: [...] }` with path + content (or hash) per file. Server loads last snapshot, applies diff, runs agent, writes new snapshot.
   - Persist **agentic memory** in the same store or a small KV; load at session start, save at end.
   - **Measure:** End-to-end time from “user hits go” to “agent has workspace and memory” (including cold start if any). If this is acceptable (e.g. under 3–5 s for incremental case), **deploy stateless** (Cloud Run + R2, or Lambda + S3/R2). Extension points at this backend for beta.
2. **If stateless path is too slow or complex**
   - **Deploy non-stateless:** Fly (or Modal) with one machine/app per user/repo, sync endpoint + A2A, repo on volume (or snapshot). Document lifecycle (provision, idle timeout, cleanup). Extension points at Fly/Modal beta URL.
3. **Either way**
   - Keep **GCP Terraform for dev**: unchanged; workspace-in-JSON for your own testing.
   - Beta URL is configurable in the extension (`refactorAgent.a2aBaseUrl`, `refactorAgent.syncUrl`) so dev uses GCP and beta users use the chosen beta backend.
   - Add clear **“Starting…” / “Syncing…” / “Ready”** UX so cold start and sync feel intentional, not broken.

## Same infra for dev and beta: what we have vs what it would take

**Can we use the same infra for dev and for clients?** Yes. Same Cloud Run (and same image) can serve both. For dev you keep using workspace-in-JSON and optional local sync. For beta clients you add a **workspace store** (R2 or GCS) and a **sync API** that reads/writes that store; A2A then loads workspace from the store when the client sends a `workspace_id` (instead of only `use_replica` with local disk or inline workspace). One deployment, two usage modes.

**Do we have "client envs" or onboarding today?** No. The current PR (e.g. commit `7b1f92d`) does **not** implement any of: creating "client envs" on demand; onboarding flow or workspace identity; persisted workspace storage; sync in the cloud (sync code exists but writes to a single local `REPLICA_DIR` and is not deployed on Cloud Run; no storage backend).

**What the current PR has (commit 7b1f92d):**

| Piece | Status |
|-------|--------|
| Terraform | Cloud Run (A2A only), Artifact Registry, Secret Manager, Firestore, APIs; EU region. |
| Cloud Run | Single service; runs A2A via `entrypoint-cloudrun.sh`; no sync in cloud. |
| A2A | Reads `PORT` from env; supports `use_replica` (reads from `REPLICA_DIR`) or inline `workspace` in request body. |
| Sync (in repo) | `sync/app.py` + `sync/server.py`: WebSocket + POST `/sync/workspace`; writes to one local `REPLICA_DIR`. No per-client keying, no object storage. |
| Dev usage | Extension points at Cloud Run URL; uses workspace-in-JSON (no sync). |

**What it would take to support beta (stateless + persisted workspace) on top of this:**

| Addition | Purpose |
|----------|--------|
| **Workspace store** | GCS bucket (same project) or R2; key = `workspace_id` (or `user_id` + `repo_id`). Value = last snapshot (file tree + contents). Terraform: bucket + IAM for Cloud Run. |
| **Workspace identity** | Extension sends `workspace_id` (e.g. derived from repo path + user, or issued by a tiny backend). First sync with that id creates/overwrites the blob; no separate "create env" API. |
| **Sync API in cloud** | Deploy sync in the same (or a second) Cloud Run service. Writes/reads from store instead of `REPLICA_DIR`; applies full or **delta** (added/modified/deleted), persists new snapshot. |
| **Incremental sync protocol** | Client tracks last-synced state; sends full on first sync, then only changes. Server merges delta into last snapshot and persists. |
| **A2A: load from store** | When request includes `workspace_id`, A2A fetches snapshot from store, materialises into a temp dir, runs agent, optionally writes back. Only the source of `workspace_dir` changes. |
| **Auth (optional)** | API key or similar per beta user so `workspace_id` is scoped; minimal (e.g. one shared beta key) at first. |

So: **no "create env" API** — with stateless + store, "onboarding" is implicit (first sync with a `workspace_id` creates the blob). The extra work vs this PR is: storage + sync API backed by store + delta protocol + A2A branch to load by `workspace_id`.

## References

- Current infra plan: [.cursor/plans/gcp_terraform_dev_infra_4e86f366.plan.md](../.cursor/plans/gcp_terraform_dev_infra_4e86f366.plan.md) (GCP Terraform dev infra).
- Sync and workspace: [sync-service.md](sync-service.md), [a2a-server.md](a2a-server.md). Executor supports both `use_replica` (sync) and inline workspace.
