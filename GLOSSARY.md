# Docker Commands Glossary

A reference of every command used across the demos in this repo.

---

## docker compose up

Start all services defined in `compose.yaml`.

```bash
docker compose up
```

| Flag | Description |
|---|---|
| `--build` | Rebuild images before starting (picks up code/config changes) |
| `-d` | Detached mode — run in background, free up your terminal |
| `<service>` | Target a single service instead of the whole stack |

Examples:
```bash
docker compose up --build          # rebuild everything and start
docker compose up -d               # start in background
docker compose up --build -d       # rebuild and start in background
docker compose up --build -d api   # rebuild and restart only the api service
```

---

## docker compose down

Stop and remove containers and networks. Named volumes are kept by default.

```bash
docker compose down
```

| Flag | Description |
|---|---|
| `-v` | Also delete named volumes (data will be lost) |

---

## docker compose restart

Restart running services without rebuilding.

```bash
docker compose restart             # restart everything
docker compose restart status-ui  # restart a single service
```

---

## docker compose watch

Watch for file changes and automatically sync or rebuild services.

```bash
docker compose watch
```

Requires a `develop.watch` block in `compose.yaml`:

```yaml
develop:
  watch:
    - action: sync+restart   # sync files into container and restart app
      path: src
      target: /app/src
    - action: rebuild        # full image rebuild
      path: requirements.txt
```

| Action | What it does |
|---|---|
| `sync` | Copy changed files into the running container (no restart) |
| `sync+restart` | Copy files in and restart the app process |
| `rebuild` | Full `docker build` — use for dependency/config changes |

---

## docker compose logs

View output from a service.

```bash
docker compose logs api            # all logs for api service
docker compose logs api --tail 20  # last 20 lines only
docker compose logs -f api         # follow live (like tail -f)
```

---

## docker compose down + up (data persistence test)

Used in the volumes demo to prove data survives with named volumes:

```bash
docker compose down    # destroy containers (volume survives)
docker compose up -d   # bring back up — data still there
```

---

## docker exec

Run a command inside a running container.

```bash
docker exec <container-name> <command>
```

Examples:
```bash
docker exec networking_demo-api-1 sh -c "ls /mnt/data/storage"
docker exec networking_demo-api-1 env
docker exec -it networking_demo-api-1 sh   # interactive shell session
```

| Flag | Description |
|---|---|
| `-it` | Interactive terminal — use when you want a shell session |
| `sh -c "..."` | Run a one-liner without an interactive shell |

---

## docker volume inspect

Find out where Docker stores a named volume on the host.

```bash
docker volume inspect networking_demo_data
```

Returns the `Mountpoint` path inside the Docker VM.

---

## docker compose config --services

List all service names defined in `compose.yaml`.

```bash
docker compose config --services
```

---

## docker init

Auto-generate Docker files for an existing project. Run it once in a project folder — Docker detects the language/framework and creates:

- `Dockerfile`
- `compose.yaml`
- `.dockerignore`
- `README.Docker.md`

```bash
cd your-project
docker init
```

---

## k3d cluster stop

Used to free up ports (8090/8091) occupied by a local Kubernetes cluster before running the depends_on demo.

```bash
k3d cluster stop
```

---

## Compose file quick reference

| Key | What it does |
|---|---|
| `ports: - 8080:80` | Map host port 8080 → container port 80 |
| `hostname: my-api` | Set a DNS alias for the container inside Docker's network |
| `volumes: - data:/mnt/data` | Mount named volume `data` at `/mnt/data` inside container |
| `command: tail -f /dev/null` | Override startup command — keeps container alive for debugging |
| `depends_on: api: condition: service_healthy` | Wait for `api` healthcheck to pass before starting this service |
| `healthcheck: test/interval/retries` | Define how Docker checks if a service is ready |
| `develop: watch:` | Configure Docker watch rules for auto-sync/rebuild |
