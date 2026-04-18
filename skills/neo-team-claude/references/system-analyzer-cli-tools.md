# System Analyzer — CLI Tools Reference

CLI tools available via Bash for live system investigation. Always check connectivity before running queries.

## kubectl (Kubernetes)

```bash
# Check pod status
kubectl get pods -n <namespace> -o wide

# View pod logs (recent)
kubectl logs -n <namespace> deployment/<name> --tail=200

# Search logs for errors
kubectl logs -n <namespace> deployment/<name> --tail=500 | grep -i -E "error|panic|fatal|exception"

# View pod events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Describe pod for detailed status (restarts, OOM, crash loops)
kubectl describe pod -n <namespace> <pod-name>

# Check rollout status
kubectl rollout status deployment/<name> -n <namespace>

# Check resource usage
kubectl top pods -n <namespace>

# Check environment variables
kubectl exec -n <namespace> <pod-name> -- env | sort

# Check ExternalSecret sync
kubectl get externalsecret -n <namespace>
```

## psql (PostgreSQL)

```bash
# Connect with environment variables
export $(cat .env.sit | xargs)  # or .env.uat, .env

# One-shot query (non-interactive)
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT ..."

# Check table structure
psql ... -c "\d+ table_name"

# Check recent records
psql ... -c "SELECT * FROM table_name ORDER BY created_at DESC LIMIT 10"

# Check for data anomalies
psql ... -c "SELECT column, COUNT(*) FROM table GROUP BY column HAVING COUNT(*) > 1"
```

**Database safety:**
- Only SELECT, \d, \dt, \di — never INSERT, UPDATE, DELETE, or DDL
- Use LIMIT to avoid large result sets
- Prefer `psql -c` for one-shot queries over interactive sessions
- If credentials aren't available, report what you need and stop — never guess passwords

## argocd (ArgoCD)

```bash
# Check application status
argocd app get <app-name>

# Check sync status
argocd app get <app-name> -o json | jq '.status.sync.status'

# View application history
argocd app history <app-name>

# Check health status
argocd app get <app-name> -o json | jq '.status.health.status'

# Compare live vs desired state
argocd app diff <app-name>

# List recent events
argocd app get <app-name> -o json | jq '.status.conditions'
```

## docker (Docker)

```bash
# Check running containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# View container logs
docker logs <container> --tail=200

# Check container resource usage
docker stats --no-stream

# Inspect container config (env vars, mounts, health)
docker inspect <container> | jq '.[0].Config.Env'

# Check container health
docker inspect <container> | jq '.[0].State.Health'
```
