# 📚 Docker Compose Best Practices Implemented

This document explains all the best practices implemented in this project and why they matter.

## 1. Modern Compose File Naming

### ✅ What We Did
- Used `compose.yaml` instead of `docker-compose.yml`

### 📖 Why It Matters
- `compose.yaml` is the official modern standard (Docker Compose V2+)
- Better alignment with YAML standards
- More consistent with other tools that use `*.yaml`
- `docker-compose.yml` is legacy but still supported

### 📚 Reference
- [Docker Compose Specification](https://docs.docker.com/compose/compose-file/)

---

## 2. No Version Field

### ✅ What We Did
- Removed `version: '3.8'` from compose file

### 📖 Why It Matters
- The `version` field is deprecated in Compose Specification
- Modern Docker Compose automatically uses the latest specification
- Cleaner, more maintainable configuration
- Avoids confusion about version compatibility

### 📚 Reference
- As of Compose Specification v1.0, the version field is obsolete

---

## 3. Health Checks

### ✅ What We Did
```yaml
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:5000/health"]
  interval: 10s      # Check every 10 seconds
  timeout: 3s        # Wait max 3s for response
  retries: 3         # Try 3 times before marking unhealthy
  start_period: 15s  # Grace period on startup
```

### 📖 Why It Matters
- **Reliability**: Ensures services are actually ready, not just running
- **Smart Dependencies**: Other services wait for health, not just startup
- **Auto-Recovery**: Unhealthy containers can be automatically restarted
- **Monitoring**: Easy to see which services have issues

### 🎯 Best Practices
- Use lightweight health check commands (wget, curl with --spider)
- Set reasonable intervals (10-30s for most apps)
- Allow adequate start_period for slow-starting apps
- Health check endpoints should be fast (<1s response)

### 📚 Reference
- [Docker Healthcheck](https://docs.docker.com/engine/reference/builder/#healthcheck)

---

## 4. Dependency Conditions

### ✅ What We Did
```yaml
depends_on:
  internal-api:
    condition: service_healthy  # Wait for healthy, not just started
```

### 📖 Why It Matters
- **Prevents Race Conditions**: Services don't start until dependencies are ready
- **Cleaner Startup**: No connection errors from premature starts
- **Cascading Health**: If a dependency fails, dependent services won't start

### 🔄 Startup Order in This Project
```
1. internal-api starts → becomes healthy
2. webapp1, webapp2, webapp3 start → become healthy
3. proxy starts → becomes healthy
```

### 📚 Reference
- [Control startup order](https://docs.docker.com/compose/startup-order/)

---

## 5. Environment Files

### ✅ What We Did
- Created `.env` for configuration values
- Created `.env.example` as a template
- Added `.env` to `.gitignore`

### 📖 Why It Matters
- **Security**: Secrets not committed to version control
- **Flexibility**: Easy customization without editing compose file
- **Portability**: Different environments (dev/staging/prod) use different .env files
- **Defaults**: Can provide fallback values in compose file

### 🎯 Best Practices
```yaml
# In compose.yaml - use variable with default
ports:
  - "${PROXY_PORT:-8080}:80"  # Default to 8080 if not in .env

environment:
  - INSTANCE_NAME=${WEBAPP1_NAME:-WebApp-1}  # Default value
```

### 📁 File Structure
```
.env          # Actual config (gitignored)
.env.example  # Template (committed to git)
```

### 📚 Reference
- [Environment variables in Compose](https://docs.docker.com/compose/environment-variables/)

---

## 6. .dockerignore Files

### ✅ What We Did
Created `.dockerignore` in both `webapp/` and `internal-api/` directories.

### 📖 Why It Matters
- **Faster Builds**: Excludes unnecessary files from build context
- **Smaller Images**: Less data sent to Docker daemon
- **Security**: Prevents accidental inclusion of secrets or sensitive files
- **Efficiency**: Reduces cache invalidation

### 📝 What to Exclude
```dockerignore
# Common excludes
__pycache__      # Python cache
.git             # Git repository
.env             # Environment secrets
*.md             # Documentation
.vscode          # IDE configs
tests            # Test files
.pytest_cache    # Test cache
```

### 💾 File Size Impact
Without .dockerignore: Build context can be 10-100MB
With .dockerignore: Build context typically <1MB

### 📚 Reference
- [.dockerignore file](https://docs.docker.com/engine/reference/builder/#dockerignore-file)

---

## 7. Enhanced .gitignore

### ✅ What We Did
Comprehensive .gitignore covering:
- Python cache files
- Virtual environments
- IDE configurations
- Environment files
- OS-specific files
- Docker logs

### 📖 Why It Matters
- **Clean Repository**: Only source code, no artifacts
- **Security**: Prevents committing secrets in .env files
- **Collaboration**: Avoids conflicts from IDE/OS files
- **Reduced Size**: Repository stays small

### 📚 Reference
- [gitignore patterns](https://git-scm.com/docs/gitignore)

---

## 8. Explicit Build Context

### ✅ What We Did
```yaml
build:
  context: ./webapp
  dockerfile: Dockerfile
```

### 📖 Why It Matters
- **Clarity**: Explicit is better than implicit
- **Flexibility**: Can specify different Dockerfile names
- **Organization**: Keeps build configuration clear

---

## 9. Named Networks

### ✅ What We Did
```yaml
networks:
  frontend:
    name: ${FRONTEND_NETWORK:-frontend}
  backend:
    name: ${BACKEND_NETWORK:-backend}
```

### 📖 Why It Matters
- **Predictable Names**: Not auto-generated with project prefix
- **Easier Debugging**: Clear network names in `docker network ls`
- **External Connectivity**: Other compose projects can connect using known names

---

## 10. Resource Optimization in Dockerfile

### ✅ What We Did
```dockerfile
# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### 📖 Why It Matters
- **Smaller Images**: Cleanup in same layer reduces size
- **Layer Efficiency**: Combined commands = fewer layers
- **Cache Optimization**: Related operations together

### 🎯 Dockerfile Best Practices
1. **Multi-stage builds** (for production)
2. **Minimize layers** (combine RUN commands)
3. **Order by change frequency** (less changing commands first)
4. **Clean up in same layer** (apt-get clean, rm -rf)
5. **Use specific versions** (for reproducibility)

---

## 11. Explicit Restart Policies

### ✅ What We Did
```yaml
restart: ${RESTART_POLICY:-unless-stopped}
```

### 📖 Why It Matters
- **Resilience**: Containers restart on failure
- **Configuration**: Externalized via environment variable
- **Production Ready**: Survives daemon restarts

### 🔄 Restart Policy Options
- `no`: Never restart (default)
- `always`: Always restart
- `on-failure`: Restart on non-zero exit
- `unless-stopped`: Restart unless manually stopped

---

## 12. Internal Networks

### ✅ What We Did
```yaml
backend:
  driver: bridge
  internal: true  # No external access
```

### 📖 Why It Matters
- **Security**: Backend services isolated from internet
- **Zero Trust**: Services can't reach external networks
- **Defense in Depth**: Only exposed services are public

### 🛡️ Security Model
```
Internet → Proxy (frontend network) → WebApps (both networks) → Internal API (backend network only)
```

---

## 13. Health Check Endpoints

### ✅ What We Did
```python
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})
```

### 📖 Why It Matters
- **Standardization**: Common pattern across microservices
- **Monitoring**: Can be used by orchestrators (K8s, Swarm, Compose)
- **Load Balancers**: Can remove unhealthy instances from rotation
- **Debugging**: Quick way to verify service is responding

### 🎯 Best Practices for Health Endpoints
- Keep them lightweight (no heavy computation)
- Return quickly (<100ms)
- Check critical dependencies (DB, cache) for advanced health
- Use appropriate HTTP status codes (200 = healthy)

---

## 14. Container Naming

### ✅ What We Did
```yaml
container_name: webapp1
```

### 📖 Why It Matters
- **Predictable**: Always the same name (easier debugging)
- **CLI Friendly**: `docker logs webapp1` instead of random names
- **Monitoring**: Consistent names for log aggregation

### ⚠️ Caveat
Cannot scale services with explicit container names. Choose between:
- Fixed names + manual scaling
- Auto names + dynamic scaling (`docker compose up --scale`)

---

## Summary Checklist

✅ Use `compose.yaml` (not docker-compose.yml)
✅ Remove version field
✅ Add healthchecks to all services
✅ Use `depends_on` with `condition: service_healthy`
✅ Externalize configuration in `.env`
✅ Create `.env.example` template
✅ Add `.dockerignore` to all services
✅ Comprehensive `.gitignore`
✅ Explicit build context
✅ Named networks
✅ Optimize Dockerfile layers
✅ Explicit restart policies
✅ Use internal networks for security
✅ Implement health endpoints
✅ Meaningful container names

---

## Additional Resources

- [Docker Compose Specification](https://docs.docker.com/compose/compose-file/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Container Networking](https://docs.docker.com/network/)

---

**This project demonstrates production-ready Docker Compose practices suitable for real-world applications!**
