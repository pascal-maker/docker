# 🐳 Docker Proxy & Load Balancer Demo

A comprehensive demonstration of Docker networking, reverse proxy, and load balancing concepts using Docker Compose with **production-ready best practices**.

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[BROWSER-LAB.md](BROWSER-LAB.md)** - Browser-only student exercise sheet (no terminal commands)
- **[BEST_PRACTICES.md](BEST_PRACTICES.md)** - Detailed explanation of all best practices
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Quick reference and overview
- **[architecture-overview.svg](architecture-overview.svg)** - Colored architecture overview
- **[traffic-allowed-blocked.svg](traffic-allowed-blocked.svg)** - Allowed vs blocked request examples
- **This README** - Complete documentation

## 📋 What This Demo Shows

This project demonstrates:

1. **Reverse Proxy / Load Balancer**: NGINX distributes traffic across multiple backend services
2. **External Network**: Public-facing services accessible from outside Docker
3. **Internal Network**: Private backend services isolated from external access
4. **Path-Based Proxy Routing**: NGINX routes `/`, `/webapp-api`, and `/internal-api/*` to different targets
5. **Load Balancing**: Round-robin distribution across multiple web service instances
6. **Service Discovery**: Containers communicate using DNS names
7. **Cross-Compose Networking**: A separate Compose project joins the same external frontend network

## 🏗️ Architecture

```
                    [External Traffic]
                            |
                            | Port 8080
                            ↓
                    ┌──────────────┐
                    │    NGINX     │ ← Reverse Proxy / Load Balancer
                    │ (Load Balance)│
                    └──────────────┘
                            |
            ┌───────────────┼───────────────┐
            ↓               ↓               ↓
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ WebApp-1 │    │ WebApp-2 │    │ WebApp-3 │
    │  (Red)   │    │  (Teal)  │    │  (Blue)  │
    └──────────┘    └──────────┘    └──────────┘
            |               |               |
            └───────────────┼───────────────┘
                            |
                            ↓ Backend Network (Internal Only)
                    ┌──────────────┐
                    │ Internal API │ ← NOT accessible externally
                    │   (Backend)  │
                    └──────────────┘
```

SVG diagrams for presentations and docs:
- **Overview (colored):** [architecture-overview.svg](architecture-overview.svg)
- **Allowed vs blocked examples:** [traffic-allowed-blocked.svg](traffic-allowed-blocked.svg)

## 📂 Project Structure

```
docker-proxy-demo/
├── compose.yaml                # Container orchestration (modern standard)
├── external-web/               # Separate compose project (shared frontend network)
│   ├── compose.yaml
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
├── .env                        # Environment variables (not committed)
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── nginx.conf                  # Load balancer configuration
├── webapp/                     # Web application service
│   ├── Dockerfile
│   ├── .dockerignore           # Docker build exclusions
│   ├── requirements.txt
│   ├── app.py
│   └── templates/
│       └── index.html
├── internal-api/               # Internal-only API service
│   ├── Dockerfile
│   ├── .dockerignore           # Docker build exclusions
│   ├── requirements.txt
│   └── app.py
├── README.md                   # This file
└── QUICKSTART.md              # Quick start guide
```

## 🔑 Key Concepts Explained

### 1. Reverse Proxy

**What is it?**
- A server that sits in front of web servers and forwards client requests to them
- Acts as an intermediary between clients and backend servers

**Benefits:**
- Hide backend server details (security)
- SSL/TLS termination
- Single entry point for multiple services
- Can cache responses

### 2. Load Balancer

**What is it?**
- Distributes incoming traffic across multiple servers
- Ensures no single server is overwhelmed

**Load Balancing Methods (NGINX):**
- `round-robin` (default): Requests distributed evenly in rotation
- `least_conn`: Sends requests to server with fewest active connections
- `ip_hash`: Client IP determines which server receives request
- `random`: Randomly selects server

### 3. Docker Networks

**Frontend Network (External):**
- Bridge network allowing external access
- NGINX proxy and web apps communicate here
- Accessible from host machine

**Backend Network (Internal):**
- Internal-only network (`internal: true`)
- Web apps and internal-api communicate here
- NOT accessible from outside Docker
- Perfect for databases, caches, internal APIs

### 4. Service-to-Service Traffic (a.k.a. "east-west")

- **Service-to-service traffic** means one container talking to another inside Docker networks.
- In this demo: `webapp1/2/3 -> internal-api`.
- **Client-to-proxy traffic** (browser/curl from outside) is often called north-south.

## 🚀 Getting Started

### Prerequisites

- Docker installed (Docker Desktop on Windows)
- Docker Compose V2+ (included with Docker Desktop)
- Containers run on **Python 3.14+** (configured via `PYTHON_VERSION` in `.env`)

### Setup

1. **Copy environment file:**
   ```powershell
   cp .env.example .env
   ```
   
   Edit `.env` to customize configuration if needed.

### Running the Demo

1. **Start main stack:**
   ```powershell
   docker compose up --build
   ```
   
   Note: Modern Docker uses `docker compose` (space) not `docker-compose` (hyphen)

2. **Start separate compose project (cross-project demo):**
   ```powershell
   docker compose -f external-web/compose.yaml --project-name external-web --env-file .env up -d --build
   ```

3. **Wait for healthchecks:**
   Services start in order based on health status:
   - internal-api starts first and becomes healthy
   - webapp instances start and become healthy
   - proxy starts last when all webapps are healthy

4. **Access the application:**
   - Open browser to: http://localhost:8080
   - Refresh multiple times to see load balancing in action!
   - Each refresh may show a different instance (different color)

5. **View logs:**
   ```powershell
   # All services
   docker compose logs -f

   # Specific service
   docker compose logs -f proxy
   docker compose logs -f webapp1
   ```

6. **Stop the demo:**
   ```powershell
   docker compose down
   docker compose -f external-web/compose.yaml --project-name external-web --env-file .env down
   ```

## 🧪 Testing & Experimentation

### 1. See Load Balancing in Action

Refresh the browser multiple times at http://localhost:8080 - you'll see different colored instances serving requests!

### 2. See Reverse Proxy Routing in Action

```powershell
# Served directly by nginx (no upstream app)
curl http://localhost:8080/proxy-info

# Proxied to the load-balanced webapp upstream
curl http://localhost:8080/webapp-api

# Proxied to private internal-api (not directly exposed on host)
curl http://localhost:8080/internal-api/data

# Proxied to a web service from a separate Compose project
curl http://localhost:8080/external-project/info
```

### 3. Check NGINX Status

```powershell
curl http://localhost:8080/nginx-status
```

### 4. Test Internal API Isolation

Try to access the internal API directly (this should fail):
```powershell
# This will NOT work - internal-api is not exposed externally
curl http://localhost:5000/data
```

But web apps CAN access it (check the web page - it displays internal API data).

The proxy can also access it through `http://localhost:8080/internal-api/data`.

### 5. Explicit Blocked Examples (from host)

```powershell
# Blocked: internal-api has no published host port
curl http://localhost:5000/data

# Blocked: web apps also have no published host ports
curl http://localhost:5001/
```

In this demo, `external-web` is intentionally exposed as well on `http://localhost:${EXTERNAL_WEB_HOST_PORT}` so you can compare direct access vs proxy access.

```powershell
# Direct access to the separate compose project service (now allowed)
curl http://localhost:5050/info

# Same service through the reverse proxy
curl http://localhost:8080/external-project/info
```

### 6. Simulate Server Failure

Stop one instance to see load balancer handle it:
```powershell
docker stop webapp2
```

Refresh browser - requests still work, distributed between remaining instances!

Restart it:
```powershell
docker start webapp2
```

### 7. View Health Status

Check service health:
```powershell
docker compose ps
```

You'll see health status for each service in the STATUS column.

### 8. Scale Services

Add more webapp instances:
```powershell
docker compose up --scale webapp1=2
```

Note: You'll need to update nginx.conf to include new instances or use dynamic service discovery.

## 🔍 Understanding the Components

### NGINX Configuration ([nginx.conf](nginx.conf))

```nginx
upstream webapp_backend {
    server webapp1:5000;  # Instance 1
    server webapp2:5000;  # Instance 2
    server webapp3:5000;  # Instance 3
}

server {
    listen 80;
    location / {
        proxy_pass http://webapp_backend;  # Load balance here
    }
}
```

### Docker Compose Best Practices ([compose.yaml](compose.yaml))

**Healthchecks:**
```yaml
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:5000/health"]
  interval: 10s
  timeout: 3s
  retries: 3
  start_period: 15s
```

**Service Dependencies:**
```yaml
depends_on:
  internal-api:
    condition: service_healthy  # Wait for healthy status
```

**Environment Variables:**
```yaml
environment:
  - INSTANCE_NAME=${WEBAPP1_NAME:-WebApp-1}  # From .env with default
  - INSTANCE_COLOR=${WEBAPP1_COLOR:-#FF6B6B}
```

### Docker Compose Networks

**Frontend Network:**
```yaml
networks:
  frontend:
    driver: bridge
    name: ${FRONTEND_NETWORK:-frontend}
```
- External-facing network
- Proxy and webapps connected

**Backend Network:**
```yaml
networks:
  backend:
    driver: bridge
    internal: true  # Key: Makes it internal-only!
    name: ${BACKEND_NETWORK:-backend}
```
- Internal communication only
- Webapps and internal-api connected
- No external access

## 📊 Monitoring

### View Container Stats

```powershell
docker stats
```

### Check Network Configuration

```powershell
# List networks
docker network ls

# Inspect frontend network
docker network inspect docker-proxy-demo_frontend

# Inspect backend network
docker network inspect docker-proxy-demo_backend
```

### Proxy Logs (Persisted in Volume)

```powershell
# Access log (inside proxy container, persisted on proxy_logs volume)
docker compose exec proxy tail -f /var/log/nginx-persist/proxy-access.log

# Error log
docker compose exec proxy tail -f /var/log/nginx-persist/proxy-error.log

# Optional: view Docker-managed volume details
docker volume inspect proxy_logs
```

### Test Service Resolution

```powershell
# Exec into webapp1 and test DNS
docker exec -it webapp1 ping internal-api
docker exec -it webapp1 ping webapp2
```

## 🎯 Real-World Applications

This architecture pattern is used for:

1. **Microservices**: Multiple services behind a single gateway
2. **High Availability**: Multiple instances for redundancy
3. **Horizontal Scaling**: Add more instances to handle traffic
4. **Security**: Hide internal services from external access
5. **API Gateway**: Single entry point for multiple APIs
6. **CDN / Caching**: Proxy can cache responses

## 🔧 Customization Ideas

### Change Load Balancing Algorithm

Edit [nginx.conf](nginx.conf):
```nginx
upstream webapp_backend {
    least_conn;  # or ip_hash, random
    server webapp1:5000;
    server webapp2:5000;
    server webapp3:5000;
}
```

### Add SSL/TLS

Add certificate mounting and configuration to NGINX.

### Add Database

Add a PostgreSQL or MongoDB service to the backend network.

### Add Redis Cache

Add Redis to backend network for session storage.

## 📚 Learn More

- [Docker Networking Documentation](https://docs.docker.com/network/)
- [NGINX Load Balancing](https://docs.nginx.com/nginx/admin-guide/load-balancer/http-load-balancer/)
- [Docker Compose Networking](https://docs.docker.com/compose/networking/)

## 🐛 Troubleshooting

**Services won't start:**
```powershell
docker compose down -v  # Remove volumes
docker compose up --build --force-recreate
```

**Healthchecks failing:**
```powershell
# Check logs for specific service
docker compose logs webapp1

# Check health status
docker compose ps

# Inspect container health
docker inspect --format='{{json .State.Health}}' webapp1
```

**Port 8080 already in use:**
Edit [.env](.env) file:
```bash
PROXY_PORT=9090  # Change to available port
```

**Cannot access internal-api:**
This is expected! It's internal-only. Check web app page to see it working.

**Environment variables not loading:**
Ensure `.env` file exists in the same directory as `compose.yaml`.

## 📝 License

This is a demo project for educational purposes.

---

**Happy Learning! 🚀**

Feel free to experiment, break things, and learn how Docker networking works!
