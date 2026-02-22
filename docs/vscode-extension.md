# VS Code extension

For VS Code users, the **Refactor Agent** extension is a **standalone** sidebar panel. It speaks A2A HTTP directly; no MCP or Copilot Chat.

## Flow

1. User opens a workspace and opens the **Refactor Agent** view from the activity bar.
2. User enters old and new symbol names and clicks **Rename**.
3. The extension gathers Python files and pushes them to the **sync service** (HTTP POST to `/sync/workspace`).
4. The extension sends a refactor request to the **A2A server** with `use_replica: true` (no inline workspace in the body).
5. If the server returns `input_required` (e.g. name collision), the panel shows a reply form; the user enters a reply and the extension sends a follow-up `message/send` with the same `taskId`/`contextId`.
6. On completion, the extension applies each `rename-result` artifact (`modified_source` to `path`) in the workspace.

## UI

- **Activity bar**: Refactor Agent icon opens the sidebar view.
- **Sidebar panel**: Webview with Old name / New name inputs, Rename button, sync status (green/red), and message list. When the agent needs input, a reply form is shown.
- **Status bar**: Sync status (green = OK, red = error) at the bottom of the window so you can see sync health at a glance.

## Configuration

- **A2A base URL** — e.g. `http://localhost:9999` (local) or a hosted URL.
- **Sync URL** — e.g. `http://localhost:8765` for HTTP (POST `/sync/workspace`).
- **API key** (optional) — For hosted backends that accept BYOK; sent as `Authorization: Bearer <key>`.

See the extension README in `vscode-extension/README.md` for install and usage.

## Relation to Cursor/MCP

- **Cursor:** Use the [A2A–MCP bridge](cursor-bridge.md) and register the agent; Cursor then uses MCP tools to send tasks.
- **VS Code:** Use this extension; it has its own sidebar panel and speaks A2A HTTP directly. No MCP or Chat required.
