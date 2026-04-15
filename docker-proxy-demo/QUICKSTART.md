# 🚀 Quick Start Guide

## Start the Demo in 4 Steps

### 0. Setup Environment (First Time Only)
```powershell
cp .env.example .env
```

### 1. Build and Start
```powershell
docker compose up --build
```

Wait for all services to start and become healthy (you'll see health check logs).

### 1b. Start Separate Compose Project (external network demo)
```powershell
docker compose -f external-web/compose.yaml --project-name external-web --env-file .env up -d --build
```

### 2. Open Browser
```
http://localhost:8080
```

### 3. Test Load Balancing
**Refresh the page multiple times** - you'll see different colored instances!

### 4. Test Reverse Proxy Routes
```powershell
# Served by nginx itself
curl http://localhost:8080/proxy-info

# Proxied to load-balanced webapp API
curl http://localhost:8080/webapp-api

# Proxied to private internal-api service
curl http://localhost:8080/internal-api/data

# Proxied to service from separate compose project
curl http://localhost:8080/external-project/info
```

---

## What You Should See

- 🔴 Red instance (WebApp-1)
- 🔵 Blue instance (WebApp-3)  
- 🟢 Teal instance (WebApp-2)

Each page shows:
- Which instance served your request
- Internal API data (from backend network)
- Container hostname
- Timestamp

---

## Common Commands

### View Logs
```powershell
# All services
docker compose logs -f

# Proxy startup/runtime logs
docker compose logs -f proxy

# Proxy HTTP access log (persisted volume)
docker compose exec proxy tail -f /var/log/nginx-persist/proxy-access.log

# Proxy error log (persisted volume)
docker compose exec proxy tail -f /var/log/nginx-persist/proxy-error.log

# Just one webapp
docker compose logs -f webapp1
```

### Check Health Status
```powershell
docker compose ps
```
Look for "(healthy)" in the STATUS column.

### Stop Everything
```powershell
docker compose down
```

### Restart After Changes
```powershell
docker compose down
docker compose up --build
```

---

## Test Scenarios

### 1. Normal Load Balancing
- Open http://localhost:8080
- Refresh 10 times
- Count how many times each instance responds
- Should be roughly equal (round-robin)

### 2. Instance Failure
```powershell
# Stop one instance
docker stop webapp2

# Refresh browser - still works!
# Only 2 instances now handle requests

# Restart it
docker start webapp2
```

### 3. Network Isolation Test
```powershell
# Try to access internal API (should fail)
curl http://localhost:5000/data

# Try to access external project service directly (should succeed)
curl http://localhost:5050/info

# Also through nginx proxy this works:
curl http://localhost:8080/internal-api/data
curl http://localhost:8080/external-project/info
```

---

## Troubleshooting

### "Port 8080 is already in use"
Edit `.env` and change the proxy port:
```bash
PROXY_PORT=9090  # Use 9090 instead
```

### "Services won't start" or "Unhealthy"
```powershell
docker compose down -v
docker compose up --build --force-recreate
```

### Check health status
```powershell
# See which services are healthy
docker compose ps

# Inspect specific container health
docker inspect --format='{{json .State.Health}}' webapp1
```

### "Can't see different instances"
Hard refresh your browser (Ctrl+F5) to avoid cached responses.

---

**Ready to explore? Check the full [README.md](README.md) for detailed explanations!**
