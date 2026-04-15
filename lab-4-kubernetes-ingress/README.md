# Lab 4 — Kubernetes Ingress & Load Balancer

## What is Ingress?

Ingress is a Kubernetes resource that manages external HTTP/HTTPS access to services inside the cluster. Instead of opening a separate NodePort per application, Ingress lets you define routing rules based on **hostname** or **URL path** — all funnelled through a single entry point.

| Approach | How to access | Limitation |
|---|---|---|
| NodePort | `localhost:30000`, `localhost:30001` … | One port per app, range 30000–32767 |
| Ingress | `nginx.localhost`, `vue.localhost` | Single port 80/443, unlimited apps via hostnames |

---

## Files (`k8s/`)

| File | Description |
|---|---|
| `nginx.yaml` | nginx Deployment (3 replicas) + ClusterIP Service |
| `vue-app.yaml` | Vue app Deployment (1 replica) + ClusterIP Service |
| `default-backend.yaml` | Fallback Deployment + ClusterIP Service |
| `ingress.yaml` | Ingress rules + defaultBackend |

### Apply all

```bash
kubectl apply -f k8s/nginx.yaml
kubectl apply -f k8s/vue-app.yaml
kubectl apply -f k8s/default-backend.yaml
kubectl apply -f k8s/ingress.yaml
```

---

## Namespace

```bash
kubectl create namespace ingress
kubectl config set-context --current --namespace=ingress
```

---

## Port mapping for Ingress

Because k3d uses Docker containers as nodes, we must forward port 80 from the `serverlb` node to the host:

```bash
k3d node edit k3d-k3s-default-serverlb --port-add 8080:80
```

Port 8080 is used instead of 80 in case the host machine blocks port 80.

---

## Ingress routing rules

```yaml
spec:
  rules:
    - host: nginx.localhost   → routes to svc-nginx:80
    - host: vue.localhost     → routes to svc-vue-app:80
```

Access:
- **http://nginx.localhost:8080** — shows the nginx app (load balanced across 3 pods)
- **http://vue.localhost:8080** — shows the Vue app
- **http://anything-else** — falls back to the default backend (404 page)

> On Windows: add entries to `C:\Windows\System32\drivers\etc\hosts`
> ```
> 127.0.0.1 nginx.localhost
> 127.0.0.1 vue.localhost
> ```
> On Mac/Linux this is not needed — `.localhost` resolves automatically.

---

## Default Backend

### What it is
When no Ingress rule matches a request, Kubernetes sends it to the `defaultBackend`. We built a custom 404 page for this.

### Files (`default-backend/`)
- `index.html` — styled 404 page
- `Dockerfile` — copies the HTML into an `nginx:alpine` image

```dockerfile
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
```

### Build & load into cluster

```bash
docker build -t pascal-maker/default-backend-k8s ./default-backend/
k3d image import pascal-maker/default-backend-k8s -c k3s-default
```

> To push to Docker Hub instead: `docker push pascal-maker/default-backend-k8s`
> (requires `docker login` first)

### Q — How did you set up the Default Backend?

Full `ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-router
  namespace: ingress
  annotations:
    ingress.kubernetes.io/ssl-redirect: "false"
spec:
  defaultBackend:
    service:
      name: svc-default-backend
      port:
        number: 80
  rules:
    - host: nginx.localhost
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: svc-nginx
                port:
                  number: 80
    - host: vue.localhost
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: svc-vue-app
                port:
                  number: 80
```

The `spec.defaultBackend` field points to `svc-default-backend`. Any request that doesn't match `nginx.localhost` or `vue.localhost` is routed there and served the custom 404 page.

---

## Why Ingress over NodePort in production?

1. **Single entry point** — one port 80/443 handles all apps via hostname routing
2. **No port range limits** — NodePorts are restricted to 30000–32767
3. **TLS termination** — Ingress controllers handle HTTPS certificates centrally
4. **Cleaner URLs** — users visit `app.example.com`, not `example.com:30042`
5. **Centralised routing** — all rules in one YAML file instead of one Service per app
