# Lab 4 - Docker Debug: Solution

## Overview

A microservice todo application consisting of three services:
- **database** — PostgreSQL 17
- **backend** — Python/FastAPI REST API
- **frontend** — Python/Flask web UI

The application had 7 bugs preventing it from running, plus several areas for optimization.

---

## Bugs Fixed

### Bug 1 — `frontend/Dockerfile` was nearly empty

**Problem:** The file only contained `CMD ["python", "app.py"]`. There was no base image (`FROM`), no working directory, no file copy, and no dependency installation. Docker cannot build an image without at least a `FROM` instruction.

**Fix:** Wrote a complete Dockerfile with a base image, working directory, dependency installation, and file copy.

---

### Bug 2 — `frontend/requirements.txt` had a nonexistent Flask version

**Problem:** `flask>=9.3.2` — Flask's latest major version is 3.x. Version 9 does not exist. pip would fail to resolve the package and the image build would crash.

**Fix:** Changed to `flask>=3.0.0`.

---

### Bug 3 — `compose.yaml` had the wrong port mapping for the backend

**Problem:** `"8000:8888"` maps host port 8000 to container port 8888. But the backend launches uvicorn on port 8000 inside the container, so nothing would ever reach it.

**Fix:** Changed to `"8000:8000"`.

---

### Bug 4 — `compose.yaml` used the wrong service name in `BACKEND_URL`

**Problem:** `BACKEND_URL: http://api:8000` — Docker's internal DNS resolves service names, and the backend service is named `backend`, not `api`. The frontend could never reach the backend.

**Fix:** Changed to `BACKEND_URL: http://backend:8000`.

---

### Bug 5 — `compose.yaml` had no port mapping for the frontend

**Problem:** The Flask app runs on port 80 inside the container but no `ports:` entry was defined in compose.yaml, making it completely unreachable from the host browser.

**Fix:** Added `ports: - "80:80"` to the frontend service.

---

### Bug 6 — No `depends_on`: backend started before the database was ready

**Problem:** `backend/app.py` calls `init_db()` at module load time, which creates the `todos` table. If PostgreSQL isn't accepting connections yet when the backend starts, the table is never created and every request returns a 500 error.

**Fix:** Added `depends_on` with `condition: service_healthy` on both the backend (waiting for the database) and the frontend (waiting for the backend).

---

### Bug 7 — `backend/requirements.txt` was missing `python-multipart`

**Problem:** FastAPI requires the `python-multipart` package to handle `Form(...)` data. It is not bundled with FastAPI itself. The `/add-todo` endpoint uses `Form(...)`, so without it uvicorn crashes at startup with a `RuntimeError`.

**Fix:** Added `python-multipart>=0.0.9` to `backend/requirements.txt`.

---

## Optimizations Applied

### Performance — Docker layer caching

**Both Dockerfiles** were updated to copy `requirements.txt` and run `pip install` *before* copying the application code:

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

Docker caches each layer. If only application code changes (not dependencies), the pip install layer is reused from cache, making rebuilds significantly faster.

---

### Healthchecks

Healthchecks were added to all three services so Docker knows when each service is genuinely ready, not just running.

- **database:** Uses `pg_isready`, PostgreSQL's own readiness tool.
- **backend:** Makes an HTTP request to the `/` endpoint via Python's built-in `urllib`.
- **frontend:** Inherits readiness via `depends_on` on a healthy backend.

---

### Persistent Volume

```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

Without a named volume, all todo data is lost every time `docker compose down` is run. The named volume `postgres_data` persists data across container restarts and rebuilds.

---

### Security — Non-root user

Both Dockerfiles were updated to create and switch to an unprivileged user:

```dockerfile
RUN adduser --disabled-password --gecos "" appuser
USER appuser
```

By default, Docker runs container processes as root. If the application is ever compromised, a root process has far greater ability to cause damage or escape the container. Running as a dedicated non-root user limits the blast radius.

---

## Final File State

### `backend/requirements.txt`
```
fastapi>=0.115.2
uvicorn>=0.31.1
psycopg2-binary>=2.9.9
python-multipart>=0.0.9
```

### `backend/Dockerfile`
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN adduser --disabled-password --gecos "" appuser
USER appuser
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `frontend/requirements.txt`
```
flask>=3.0.0
requests>=2.32.3
```

### `frontend/Dockerfile`
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN adduser --disabled-password --gecos "" appuser
USER appuser
CMD ["python", "app.py"]
```

### `compose.yaml`
```yaml
services:
  database:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: todo_db
      POSTGRES_USER: todo_user
      POSTGRES_PASSWORD: todo_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U todo_user -d todo_db"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgres://todo_user:todo_password@database:5432/todo_db
    depends_on:
      database:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/')\""]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    environment:
      BACKEND_URL: http://backend:8000
    depends_on:
      backend:
        condition: service_healthy

volumes:
  postgres_data:
```
