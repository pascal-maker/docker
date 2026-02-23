# Current deployment state (as of Feb 2025)

What is deployed today vs what needs to change for alpha.

See [architecture-schematic.md](architecture-schematic.md) for the full component map and target architecture.

---

## Deployed today

| Component | Local / Docker | Cloud Run |
|-----------|---------------|-----------|
| **Chainlit** | In-process orchestrator against `playground/` | Not deployed (optional; would call A2A but no auth → 401) |
| **A2A** | Port 9999 | Single Cloud Run service, GitHub OAuth enforced |
| **Sync** | Port 8765 (same container as A2A) | **Not deployed** |

## What works

- **Extension → local A2A + sync**: Full flow (sync → clone → overlay → refactor → results).
- **A2A auth on Cloud Run**: GitHub OAuth enforced. Unauthenticated POST returns 401. Verified by CI security tests.
- **Chainlit local**: Direct orchestrator call against `playground/`.

## What does not work (yet)

- **Extension → hosted A2A**: Sync is not deployed on Cloud Run. Extension requires sync → hosted extension flow broken.
- **Hosted Chainlit → A2A**: Chainlit does not send auth when calling A2A → 401.

## Next step: deploy sync for alpha

Deploy sync + A2A as a **single combined ASGI app** on Cloud Run (same service, same port, shared `REPLICA_DIR`). See [architecture-schematic.md](architecture-schematic.md) section 5 for the target diagram.

---

## Gaps to close

1. **Deploy sync on Cloud Run** — Combined ASGI app routing sync and A2A on one port. Ephemeral `REPLICA_DIR` with TTL.
2. **Remove workspace-in-JSON** — Executor still supports inline `workspace` as legacy. Extension does not use it. Remove to enforce sync as the only path.
3. **Hosted Chainlit auth** — Low priority for now. Chainlit is dev/test only; scoped to local `make ui` against playgrounds. Hosted Chainlit is a nice-to-have for smoke-testing; not required for alpha.
