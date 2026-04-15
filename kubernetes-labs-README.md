# Kubernetes Labs — Full Overview
## Lab 0, 1, 2, 3

---

# Lab 0 — Kubernetes Setup

## What is Kubernetes?
Kubernetes is a container orchestration platform. It automatically manages the deployment, scaling, and health of containerized applications across a cluster of machines. Instead of manually starting containers on servers, you describe what you want and Kubernetes makes it happen.

## What is a Control Plane?
The Control Plane is the brain of the cluster. It stores the desired state, schedules workloads onto nodes, and handles all `kubectl` commands. In k3d, this is the `server-0` node.

## Node Roles

| Role | Node | Responsibility |
|---|---|---|
| **Server (Control Plane)** | `server-0` | Manages cluster state, runs scheduler, API server, etcd |
| **Agent (Worker)** | `agent-0/1/2` | Runs the actual application Pods |
| **Load Balancer** | `serverlb` | Forwards external traffic into the cluster |

## Cluster Setup

```bash
k3d cluster create --agents 3 -p "30000-30020:30000-30020@server:0" -v /tmp:/tmp
kubectl config use-context k3d-k3s-default
```

Verify:
```bash
k3d node list
```

Expected output:
```
k3d-k3s-default-agent-0    agent          k3s-default   running
k3d-k3s-default-agent-1    agent          k3s-default   running
k3d-k3s-default-agent-2    agent          k3s-default   running
k3d-k3s-default-server-0   server         k3s-default   running
k3d-k3s-default-serverlb   loadbalancer   k3s-default   running
```

## Q1 — K3D Config file

Create `k3d-config.yaml`:
```yaml
apiVersion: k3d.io/v1alpha5
kind: Simple
metadata:
  name: k3s-default
servers: 1
agents: 3
ports:
  - port: "30000-30020:30000-30020"
    nodeFilters:
      - server:0
```

Command:
```bash
k3d cluster create --config k3d-config.yaml
```

## Q2 — Load Balanced Deployment

Show all pod names:
```bash
kubectl get pods -l app=nginx-app
```
Just the names:
```bash
kubectl get pods -l app=nginx-app -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'
```

Components responsible for different hostnames on each refresh:
- **Deployment** — manages the 3 replicas
- **Service (ClusterIP)** — load-balances requests across all pod IPs
- **kube-proxy** — maintains routing rules on each node

## Q3 — Default Namespace

```bash
kubectl config set-context --current --namespace=howest-k8s-demo
```

---

# Lab 1 — Kubernetes Basics

## Manifest Files (`lab-1-kubernetes-basics/k8s/`)

| File | Description |
|---|---|
| `deployment-k8s-demo.yaml` | Demo app — 3 replicas, Node Affinity on agent-0, RollingUpdate |
| `svc-k8s-demo-app.yaml` | NodePort Service on port 30000 |
| `deployment-mariadb.yaml` | MariaDB + ClusterIP Service |
| `deployment-api.yaml` | FastAPI + ClusterIP Service |

Apply all:
```bash
kubectl apply -f lab-1-kubernetes-basics/k8s/
```

## Q1 — Update Replicas

Edit this line in `deployment-k8s-demo.yaml`:
```yaml
replicas: 3
```
Re-apply:
```bash
kubectl apply -f k8s/deployment-k8s-demo.yaml
```

## Q2 — Why do we need a Service?

Pods get a new random IP on every restart. A **Service** provides a stable, fixed address that always points to the right pods regardless of restarts, and automatically load-balances across all healthy replicas. Without it, you'd need to manually track pod IPs after every crash or reschedule.

## Q3 — Which components create Pods?

1. **Deployment** — defines the desired state (replica count, image)
2. **ReplicaSet** — enforces the exact number of running replicas at all times
3. **Scheduler** — decides which node each pod lands on
4. **kubelet** — runs on each node and starts the container via the container runtime

## Q4 — Node Affinity

Pin all pods to `agent-0` by adding to the pod `spec`:
```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: kubernetes.io/hostname
              operator: In
              values:
                - k3d-k3s-default-agent-0
```

Verify:
```bash
kubectl get pods -n howest-k8s-demo -l app=k8s-demo -o wide
# All pods show k3d-k3s-default-agent-0 in the NODE column
```

## Q5 — NodePort Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-k8s-demo-app
  namespace: howest-k8s-demo
spec:
  type: NodePort
  selector:
    app: k8s-demo
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
      nodePort: 30000
```

Access at: **http://localhost:30000**

| Type | Accessible from | Use case |
|---|---|---|
| ClusterIP | Inside cluster only | Internal service-to-service |
| NodePort | Host machine | Development / testing |
| LoadBalancer | Public internet | Production |

## Q6 — RollingUpdate Strategy

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 2         # allow 2 extra pods during update
    maxUnavailable: 50% # at most half the pods can be down at once
```

## Q7 — Rollback

```bash
kubectl rollout undo deployment/k8s-demo-app -n howest-k8s-demo
# Roll back to specific version:
kubectl rollout history deployment/k8s-demo-app -n howest-k8s-demo
kubectl rollout undo deployment/k8s-demo-app --to-revision=1 -n howest-k8s-demo
```

## MYSQL_HOST value

```
svc-mariadb
```
Kubernetes DNS resolves the Service name to its ClusterIP — same concept as Docker Compose service names.

## Secrets

```bash
kubectl create secret generic mariadb-secret \
  --from-literal=MYSQL_ROOT_PASSWORD=my_root_password \
  --from-literal=MYSQL_DATABASE=my_db \
  --from-literal=MYSQL_USER=my_user \
  --from-literal=MYSQL_PASSWORD=my_password \
  --from-literal=MYSQL_PORT=3306 \
  --from-literal=MYSQL_HOST=svc-mariadb \
  -n howest-k8s-demo
```

Reference in deployments via:
```yaml
envFrom:
  - secretRef:
      name: mariadb-secret
```

## Headlamp Dashboard

```bash
helm repo add headlamp https://kubernetes-sigs.github.io/headlamp/
helm install my-headlamp headlamp/headlamp --namespace kube-system
kubectl --namespace kube-system port-forward svc/my-headlamp 9090:80
kubectl create token my-headlamp --namespace kube-system
```
Open **http://localhost:9090**, paste the token to log in.

---

# Lab 2 — Kubernetes Advanced: Persistent Volumes

## What is a Persistent Volume?

| Object | Who creates it | Purpose |
|---|---|---|
| **PersistentVolume (PV)** | Admin / YAML | Defines the actual storage location |
| **PersistentVolumeClaim (PVC)** | Application / YAML | Requests storage from a PV |

Without a PV, database data is lost every time a pod is deleted. With a PV, data lives on the host filesystem and survives pod restarts, upgrades, and rescheduling.

## Manifest Files (`lab-2-kubernetes-advanced/k8s/`)

| File | Description |
|---|---|
| `storageclass-manual.yaml` | StorageClass "manual" for static PV binding |
| `pv-database.yaml` | PV for MariaDB backed by `/tmp/database` |
| `pvc-database.yaml` | PVC requesting 1Gi for MariaDB |
| `deployment-mariadb.yaml` | MariaDB Deployment with PVC mounted at `/var/lib/mysql` |
| `pv-storage-api.yaml` | PV for storage API backed by `/tmp/storage-api` |
| `pvc-storage-api.yaml` | PVC requesting 1Gi for storage API |
| `deployment-storage-api.yaml` | Storage API Deployment + NodePort on 30001 |

Apply in order:
```bash
kubectl apply -f k8s/storageclass-manual.yaml
kubectl apply -f k8s/pv-database.yaml
kubectl apply -f k8s/pv-storage-api.yaml
kubectl apply -f k8s/pvc-database.yaml
kubectl apply -f k8s/pvc-storage-api.yaml
kubectl apply -f k8s/deployment-mariadb.yaml
kubectl apply -f k8s/deployment-storage-api.yaml
```

Verify:
```bash
kubectl get pv
kubectl get pvc -n howest-k8s-demo
# Both PVCs should show STATUS: Bound
```

## Key YAML — Mounting a PVC

```yaml
# Pod level — declare the volume
volumes:
  - name: database-storage
    persistentVolumeClaim:
      claimName: pvc-database

# Container level — mount it
volumeMounts:
  - mountPath: "/var/lib/mysql"
    name: database-storage
```

## Q — How did you test the Persistent Volume?

```bash
# 1. Upload a file to the storage API
curl -X POST http://localhost:8001/upload \
  -F "file=@/tmp/test-persistence.txt" \
  -F "storage_type=DEFAULT"
# → Uploaded file to /mnt/data/storage/DEFAULT/test-persistence.txt

# 2. Delete the pod
kubectl delete pod -l app=storage-api -n howest-k8s-demo

# 3. Wait for new pod
kubectl rollout status deployment/storage-api -n howest-k8s-demo

# 4. File is still there on the new pod
kubectl exec -n howest-k8s-demo deploy/storage-api -- ls /mnt/data/storage/DEFAULT/
# → test-persistence.txt ✓

# 5. Also visible on host Mac filesystem
ls /tmp/storage-api/DEFAULT/
# → test-persistence.txt ✓
```

## Q — Mounting a ConfigMap as a volume

```yaml
# ConfigMap definition
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  app.properties: |
    LOG_LEVEL=debug
    MAX_CONNECTIONS=100

# Mount in Deployment
volumes:
  - name: config-volume
    configMap:
      name: my-config
containers:
  - volumeMounts:
      - mountPath: "/etc/config"
        name: config-volume
```

Each ConfigMap key becomes a file inside the mounted directory. For Secrets the syntax is identical — replace `configMap:` with `secret:`.

---

# Lab 3 — Kubernetes Helm

## What is Helm?

Helm is the package manager for Kubernetes. A **Chart** is a reusable, templated bundle of Kubernetes manifests. Values can be overridden per environment without touching the templates.

| Concept | Description |
|---|---|
| **Chart** | Bundled Kubernetes YAML templates |
| **Repository** | Hosted collection of Charts |
| **Release** | A running Chart instance in the cluster |

## Helm Repos

```bash
helm repo add howest https://howest-mct.github.io/helm-demo
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm search repo howest
```

## Q — Repository, Release name, Chart name

```bash
helm install helm-demo howest/example-v2 -n pascal-maker-helm-demo
```

1. **Repository:** `howest`
2. **Release name:** `helm-demo`
3. **Chart name:** `example-v2`

## WordPress with custom values

```bash
helm upgrade --install my-wordpress bitnami/wordpress \
  -f wordpress-values.yaml \
  -n pascal-maker-helm-demo
```

`wordpress-values.yaml`:
```yaml
wordpressUsername: pascal
service:
  type: NodePort
  nodePorts:
    http: 30010
    https: 30011
wordpressBlogName: Pascal's Blog
```

Access at **http://localhost:30010**

## Custom FastAPI Helm Chart

```
fastapi-example/
├── Chart.yaml         # name, version, description
├── values.yaml        # default values
└── templates/
    ├── _helpers.tpl   # reusable name/label functions
    ├── deployment.yaml
    ├── service.yaml
    ├── serviceaccounts.yaml
    └── NOTES.txt
```

Templates use `{{ .Values.xxx }}` placeholders replaced at install time:
```yaml
replicas: {{ .Values.replicaCount }}
image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
```

Install with custom values:
```bash
helm install fastapi-helm ./fastapi-example \
  -f helm-values.yaml \
  -n pascal-maker-helm-demo
```

Upgrade / Uninstall:
```bash
helm upgrade fastapi-helm ./fastapi-example -f helm-values.yaml -n pascal-maker-helm-demo
helm uninstall helm-demo -n pascal-maker-helm-demo
helm list -n pascal-maker-helm-demo
```

## Q — What does test-connection.yaml do?

It defines a **Helm test** — a temporary Pod that runs only when you execute `helm test <release>`. It uses `busybox` to run `wget` against the Service's internal cluster address. If the request succeeds, the test passes. The `helm.sh/hook: test-success` annotation marks it as a test pod so Helm creates and cleans it up automatically — it is not a permanent workload.

## Q — Why is Helm useful?

1. **Reusability** — one chart deploys to dev, staging, and production by changing only `values.yaml`
2. **Shareability** — anyone installs your app with one command from a repo
3. **Versioning** — upgrade or roll back any release with `helm upgrade` / `helm rollback`
4. **Templating** — variables and loops eliminate copy-paste across environments
5. **Single source of truth** — all config in `values.yaml`, change once, applied everywhere
