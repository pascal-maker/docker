# Lab 2 — Kubernetes Advanced: Persistent Volumes

## What is a Persistent Volume?

A **Persistent Volume (PV)** is storage that exists independently from any Pod.
Normal container storage disappears the moment a Pod is deleted — a PV does not.
Think of it as a USB drive that stays plugged into the cluster regardless of which pod is running.

A **Persistent Volume Claim (PVC)** is a request by an application for storage.
Kubernetes matches the PVC to an available PV that satisfies the request (size, access mode, storage class).

| Object | Who creates it | Purpose |
|---|---|---|
| PersistentVolume (PV) | Admin / YAML | Defines the actual storage |
| PersistentVolumeClaim (PVC) | Application / YAML | Requests storage from a PV |

---

## Why is persistent storage necessary?

Without a PV, every time a database pod is deleted (upgrade, crash, reschedule), all data is lost.
With a PV, the data lives on the host filesystem (`/tmp/database`) and any new pod that mounts the same PVC instantly has access to all previous data.

---

## Cluster Setup

The k3d cluster was created with `/tmp` bind-mounted into all nodes:

```bash
k3d cluster create --agents 3 -p "30000-30020:30000-30020@server:0" -v /tmp:/tmp
```

This maps `/tmp` on your Mac into every k3d Docker container, so any `hostPath` PV pointing to `/tmp/...` is backed by a real folder on your laptop.

---

## Files

| File | Description |
|---|---|
| `storageclass-manual.yaml` | StorageClass "manual" (no-provisioner, static binding) |
| `pv-database.yaml` | PersistentVolume for MariaDB, backed by `/tmp/database` |
| `pvc-database.yaml` | PersistentVolumeClaim for MariaDB, requests 1Gi |
| `deployment-mariadb.yaml` | MariaDB Deployment + ClusterIP Service with PVC mounted |
| `pv-storage-api.yaml` | PersistentVolume for the storage API, backed by `/tmp/storage-api` |
| `pvc-storage-api.yaml` | PersistentVolumeClaim for the storage API, requests 1Gi |
| `deployment-storage-api.yaml` | Storage API Deployment + NodePort Service (port 30001) with PVC mounted |

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

Verify everything is Bound:

```bash
kubectl get pv
kubectl get pvc -n howest-k8s-demo
```

---

## Key YAML additions — Mounting a PVC to a Pod

Two sections must be added to the Deployment:

**1. Under `spec.template.spec` (Pod level) — declare the volume:**
```yaml
volumes:
  - name: database-storage
    persistentVolumeClaim:
      claimName: pvc-database
```

**2. Under `spec.template.spec.containers` (Container level) — mount it:**
```yaml
volumeMounts:
  - mountPath: "/var/lib/mysql"
    name: database-storage
```

The `volumes` section says "I want to use `pvc-database` and call it `database-storage`".
The `volumeMounts` section says "mount `database-storage` at this path inside the container".

---

## Question — How did you test the Persistent Volume?

```bash
# 1. Upload a file to the storage API
curl -X POST http://localhost:8001/upload \
  -F "file=@/tmp/test-persistence.txt" \
  -F "storage_type=DEFAULT"
# → Uploaded file to /mnt/data/storage/DEFAULT/test-persistence.txt

# 2. Delete the pod — Kubernetes automatically creates a new one
kubectl delete pod -l app=storage-api -n howest-k8s-demo

# 3. Wait for the new pod to start
kubectl rollout status deployment/storage-api -n howest-k8s-demo

# 4. List files on the new pod — file is still there
kubectl exec -n howest-k8s-demo deploy/storage-api -- ls /mnt/data/storage/DEFAULT/
# → test-persistence.txt  ✓

# 5. Also verify on the host filesystem
ls /tmp/storage-api/DEFAULT/
# → test-persistence.txt  ✓
```

The file survived the pod deletion because it was stored on the PV (`/tmp/storage-api`),
not inside the container. The new pod mounted the same PVC and found all previous data intact.

---

## Storage API details

Source: https://github.com/nathansegers/docker-storage-demo  
Image: `ghcr.io/nathansegers/kubernetes-storage-test:latest`

| Setting | Value |
|---|---|
| Container port | 80 |
| Volume mount path | `/mnt/data/storage` |
| NodePort | 30001 → http://localhost:30001 |
| API docs | http://localhost:30001/docs |

---

## Question — Mounting a ConfigMap as a volume

Yes, Kubernetes supports mounting ConfigMaps as files inside a container.
This is useful when an application reads its config from a file (e.g. `nginx.conf`, `app.properties`).

```yaml
# 1. Create a ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  namespace: howest-k8s-demo
data:
  app.properties: |
    LOG_LEVEL=debug
    MAX_CONNECTIONS=100

---
# 2. Mount it as a volume in your Deployment
spec:
  template:
    spec:
      volumes:
        - name: config-volume
          configMap:
            name: my-config        # reference the ConfigMap by name
      containers:
        - name: my-app
          volumeMounts:
            - mountPath: "/etc/config"   # folder inside the container
              name: config-volume
```

Each key in the ConfigMap becomes a file inside `/etc/config/`.
So `app.properties` appears at `/etc/config/app.properties` inside the container.

**Difference from a Secret mount:**
The syntax is identical — just replace `configMap:` with `secret:` and `name:` pointing to the Secret name.
Secrets are base64-encoded in etcd and access can be restricted via RBAC, making them more suitable for passwords and tokens.

Reference: https://kubernetes.io/docs/concepts/storage/volumes/#configmap
