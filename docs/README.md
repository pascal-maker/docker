---
title: Documentation
---

# Documentation

Documentation for the refactor-agent: architecture, setup, integrations, infrastructure, and contributing.

## Getting started

- [Getting started](getting-started.md) — run locally (Docker) or use the extension / Cursor bridge.

## Architecture and integrations

- [Architecture](architecture.md) — unified orchestrator, two surfaces (Dev UI and A2A), shared core.
- [Integrations (APIs)](integrations.md) — entry points: A2A server, sync service, dashboard ingest, MCP server.
- [Troubleshooting](troubleshooting.md) — common issues and where to look.

## Infrastructure and deployment

- [Infrastructure](infra/README.md) — GCP, Terraform, releasing, dev-loop tasks, beta pricing.
  - [GCP (Terraform, EU)](infra/gcp.md)
  - [Releasing](infra/releasing.md)
  - [Dev-loop tasks](infra/dev-loop-tasks.md)
  - [Beta pricing](infra/beta-pricing.md)

## Clients and services

- [A2A server (HTTP)](a2a-server.md) — agent-to-agent protocol, endpoints, request formats.
- [Sync service](sync-service.md) — workspace sync over WebSocket; server and client.
- [Docker deployment](docker-deployment.md) — run sync + A2A in one container; sync client usage.
- [Chat UI (Chainlit)](chat-ui.md) — dev UI: Ask / Auto / Plan modes, persistence, auth.
- [Cursor bridge](cursor-bridge.md) — use the A2A agent from Cursor via A2A–MCP bridge.
- [MCP server (stdio)](mcp-server.md) — stdio MCP server, `rename_symbol` tool, config.
- [VS Code extension](vscode-extension/README.md) — overview, install, debugging.

## Contributing

- [Coding standards](coding/README.md) — repo rules summary and link to CLAUDE.md; [audit](coding/audit.md).
- [CI refactor check](ci-refactor-check.md) — presets, config, auto-apply, secrets.
- [Refactor issues dashboard](dashboard.md) — ingestion API, SQLite, React UI, run instructions.
- [Testing](testing/README.md) — refactor schedule, playgrounds, manual and automated testing.
- [Refactor schedule](refactor-schedule/README.md) — pipeline, manifold, data model, PoC steps.

## Reference and future work

- [Resources](resources.md) — courses, A2A, ts-morph, agent patterns, GCP, related projects.
- [Agentic patterns](agentic-patterns.md) — ReAct, plan-then-execute, refactor schedule.
- [Ideas and roadmap](ideas/README.md) — vision, validation feedback, handoff prompts, deployment roadmap.
