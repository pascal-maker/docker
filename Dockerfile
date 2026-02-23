# Sync server + A2A + Chainlit; one image, entrypoint chooses which to run.
# Build with BuildKit for cache: DOCKER_BUILDKIT=1 docker compose build
FROM python:3.12-slim

WORKDIR /app

# 0. Install Node.js (LTS) and pnpm for TypeScript/ts-morph bridge subprocess in A2A
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && corepack enable && corepack prepare pnpm@latest --activate \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 1. Install dependencies only (layer cached when pyproject.toml/uv.lock unchanged)
# (No BuildKit --mount here so Cloud Build and plain docker build work.)
COPY pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-install-project

# 2. Copy app source and install project (layer cached when src/ unchanged)
COPY src ./src
RUN uv sync --frozen --no-dev

# 2b. Install TypeScript bridge deps with pnpm (workspace) so A2A can run ts-morph subprocess
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --filter ts-morph-bridge

# 3. Copy runtime assets (scripts, prompts, entrypoint)
COPY scripts ./scripts
COPY prompts ./prompts
COPY docker ./docker

ENV REPLICA_DIR=/workspace
ENV PATH="/app/.venv/bin:$PATH"

RUN mkdir -p /workspace

EXPOSE 8765 9999 8000

ENTRYPOINT ["sh", "docker/entrypoint.sh"]
