# Sync server + A2A + Chainlit; one image, entrypoint chooses which to run.
# Build with BuildKit for cache: DOCKER_BUILDKIT=1 docker compose build
FROM python:3.12-slim

WORKDIR /app

# 1. Install dependencies only (layer cached when pyproject.toml/uv.lock unchanged)
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-install-project

# 2. Copy app source and install project (layer cached when src/ unchanged)
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# 3. Copy runtime assets (scripts, prompts, entrypoint)
COPY scripts ./scripts
COPY prompts ./prompts
COPY docker ./docker

ENV REPLICA_DIR=/workspace
ENV PATH="/app/.venv/bin:$PATH"

RUN mkdir -p /workspace

EXPOSE 8765 9999 8000

ENTRYPOINT ["sh", "docker/entrypoint.sh"]
