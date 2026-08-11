# Flask K8s Project — Production-Style Deployment

A minimal production-style application stack demonstrating containerization, 
deployment automation, observability, and operational debugging.

## Architecture
GitHub Actions CI/CD
↓
Docker Hub Registry
↓
Kubernetes Cluster (Minikube)
↓
┌─────────────────────────────┐
│ flask-app │
│ (2 replicas + probes) │
│ Ingress │
└─────────────┬───────────────┘
↓
┌─────────────────────────────┐
│ PostgreSQL │
│ (ClusterIP Service) │
└─────────────────────────────┘

## Stack
- **App:** Python Flask REST API
- **Database:** PostgreSQL 15
- **Container Registry:** Docker Hub
- **Orchestration:** Kubernetes (Minikube)
- **CI/CD:** GitHub Actions
- **Namespace:** flask-app

## Endpoints
| Endpoint | Description |
|----------|-------------|
| GET /health | Liveness check — is app alive? |
| GET /ready | Readiness check — is DB connected? |
| GET /init | Initialize database and seed data |
| GET /users | Fetch all users from PostgreSQL |

## Reliability Implementation — Readiness & Liveness Probes

### Why I chose probes:
In production, a container can be running but not actually ready to serve 
traffic — for example if the database hasn't started yet. Without probes, 
Kubernetes sends traffic to broken pods causing user-facing errors.

### What they solve:
- **Liveness probe** hits `/health` every 15s — if it fails 3 times, 
  Kubernetes restarts the container. Catches deadlocks and infinite loops.
- **Readiness probe** hits `/ready` every 10s — checks real PostgreSQL 
  connectivity. Pod only receives traffic when DB connection is confirmed.

### Tradeoff:
- `initialDelaySeconds: 15` means pods take 15s before receiving traffic.
- Too aggressive probe settings can cause unnecessary restarts.
- Solution: tune `failureThreshold` and `periodSeconds` based on app startup time.

## CI/CD Pipeline
Every push to `main` triggers GitHub Actions:
1. Checkout code
2. Login to Docker Hub
3. Build Docker image tagged with Git SHA
4. Push to Docker Hub
5. Update K8s manifest with new image tag
6. Commit updated manifest back to repo

## Failure Simulations

### Failure 1 — ImagePullBackOff (encountered naturally)
**What happened:** Image existed locally but wasn't pushed to Docker Hub.
**Symptom:** Pods stuck in ImagePullBackOff / ErrImagePull
**Debug:**
```bash
kubectl describe pod <pod-name> -n flask-app
# Events showed: Failed to pull image — not found in registry
```
**Fix:** `docker push rutujakurhekar/flask-k8s-app:v1`
**Lesson:** Kubernetes can't access local Docker images — always push to registry first.

### Failure 2 — Bad ConfigMap → Readiness Probe Failure
**What happened:** Changed DB_HOST to wrong value in ConfigMap
**Symptom:** Pods running but 0/1 READY — readiness probe timing out
**Debug:**
```bash
kubectl get pods -n flask-app
# STATUS: Running but READY: 0/1

kubectl describe pod -n flask-app -l app=flask-app
# Warning Unhealthy: Readiness probe failed: context deadline exceeded

kubectl logs -n flask-app -l app=flask-app
# Connection refused to wrong-host:5432
```
**Fix:**
```bash
kubectl patch configmap app-config -n flask-app \
  --patch '{"data":{"DB_HOST":"postgres-service"}}'
kubectl rollout restart deployment/flask-app -n flask-app
```
**Lesson:** Readiness probes protect users — broken pods never receive 
traffic even when container is running. ConfigMap changes require pod 
restart to take effect.

## Deployment Commands
```bash
# Start cluster
minikube start
minikube addons enable ingress

# Deploy everything
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/flask-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Verify
kubectl get all -n flask-app

# Test
kubectl port-forward service/flask-service 8080:80 -n flask-app
curl http://localhost:8080/health
curl http://localhost:8080/ready
curl http://localhost:8080/init
curl http://localhost:8080/users
```

## Tradeoff Discussion
**What I simplified:**
- Single node Minikube vs multi-node production cluster
- No TLS on Ingress
- PostgreSQL without persistent volume (data lost on pod restart)
- No horizontal pod autoscaler

**What would break at scale:**
- PostgreSQL needs PersistentVolumeClaim for data durability
- Single replica PostgreSQL is a single point of failure
- No resource quotas at namespace level

**What I'd improve in production:**
- Add PersistentVolume for PostgreSQL
- Implement HorizontalPodAutoscaler for Flask app
- Add TLS termination at Ingress
- Use external secret manager (AWS Secrets Manager)
- Add Prometheus + Grafana for monitoring
