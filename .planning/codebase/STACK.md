# Technology Stack

**Analysis Date:** 2026-04-01

## Languages

**Primary:**
- Python 3.12 - Backend services, CLI tools, functions
- TypeScript 5.9 - Frontend applications, VSCode extension, shared packages
- JavaScript - Monorepo tooling and scripts

**Secondary:**
- YAML - Configuration files, prompts
- SQL - Database operations (Firestore, SQLite)

## Runtime

**Environment:**
- Python 3.12+ (enforced via `requires-python = ">=3.12"`)
- Node.js 24+ (enforced via `engines.node` in package.json)

**Package Managers:**
- `uv` (Python build backend via `uv_build`) - Fast Python package installer/manager
- `pnpm` (TypeScript) - Strict pnpm workspace at root with `pnpm-lock.yaml`
  - Lockfile: Present and committed
  - Configured with security overrides for minimatch and http-proxy-agent

## Frameworks

**Backend:**
- FastAPI/Starlette 0.38.0+ - ASGI web framework for HTTP/WebSocket
- PydanticAI 1.59.0+ - Agentic AI framework for Claude agents
- Uvicorn 0.32.0+ - ASGI server
- Chainlit - Frontend UI for agent interaction
- WebSockets 14.0+ - WebSocket protocol support

**Frontend:**
- React 19.2.4 - UI framework (dashboard, site)
- React Router 7.0.0 - Client-side routing
- Vite 7.3.1 - Build tool and dev server
- TailwindCSS 4.2.1 - Utility CSS framework
- Tailwind PostCSS - PostCSS integration for TailwindCSS

**VSCode Extension:**
- VSCode SDK 1.90.0+ - Extension API

**Testing:**
- pytest - Python test runner
- pytest-asyncio - Async test support (asyncio_mode = auto)
- Vitest (TypeScript) - Test runner for TS packages

**Build/Dev:**
- Ruff - Python linter and formatter
- mypy - Static type checker (strict mode)
- Pyright - Alternative static type checker (standard mode)
- ESLint (oxlint) - TypeScript linting
- Prettier 3.3.3 - Code formatter (TS/TSX/CSS)
- TypeScript compiler - Type checking for TS
- Nx 22.5.3 - Monorepo task orchestration
- pnpm workspaces - Monorepo package management

## Key Dependencies

**Critical:**
- pydantic>=2.0.0, pydantic-settings>=2.0.0, pydantic-ai>=1.59.0 - Data validation and AI framework
- anthropic>=0.78.0,<0.80.0 - Claude API client (pinned for compatibility with pydantic-ai)
- libcst>=1.0.0 - Python AST manipulation and transformation
- fastmcp>=2.14.0,<3 - Model Context Protocol server for tool definitions
- a2a-sdk>=0.3.0 - Async agent-to-agent execution framework (CloudEvents-based)

**Infrastructure:**
- google-cloud-firestore>=2.19.0 - User store, audit logs, rate limiting (Firestore backend)
- asyncpg - PostgreSQL driver (installed but may be optional for some deployments)
- structlog>=24.1.0 - Structured logging (JSON output)
- sentry-sdk>=2.0.0 - Error tracking and monitoring

**Observability:**
- langfuse - LLM observability, prompt management, evaluation

**Utilities:**
- python-dotenv - Environment variable loading from .env files
- pyyaml>=6.0 - YAML parsing
- watchdog>=4.0 - File system monitoring

**Security & Testing:**
- vulture>=2.11 - Dead code detection
- flake8>=7.0, flake8-deprecated>=2.3 - Code quality checks (supplemental to ruff)
- types-PyYAML - Type stubs for PyYAML

## Configuration

**Environment:**
- Environment variables configured via:
  - `.env` files (loaded by python-dotenv)
  - Container/cloud platform env vars (Google Cloud Run, Cloud Functions)
  - `.nvmrc` specifies Node.js 24
  - `.python-version` specifies Python 3.12

**Key Configuration Files:**
- `pyproject.toml` (workspace root) - Ruff, mypy, and pytest configuration
- `apps/backend/pyproject.toml` - Backend dependencies and type checking
- `functions/shared/pyproject.toml` - Shared function models
- `package.json` (root) - Node version, pnpm overrides, Nx config
- `pnpm-workspace.yaml` - Defines all monorepo packages
- `tsconfig.json` (per app/package) - TypeScript configuration
- `.prettierrc` - Code formatting rules
- `.eslintrc` (or oxlint config) - Linting rules

**Type Checking Configuration:**
- mypy strict mode enabled: `strict = true`
- pyright standard mode with execution environment overrides for known third-party gaps
- Pydantic mypy plugin enabled

## Platform Requirements

**Development:**
- Python 3.12 with pip/uv
- Node.js 24.x with pnpm
- Git for version control
- Make (Makefile with targets for pre-commit, checks, TS operations)

**Production:**
- Deployment: Google Cloud Run or Cloud Functions
- Firestore for user/audit data
- Optional: PostgreSQL (asyncpg support indicates potential use)
- Optional: LiteLLM proxy for LLM caching/load-balancing
- Optional: Sentry for error tracking

---

*Stack analysis: 2026-04-01*
