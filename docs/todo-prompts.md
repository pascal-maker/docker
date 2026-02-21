# Hosting & code extension

## 2. Handoff for planning agent (remaining phases)

Use this with a **planning agent** to continue the LibCST + MCP + A2A work:

---

**Context:** This repo implements an AST refactor agent (LibCST engine, PydanticAI agent, MCP and A2A wrappers). The plan is **`.cursor/plans/libcst_+_mcp_+_a2a_wrappers_e005fdf7.plan.md`** (or in your plans list as “LibCST + MCP + A2A wrappers”). A more detailed Phase 2 implementation plan is in **`.cursor/plans/phase_2_mcp_and_a2a_4260c831.plan.md`**.

**Current state:**
- **Phase 1 done:** LibCST engine in `src/document_structuring_agent/ast_refactor/engine.py`; agent in `agent.py`; `run_ast_refactor()` uses LibCST; tests in `tests/test_ast_refactor/test_engine.py` pass.
- **Phase 2 done:** MCP wrapper (FastMCP, `rename_symbol` tool, stdio, script + shell wrapper in Cursor `mcp.json`); A2A wrapper (local HTTP server, one refactor task type, Agent Card, executor, run script). Tests in `tests/test_ast_refactor/test_mcp_server.py` and `test_a2a_executor.py`. README documents how to start both servers and how clients reach them.
- **Phase 3 (hosting) and Phase 4 (VS Code extension)** are still placeholders in the plan and not implemented.

**What to do:**
1. **Open and update the plan** (the LibCST + MCP + A2A plan): mark Phase 2 complete and set the next steps to **Phase 3 (hosting)** and **Phase 4 (VS Code extension)** as specified there.
2. **Produce an implementation plan** for the remaining work only: Phase 3 (hosting the refactor service; what “hosting” means in that plan — e.g. deploy MCP/A2A or API, auth, etc.) and Phase 4 (VS Code extension; how it talks to the backend, UI for rename/extract, etc.). Do not implement yet; output a clear, phased plan with constraints from the original plan (time-to-value, strict typing, no edits to the plan file except to mark Phase 2 done and to set “next: Phase 3 / Phase 4”).
3. Keep the same constraints as in the existing plan; reference **CLAUDE.md**, **vision.md**, and the current code (engine, agent, MCP server, A2A server, README) as needed.

**Relevant files:** The plan file(s) above, `src/document_structuring_agent/ast_refactor/` (engine, agent, mcp_server, a2a_executor, a2a_server), `scripts/run_ast_refactor_mcp.py`, `scripts/run_ast_refactor_a2a.py`, `README.md`, `pyproject.toml`, `CLAUDE.md`, `vision.md`.

# Planning prompt: Custom MCP bridge for AST refactor agent

Copy the prompt below and pass it to a Cursor (or other) planning agent to implement the custom bridge.

---

## Prompt (copy from here)

Implement a **custom local MCP bridge** that sits between the coding agent (Cursor/Claude Code) and the AST refactor A2A agent in this repo. Replace reliance on the generic [GongRzhe A2A-MCP-Server](https://github.com/GongRzhe/A2A-MCP-Server) with our own bridge that has **repo awareness** so the refactor agent always receives up-to-date workspace context and refactors apply to all impacted files.

### Goals

1. **Local MCP server** the user runs (e.g. configured in Cursor’s MCP settings). It has **filesystem / workspace access** that the remote A2A refactor agent does not have.
2. **Bridge behavior:** When the coding agent asks for a rename (or other refactor), the bridge:
   - Gathers **current repo context** (e.g. all relevant Python files under a root, or files that reference the symbol).
   - Builds a **workspace** payload: `[{ path, source }, ...]` with up-to-date file contents.
   - Sends one request to the **AST refactor A2A agent** (this repo’s server) with that workspace and `old_name` / `new_name`.
   - Receives **task result** (artifacts: one per impacted file, each with `path` and `modified_source`).
   - **Applies** each artifact by writing `modified_source` to the corresponding `path` on disk (or returns structured result so the coding agent can apply).
3. **“Diffs” / up to date:** The bridge always sends **current file contents** when building the workspace, so the refactor agent sees the latest state. No need for literal diff format — we use the existing A2A **workspace** format (full source per file).
4. **Install / setup:** The bridge is the thing users install and configure once (e.g. in `.cursor/mcp.json` or Cursor’s MCP UI). It connects to the refactor agent (local or remote URL). Users do not need to understand A2A.

### Technical context (this repo)

- **A2A refactor server:** `uv run python scripts/run_ast_refactor_a2a.py` (default `http://localhost:9999`). It already supports:
  - **Workspace format:** POST body `{ "old_name": "...", "new_name": "...", "workspace": [ { "path": "a.py", "source": "..." }, ... ] }`. The agent returns one **rename-result** artifact per file that references the symbol; each artifact has `path` and `modified_source`.
  - **Bridge compatibility:** The server’s middleware already maps `tasks/send` → `message/send` and `tasks/getResult` → task result (see `scripts/run_ast_refactor_a2a.py`). So the bridge can speak A2A JSON-RPC to this server.
- **Limitation today:** The A2A agent is stateless and has no filesystem access. It only sees the request body. If the client sends a single file, it can only return one artifact. Full impact requires the **client** to send a workspace. Our bridge is that client — with repo access, it builds and sends the workspace.

### Requirements for the bridge

- **MCP tools:** Expose at least one tool the coding agent can call for “rename symbol with full repo impact”, e.g. `rename_symbol(old_name, new_name, scope_node?, root_dir?)`. The bridge resolves `root_dir` (default: workspace root), discovers Python files (e.g. `**/*.py` under root), reads their contents, calls the A2A agent with `workspace: [{ path, source }, ...]`, then applies every returned artifact to disk.
- **Config:** Refactor agent URL (e.g. `http://localhost:9999`) should be configurable (env var or MCP server config) so the same bridge works against a local or remote refactor server.
- **Protocol:** Bridge talks to the refactor server via HTTP (A2A JSON-RPC). Use the same request/response shape as in `scripts/run_ast_refactor_a2a.py` and `scripts/call_a2a_agent.py` (or the test scripts) so the existing server works unchanged.
- **Apply step:** After `get_task_result`, parse artifacts; for each artifact that has `path` and `modified_source`, write `modified_source` to that path (relative to workspace root if needed). Return a summary to the coding agent (e.g. “Renamed in 3 files: a.py, b.py, c.py”).

### Out of scope for this task

- Changing the A2A refactor server’s API or behavior.
- Supporting non-rename refactors unless trivial to add later.
- Auth to the refactor agent (assume local or trusted network for now).

### Deliverables

- New package or script(s) in this repo that run the MCP bridge (e.g. `scripts/run_refactor_bridge.py` or a `bridge/` package).
- README or docs update describing how to install and configure the bridge in Cursor (and that it replaces the generic a2a-mcp-server for refactor use).
- Optional: `.cursor/mcp.json` example that points to this bridge instead of `uvx a2a-mcp-server`.

---

## End of prompt
