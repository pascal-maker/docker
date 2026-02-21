# POC: sync server + A2A refactor agent in one container
# Use BuildKit for cache mount: DOCKER_BUILDKIT=1 docker compose build
FROM python:3.12-slim

WORKDIR /app

# Copy only what uv sync needs; this layer is cached until pyproject/lock/src change
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

# Copy scripts and entrypoint last so changes here don't trigger dependency reinstall
COPY scripts ./scripts
COPY docker ./docker

ENV REPLICA_DIR=/workspace
ENV PATH="/app/.venv/bin:$PATH"

RUN mkdir -p /workspace

EXPOSE 8765 9999

ENTRYPOINT ["sh", "docker/entrypoint.sh"]
