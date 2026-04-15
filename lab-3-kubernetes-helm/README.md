# Lab 3 — Kubernetes Helm

## What is Helm?

Helm is the package manager for Kubernetes. Instead of applying individual YAML files one by one, Helm bundles them into a **Chart** — a reusable, templated package where values can be overridden per environment or user.

### Three core concepts

| Concept | Explanation |
|---|---|
| **Chart** | A Helm package — all the Kubernetes YAML templates bundled together |
| **Repository** | A collection of Charts, hosted publicly or privately (like npm or apt) |
| **Release** | A running instance of a Chart in the cluster. One Chart can be installed multiple times, each creating its own Release |

---

## Setup

```bash
# Add the Howest demo repo
helm repo add howest https://howest-mct.github.io/helm-demo

# List available charts
helm search repo howest

# Add Bitnami repo
helm repo add bitnami https://charts.bitnami.com/bitnami
```

---

## Question — Repository, Chart name, Release name

Command used:
```bash
helm install helm-demo howest/example-v2 -n pascal-maker-helm-demo
```

1. **Repository:** `howest`
2. **Release name:** `helm-demo`
3. **Chart name:** `example-v2`

---

## WordPress with custom values

**Command used:**
```bash
helm upgrade --install my-wordpress bitnami/wordpress \
  -f wordpress-values.yaml \
  -n pascal-maker-helm-demo
```

`wordpress-values.yaml` overrides:
```yaml
wordpressUsername: pascal
service:
  type: NodePort
  nodePorts:
    http: 30010
    https: 30011
wordpressBlogName: Pascal's Blog
```

Access at: **http://localhost:30010**

---

## Custom FastAPI Helm Chart

### File structure

```
fastapi-example/
├── Chart.yaml               # Chart metadata (name, version, description)
├── values.yaml              # Default values — overridable per install
└── templates/
    ├── _helpers.tpl          # Reusable template functions (name, labels, etc.)
    ├── deployment.yaml       # Kubernetes Deployment template
    ├── service.yaml          # Kubernetes Service template
    ├── serviceaccounts.yaml  # Kubernetes ServiceAccount template
    └── NOTES.txt             # Instructions printed after helm install
```

### How templates work

Instead of hardcoded values, templates use `{{ .Values.xxx }}` placeholders:

```yaml
# In deployment.yaml
replicas: {{ .Values.replicaCount }}
image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
```

When you run `helm install`, Helm substitutes all placeholders with values from `values.yaml` (or your override file).

### Install the custom chart

```bash
helm install fastapi-helm ./fastapi-example \
  -f helm-values.yaml \
  -n pascal-maker-helm-demo
```

`helm-values.yaml` overrides:
```yaml
replicaCount: 2
image:
  repository: ghcr.io/nathansegers/fastapi-intro
  tag: v1.0.0
nameOverride: "pascal-fastapi"
fullnameOverride: "pascal-fastapi-demo"
serviceAccount:
  create: true
  name: helm-service-account
```

### Upgrade / Uninstall

```bash
helm upgrade fastapi-helm ./fastapi-example -f helm-values.yaml -n pascal-maker-helm-demo
helm uninstall helm-demo -n pascal-maker-helm-demo
helm list -n pascal-maker-helm-demo
```

---

## Question — What does test-connection.yaml do?

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "example.fullname" . }}-test-connection"
  annotations:
    "helm.sh/hook": test-success
spec:
  containers:
    - name: wget
      image: busybox
      command: ['wget']
      args: ['{{ include "example.fullname" . }}:{{ .Values.service.port }}']
  restartPolicy: Never
```

This defines a **Helm test** — a temporary Pod that only runs when you execute `helm test <release>`. It uses `busybox` to run `wget` against the Service's internal address. If the request succeeds, the test passes. The `helm.sh/hook: test-success` annotation marks it as a test pod, not a permanent workload — it is created during `helm test` and cleaned up afterwards.

In short: it automatically verifies the Service is reachable from inside the cluster after installation.

---

## Question — Why is Helm useful?

1. **Reusability** — one chart deploys to dev, staging, and production by changing only `values.yaml`
2. **Shareability** — publish a chart to a repo and others install it with one command
3. **Versioning** — upgrade or roll back any release with `helm upgrade` / `helm rollback`
4. **Templating** — variables and conditionals in YAML eliminate copy-paste across environments
5. **Single source of truth** — all config lives in `values.yaml`; change replica count or image tag in one place
