# A2A server (HTTP)

A2A surface for agent-to-agent refactor tasks; shares the same [orchestrator](../guides/architecture.md) as the Chat UI. Human-in-the-loop (e.g. name collision) uses `input_required` and resumption.

Start the server (default port 9999):

```bash
uv run python scripts/run_ast_refactor_a2a.py
```

Custom port:

```bash
uv run python scripts/run_ast_refactor_a2a.py 8080
```

## Endpoints

- **Agent Card:** `GET http://localhost:9999/.well-known/agent-card.json` — discover skills and capabilities. The card exposes one generic **refactor** skill (no enumeration of operations).
- **Refactor task:** `POST http://localhost:9999` — send an A2A `message/send` JSON-RPC request. Backward compatible: same JSON shapes (e.g. `old_name`, `new_name`, `source` or `workspace`) are accepted.

## Request formats

### Single-file

```json
{"source": "<python source>", "old_name": "foo", "new_name": "bar", "path": "src/foo.py"}
```

`scope_node` and `path` are optional. The server returns the result in the task status message and in a **rename-result artifact** with `modified_source` and `path`.

### Workspace (full impact)

```json
{"old_name": "greet", "new_name": "greet_user", "workspace": [{"path": "a.py", "source": "..."}, {"path": "b.py", "source": "..."}]}
```

The agent finds which files reference the symbol and returns one artifact per impacted file. The client applies every artifact.

### Explicit files

```json
{"old_name": "greet", "new_name": "greet_user", "files": [{"path": "a.py", "source": "..."}, {"path": "b.py", "source": "..."}]}
```

Refactors a fixed list. Apply each artifact's `modified_source` to its `path`.

### Use replica (sync service)

When the client has pushed workspace to the **sync service** (see [sync-service.md](sync-service.md)), send:

```json
{"old_name": "greet", "new_name": "greet_user", "use_replica": true}
```

The server uses `REPLICA_DIR` as the workspace and does not read workspace from the request body. The sync server must be running and the client must have pushed files (WebSocket or HTTP upload) before calling A2A with `use_replica: true`.

## Limitations

The A2A refactor agent is stateless and has no filesystem access. It only sees the JSON request body. For full cross-file impact, the client must send a `workspace` or `files` array with all relevant file contents. A local relay (e.g. a custom MCP bridge with repo access) can gather the workspace and push it to the agent.

## Testing

With the server running, in another terminal:

```bash
uv run python scripts/test_a2a_rename.py
```

This GETs the agent card and POSTs a rename task. Optional: pass a base URL, e.g. `uv run python scripts/test_a2a_rename.py http://localhost:8080`.

## Human-in-the-loop (collision detection)

To trigger the "pause and ask" flow, send a rename that would cause a name collision (e.g. rename `greet` to `main` when `main` already exists). The agent returns `input_required`; you send a second message: **yes** to force, **no** to cancel, or a **new name** to use instead.

### Using the test script

```bash
uv run python scripts/test_a2a_collision.py
```

The script sends a rename that would shadow `main`, then sends `yes` to confirm (pass `--no` to cancel instead). You should see `input-required` status, then the confirmed rename result.

### Manual flow with curl

1. Send the collision-producing rename. The response will have `"state": "input-required"` in `result.status`.

2. From the response, take `result.id` (taskId) and `result.contextId`. Send a second `message/send`:

```bash
curl -s -X POST http://localhost:9999 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "message/send",
    "params": {
      "message": {
        "kind": "message",
        "role": "user",
        "messageId": "m2",
        "contextId": "<contextId from step 1>",
        "taskId": "<taskId from step 1>",
        "parts": [{"kind": "text", "text": "yes"}]
      }
    }
  }'
```

With `"yes"` you get the rename result; with `"no"` you get "Rename canceled."
