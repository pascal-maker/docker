# Changelog

## Version 2.0 - Best Practices Update (March 2026)

### 🎯 Major Changes

#### File Structure
- ✅ **RENAMED**: `docker-compose.yml` → `compose.yaml` (modern standard)
- ✅ **REMOVED**: `version` field from compose file (deprecated)
- ✅ **ADDED**: `.env` for environment configuration
- ✅ **ADDED**: `.env.example` as template
- ✅ **ADDED**: `.dockerignore` files for webapp and internal-api
- ✅ **ENHANCED**: `.gitignore` with comprehensive rules

#### Health Monitoring
- ✅ **ADDED**: Health checks to all services (proxy, webapp1-3, internal-api)
- ✅ **ADDED**: `/health` endpoints in all applications
- ✅ **CHANGED**: `depends_on` now uses `condition: service_healthy`
- ✅ **ADDED**: Proper startup orchestration based on health status

#### Docker Images
- ✅ **CHANGED**: Dockerfiles now install `wget` for health checks
- ✅ **OPTIMIZED**: Multi-line RUN commands for smaller image layers
- ✅ **IMPROVED**: Better layer caching with proper cleanup

#### Configuration
- ✅ **EXTERNALIZED**: All configurable values to `.env`
- ✅ **ADDED**: Default values in compose file using `${VAR:-default}` syntax
- ✅ **IMPROVED**: Named networks for predictability
- ✅ **ADDED**: Explicit build context in all services

#### Documentation
- ✅ **ADDED**: `BEST_PRACTICES.md` - Comprehensive best practices guide
- ✅ **ADDED**: `PROJECT_SUMMARY.md` - Quick reference
- ✅ **ADDED**: `CHANGELOG.md` - This file
- ✅ **UPDATED**: `README.md` with new commands and structure
- ✅ **UPDATED**: `QUICKSTART.md` with health check info

---

## Version 1.0 - Initial Release

### Features
- ✅ NGINX reverse proxy / load balancer
- ✅ 3 web application instances (load balanced)
- ✅ Internal API service (backend network only)
- ✅ Frontend and backend network segmentation
- ✅ Interactive web UI showing which instance responds
- ✅ Complete documentation

---

## Migration Guide (v1.0 → v2.0)

### Breaking Changes
⚠️ **File renamed**: `docker-compose.yml` → `compose.yaml`

### Migration Steps

1. **Update Docker Desktop** (if needed)
   ```powershell
   # Ensure you have Docker Compose V2+
   docker compose version
   ```

2. **Create environment file** (if upgrading)
   ```powershell
   cp .env.example .env
   ```

3. **Update commands**
   ```powershell
   # Old command (still works)
   docker-compose up

   # New command (preferred)
   docker compose up
   ```

4. **Wait for health checks**
   - Services now wait for dependencies to be healthy
   - Startup takes longer but is more reliable
   - Use `docker compose ps` to check health status

5. **Review configuration**
   - Check `.env` for customizable values
   - Update as needed for your environment

---

## Detailed Changes by File

### compose.yaml (formerly docker-compose.yml)
```diff
- version: '3.8'
  
  services:
    proxy:
+     healthcheck:
+       test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost/health"]
+       interval: 10s
+       timeout: 3s
+       retries: 3
+       start_period: 10s
      ports:
-       - "8080:80"
+       - "${PROXY_PORT:-8080}:80"
      depends_on:
-       - webapp1
+       webapp1:
+         condition: service_healthy

    webapp1:
+     healthcheck:
+       test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:5000/health"]
+       interval: 10s
      environment:
-       - INSTANCE_NAME=WebApp-1
+       - INSTANCE_NAME=${WEBAPP1_NAME:-WebApp-1}
+     depends_on:
+       internal-api:
+         condition: service_healthy

    internal-api:
+     healthcheck:
+       test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:5000/health"]
+       interval: 10s

  networks:
    frontend:
+     name: ${FRONTEND_NETWORK:-frontend}
    backend:
+     name: ${BACKEND_NETWORK:-backend}
```

### Dockerfile (webapp & internal-api)
```diff
  FROM python:3.11-slim
  
  WORKDIR /app
  
+ # Install system dependencies
+ RUN apt-get update && \
+     apt-get install -y --no-install-recommends wget && \
+     apt-get clean && \
+     rm -rf /var/lib/apt/lists/*
+
+ # Install Python dependencies
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
```

### New Files
```
+ .env                    # Environment configuration
+ .env.example            # Environment template
+ .dockerignore           # Build optimization (2 files)
+ BEST_PRACTICES.md       # Best practices guide
+ PROJECT_SUMMARY.md      # Quick reference
+ CHANGELOG.md            # This file
```

### Updated Files
```
~ compose.yaml            # Modernized with health checks
~ README.md               # Updated commands and structure
~ QUICKSTART.md           # Added health check instructions
~ .gitignore              # Enhanced coverage
~ webapp/Dockerfile       # Added wget installation
~ internal-api/Dockerfile # Added wget installation
```

---

## Benefits of v2.0

### Reliability
- ✅ Services start in correct order
- ✅ No race conditions from premature starts
- ✅ Automatic detection of unhealthy services

### Maintainability
- ✅ Configuration externalized to .env
- ✅ Better documentation
- ✅ Follows current best practices
- ✅ Easier to customize

### Performance
- ✅ Smaller Docker images (.dockerignore)
- ✅ Faster builds (layer optimization)
- ✅ Better caching

### Security
- ✅ No secrets in compose file
- ✅ .env not committed to git
- ✅ Minimal attack surface

### Operations
- ✅ Easy health monitoring
- ✅ Predictable naming
- ✅ Standard health endpoints

---

## Compatibility

### Minimum Requirements
- Docker Engine 20.10+
- Docker Compose V2.0+
- Docker Desktop 4.0+ (Windows/Mac)

### Tested On
- Windows 11 with Docker Desktop
- Docker Engine 24.0+
- Docker Compose V2.20+

---

## Future Enhancements

Potential improvements for v3.0:

- [ ] Multi-stage Dockerfiles for smaller images
- [ ] Prometheus metrics endpoint
- [ ] Grafana dashboards
- [ ] SSL/TLS configuration
- [ ] Rate limiting
- [ ] Authentication layer
- [ ] Database service example
- [ ] Redis cache example
- [ ] Kubernetes manifests
- [ ] Helm charts

---

**For detailed explanations of each change, see [BEST_PRACTICES.md](BEST_PRACTICES.md)**
