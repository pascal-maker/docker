# Kubernetes Labs — Lab 0 & Lab 1

## Lab 0 — Kubernetes Setup

### What is Kubernetes?
Kubernetes is a container orchestration platform. It automatically manages the deployment, scaling, and health of containerized applications across a cluster of machines.

### What is a Control Plane?
The Control Plane is the brain of the cluster. It stores the desired state of the cluster, schedules workloads onto nodes, and responds to `kubectl` commands. In our setup, this is the `server-0` node.

### Node Roles
| Role | Description |
|---|---|
| **Server (Control Plane)** | Manages the cluster state, runs the API server, scheduler, and etcd |
| **Agent (Worker)** | Runs the actual application Pods |
| **Load Balancer** | k3d helper that forwards external traffic into the cluster |

---

### Setup

We used `k3d` to simulate a multi-node Kubernetes cluster inside Docker containers.

```bash
k3d cluster create --agents 3 -p "30000-30020:30000-30020@server:0"
```

This creates:
- 1 control plane (`server-0`)
- 3 worker nodes (`agent-0`, `agent-1`, `agent-2`)
- 1 load balancer (`serverlb`)
- Ports `30000–30020` forwarded from your host into the cluster

Verify with:
```bash
k3d node list
```

Set kubectl context:
```bash
kubectl config use-context k3d-k3s-default
```

---

### Question 1 — K3D Config file

**Command to create a cluster using a config file:**
```bash
k3d cluster create --config k3d-config.yaml
```

**k3d-config.yaml:**
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

---

### Question 2 — Load Balanced Deployment

1. Screenshot of the app showing pod hostnames in the browser — see `screenshots/`
2. Command to show all pod IDs:
```bash
kubectl get pods -l app=nginx-app
```
Extra — show just the names:
```bash
kubectl get pods -l app=nginx-app -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'
```
3. **Kubernetes components responsible:**
   - **Deployment** manages the desired number of replicas
   - **Service (ClusterIP)** load-balances requests across all pod IPs
   - **kube-proxy** maintains iptables rules on each node to route traffic from the Service IP to real pods

---

### Question 3 — Default Namespace

```bash
kubectl config set-context --current --namespace=howest-k8s-demo
```

---

## Lab 1 — Kubernetes Basics

### Manifest Files

All YAML files are located in the `k8s/` directory.

| File | Description |
|---|---|
| `deployment-k8s-demo.yaml` | Main demo app — 3 replicas, NodeAffinity on agent-0 |
| `svc-k8s-demo-app.yaml` | NodePort Service on port 30000 |
| `deployment-mariadb.yaml` | MariaDB database + ClusterIP Service |
| `deployment-api.yaml` | FastAPI backend + ClusterIP Service |

Apply all manifests:
```bash
kubectl apply -f k8s/
```

---

### Question 1 — Update Replicas

Edit this line in `deployment-k8s-demo.yaml`:
```yaml
replicas: 3
```
Then re-apply:
```bash
kubectl apply -f k8s/deployment-k8s-demo.yaml
```

---

### Question 2 — Why do we need a Service?

Pods are ephemeral — they get a new random IP every time they restart or get rescheduled to a different node. A **Service** provides a stable, fixed address that always points to the correct pods regardless of restarts. It also automatically load-balances traffic across all healthy pods.

Without a Service, you would need to manually look up the pod IP after every restart and there would be no load balancing.

---

### Question 3 — Which components create Pods?

1. **Deployment** — defines the desired state (how many replicas, which image)
2. **ReplicaSet** — created by the Deployment, enforces the exact replica count at all times
3. **Scheduler** — decides which node each pod is placed on
4. **kubelet** — runs on each node and actually starts the container via the container runtime

---

### Question 4 — Node Affinity

To pin all pods to `agent-0`, add the following to the pod `spec` inside the deployment:

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
```
All pods will show `k3d-k3s-default-agent-0` in the NODE column.

---

### Question 5 — NodePort Service

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

**ClusterIP vs NodePort:**
| Type | Accessible from | Use case |
|---|---|---|
| ClusterIP | Inside cluster only | Internal service-to-service communication |
| NodePort | Host machine via node IP + port | Development / testing from outside the cluster |
| LoadBalancer | Public internet | Production environments |

---

### Question 6 — RollingUpdate Strategy

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 2
    maxUnavailable: 50%
```

**Explanation:**
- `maxSurge: 2` — during an update, Kubernetes is allowed to create 2 extra pods above the desired replica count, so the new version can start before the old one is fully stopped.
- `maxUnavailable: 50%` — at most half the pods can be down at any given moment during the update, ensuring the app stays partially available throughout.

---

### Question 7 — Rollback

```bash
kubectl rollout undo deployment/k8s-demo-app -n howest-k8s-demo
```

To roll back to a specific revision:
```bash
kubectl rollout history deployment/k8s-demo-app -n howest-k8s-demo
kubectl rollout undo deployment/k8s-demo-app --to-revision=1 -n howest-k8s-demo
```

---

### MYSQL_HOST value

```
svc-mariadb
```

Inside the Kubernetes cluster, DNS resolves the Service name `svc-mariadb` to its ClusterIP. This works the same way as Docker Compose service names in a shared network.

---

### Secrets

Passwords are never stored in plaintext YAML. A Kubernetes Secret holds all database credentials:

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

Both the MariaDB and FastAPI deployments reference this secret via `envFrom`:
```yaml
envFrom:
  - secretRef:
      name: mariadb-secret
```

---

### Headlamp Dashboard

Install:
```bash
helm repo add headlamp https://kubernetes-sigs.github.io/headlamp/
helm install my-headlamp headlamp/headlamp --namespace kube-system
```

Access:
```bash
kubectl --namespace kube-system port-forward svc/my-headlamp 9090:80
```

Generate login token:
```bash
kubectl create token my-headlamp --namespace kube-system
```

Open **http://localhost:9090** and paste the token to log in.

**Finding logs:**
- In Headlamp: navigate to a Pod → click the **Logs** tab
- Via CLI: `kubectl logs <pod-name> -n howest-k8s-demo`
