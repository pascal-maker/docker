# Refactor Agent (VS Code Extension)

Standalone extension to rename Python symbols across your workspace via the A2A refactor server. No Copilot Chat or MCP — use the **Refactor Agent** sidebar panel and status bar.

## Prerequisites

1. **Sync service** — Push workspace to the server (required for `use_replica`).
   - Start: `uv run python -m refactor_agent.sync` (port 8765).
   - Or use the same host as A2A if running in Docker.

2. **A2A server** — Run the refactor backend.
   - Local: `uv run python scripts/a2a/run_ast_refactor_a2a.py` (port 9999).
   - Set `REPLICA_DIR` to the same path as the sync server (e.g. `/workspace` in Docker).

3. **API key (optional)** — For a hosted A2A endpoint, set **Refactor Agent: Api Key** in settings.

## Setup

1. Install the extension (from VSIX or Marketplace).
2. Open a workspace folder with Python files.
3. In settings, set **Refactor Agent: A2a Base Url** (default `http://localhost:9999`) and **Refactor Agent: Sync Url** (default `http://localhost:8765`).
4. Open the **Refactor Agent** view from the activity bar (sidebar icon).

## Usage

- Click the **Refactor Agent** icon in the activity bar to open the panel.
- Enter **Old symbol name** and **New symbol name**, then click **Rename**.
- The extension pushes the workspace to the sync service, then sends the refactor request to A2A with `use_replica: true`. Progress and results appear in the message list.
- **Sync status**: The status bar at the bottom shows **Sync OK** (green) or **Sync error** (red) after a sync attempt; the panel also shows sync status at the top.
- If the agent asks for input (e.g. name collision), the panel switches to a reply form; enter your answer (e.g. `yes`, `no`, or a new name) and click **Send reply**. When the refactor completes, the form returns to the rename fields.
- On success, file edits are applied automatically.

## Beta

This is a beta release. The extension is standalone and does not depend on Copilot or any other chat.
