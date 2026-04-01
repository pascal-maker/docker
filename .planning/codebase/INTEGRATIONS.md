# External Integrations

**Analysis Date:** 2026-04-01

## APIs & External Services

**Large Language Models:**
- Anthropic Claude API - Core AI agent intelligence
  - SDK: `anthropic>=0.78.0,<0.80.0`
  - Auth: `ANTHROPIC_API_KEY` env var
  - Client: `AsyncAnthropic` from `refactor_agent.llm_client`
  - Proxy support: Requests routed through `LITELLM_PROXY_URL` when set (LiteLLM caching/load-balancing)
  - Proxy auth: `LITELLM_MASTER_KEY` env var (used instead of ANTHROPIC_API_KEY when set)

**GitHub Integration:**
- GitHub OAuth 2.0 - User authentication and authorization
  - Auth endpoints: `https://github.com/login/oauth/access_token`, `https://api.github.com/user`
  - SDK: None (direct HTTP via urllib)
  - Configuration:
    - `GITHUB_OAUTH_CLIENT_ID` - OAuth app client ID
    - `GITHUB_OAUTH_CLIENT_SECRET` - OAuth app secret
    - `GITHUB_OAUTH_REDIRECT_URI` - Post-login redirect URL
  - Token validation: Via `refactor_agent.auth.github_auth.GitHubTokenValidator` with 5-minute TTL cache
  - Implementation: `refactor_agent.auth.github_auth` and `refactor_agent.auth.oauth`

**LLM Observability & Prompts:**
- Langfuse - LLM tracing, prompt management, evaluations
  - SDK: `langfuse` (imported as `get_client()`)
  - Configuration:
    - `LANGFUSE_PUBLIC_KEY` - Public key for client init
    - `LANGFUSE_SECRET_KEY` - Secret key for auth
    - `LANGFUSE_BASE_URL` - Custom base URL (optional)
  - Optional: When not configured (`LANGFUSE_PUBLIC_KEY` unset), prompts load from local `prompts/` directory
  - Integration: `refactor_agent.observability.langfuse_config` handles initialization and prompt/config retrieval
  - PydanticAI Integration: `Agent.instrument_all()` hooks all agents for automatic tracing

## Data Storage

**Databases:**
- Google Cloud Firestore
  - Type: NoSQL document database (Google Cloud)
  - Purpose: User records, audit logs, rate limiting, repo access
  - Client: `google.cloud.firestore.Client`
  - Configuration:
    - `GOOGLE_CLOUD_PROJECT` or `GCLOUD_PROJECT` - GCP project ID
    - Authentication: Via Google Cloud Application Default Credentials (ADC)
  - Collections:
    - `users` - User records (GitHub ID → UserRecord)
    - `installation_users` - Installation-specific user mappings
    - `audit_logs` - Action audit trail (AuditLogEntry)
    - `usage_windows` - Rate limit tracking
  - Optional: If not configured, UserStore operates in no-op mode (`is_available()` returns False)
  - Implementation: `refactor_agent.auth.user_store.UserStore` provides high-level CRUD and rate limiting

**Alternative/Local Storage:**
- SQLite3 - Local dashboard storage (optional, used in playground/dashboard)
  - Purpose: Org/repo metadata caching for dashboard views
  - Implementation: `refactor_agent.dashboard.storage` with cursor-based CRUD
  - Note: Not part of primary data model; used for local tool operations

**File Storage:**
- Local filesystem - Replica synchronization
  - Purpose: Workspace file caching during sync protocol
  - Path: `REPLICA_DIR` env var or default
  - Implementation: `refactor_agent.sync.*` modules

**Caching:**
- In-process TTL caches:
  - GitHub token validator cache (5 min TTL): `refactor_agent.auth.github_auth.GitHubTokenValidator`
  - Ban/rate-limit cache (30 sec TTL): `refactor_agent.auth.user_store.UserStore`

## Authentication & Identity

**Auth Provider:**
- GitHub OAuth 2.0 (custom implementation, not third-party SDK)
  - Protocol: Standard OAuth 2.0 code exchange
  - Token validation: Direct GitHub API calls
  - Scope/permissions: Implicit in GitHub app configuration (not enforced client-side)

**Local Development Auth:**
- `A2A_API_KEY` env var - Bypass GitHub validation for local testing
  - Used in: `refactor_agent.backend.app` and `refactor_agent.sync.app`
  - When set: Allows requests with `Authorization: Bearer <A2A_API_KEY>` without GitHub validation

**Token Management:**
- Tokens passed via `Authorization: Bearer <token>` header
- Tokens cached in-process with TTL (5 min)
- Token validation performed on WebSocket and HTTP requests
- User record (with GitHub ID, login, repos) cached in request scope as `state["user_record"]`

## Monitoring & Observability

**Error Tracking:**
- Sentry - Error/exception monitoring and alerts
  - SDK: `sentry-sdk>=2.0.0`
  - Configuration: `SENTRY_DSN` env var (optional; errors sent only if set)
  - Integration: Error-level logs sent via LoggingIntegration
  - Traces: Disabled (`traces_sample_rate=0.0`)
  - Implementation: Lazy init in `refactor_agent._log_config.configure_logging()`

**Logs:**
- Structured JSON logging to stderr
  - Framework: `structlog>=24.1.0` with stdlib integration
  - Renderer: JSONRenderer
  - Time format: ISO 8601 UTC
  - Module-level loggers defined per package: `<package>/logger.py` exports `logger`
  - Package loggers initialized via: `refactor_agent._log_config.get_logger("refactor_agent.<package>")`
  - Context: Automatic merging of contextvars, log level, logger name, exceptions

**LLM Tracing:**
- Langfuse (optional)
  - When configured: All PydanticAI agents automatically instrumented
  - When not configured: No tracing overhead

## CI/CD & Deployment

**Hosting:**
- Google Cloud Run - Primary deployment target
  - Container: Single service with combined A2A + sync app
  - Entry point: `refactor_agent.backend.app.build_combined_app()`
  - WebSocket support: Native via Starlette/Uvicorn

**Cloud Functions:**
- Workspace: `functions/` directory with per-function subdirectories
- Functions: `auth_callback`, `auth_register_device`, `email_notify`, `github_webhook`, `usage_digest`
- Shared models: `functions/shared/` with Pydantic BaseModel definitions
- Entry point convention: Each function has `src/` with handler (not inspected; follows Cloud Functions framework)

**CI Pipeline:**
- GitHub Actions
- Jobs (per codebase docs):
  - Python: format (ruff), lint (ruff), typecheck (mypy + pyright), test (pytest)
  - TypeScript: format (Prettier), lint (oxlint), typecheck (tsc)
- Build orchestration: Nx for affected/changed packages
- Configuration: Not inspected (likely in `.github/workflows/`)

## Environment Configuration

**Required env vars (by feature):**

**LLM & Agents:**
- `ANTHROPIC_API_KEY` (required unless using proxy)
- `LITELLM_PROXY_URL` (optional; enables proxy mode)
- `LITELLM_MASTER_KEY` (optional; required if using proxy without fallback)

**Observability:**
- `SENTRY_DSN` (optional)
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` (optional; only for Langfuse integration)

**Authentication:**
- `GITHUB_OAUTH_CLIENT_ID` (required if using GitHub auth)
- `GITHUB_OAUTH_CLIENT_SECRET` (required if using GitHub auth)
- `GITHUB_OAUTH_REDIRECT_URI` (required if using GitHub auth)
- `A2A_API_KEY` (optional; for local dev bypass)

**Data Storage:**
- `GOOGLE_CLOUD_PROJECT` or `GCLOUD_PROJECT` (required if using Firestore)

**Sync/Workspace:**
- `REPLICA_DIR` (optional; defaults to `DEFAULT_REPLICA_DIR`)
- `REFACTOR_AGENT_A2A_URL` (optional; for remote A2A execution)
- `REFACTOR_AGENT_PROMPTS_DIR` (optional; defaults to `prompts/`)

**Secrets location:**
- Development: `.env` file (loaded by python-dotenv at app startup)
- Production: Google Cloud Secret Manager or Cloud Run environment secrets
- Never committed to git (`.env` in `.gitignore`)

## Webhooks & Callbacks

**Incoming:**
- GitHub OAuth callback - `POST /auth/callback` (standard OAuth 2.0 redirect)
  - Handler: `refactor_agent.auth.oauth.exchange_code_for_token()`

- A2A Task Callbacks - WebSocket at `/` (custom protocol)
  - Bidirectional agent execution updates
  - Handler: `refactor_agent.sync.app.websocket_sync()` and `refactor_agent.a2a.server`

- Workspace Sync - `POST /sync/workspace` (HTTP)
  - Bootstrap file upload endpoint
  - Handler: `refactor_agent.sync.app.http_sync_workspace()`

- Agent Card - `/.well-known/agent-card.json` (public endpoint)
  - Standard agent metadata (OpenAPI spec, capabilities)
  - Handler: Built by A2A framework

**Outgoing:**
- GitHub API calls (user info, repo metadata) - Indirect via user interactions
- Anthropic API calls - LLM inference requests (indirect; routed through optional LiteLLM proxy)
- Langfuse API calls - Trace submission (when configured)
- Sentry API calls - Error reporting (when SENTRY_DSN set)

## A2A (Agent-to-Agent) Integration

**Framework:**
- a2a-sdk>=0.3.0 - CloudEvents-based agent execution
  - Protocol: CloudEvents format over WebSocket/HTTP
  - Server: `a2a.server.apps.A2AStarletteApplication`
  - Task execution: `a2a.server.agent_execution.AgentExecutor`
  - Task storage: In-memory via `a2a.server.tasks.InMemoryTaskStore`

**Custom Bridge:**
- `refactor_agent.a2a.bridge` - Maps A2A CloudEvents to PydanticAI agents
  - Request handling: Custom DefaultRequestHandler override
  - Result aggregation: Wraps A2A ResultAggregator for streaming
  - Error mapping: Converts internal errors to A2A ServerError

**MCP (Model Context Protocol):**
- fastmcp>=2.14.0 - Tool/resource definitions for Claude
  - Purpose: Exposes refactor tools to Claude models
  - Implementation: Tool registrations in `refactor_agent.agent.tools`

---

*Integration audit: 2026-04-01*
