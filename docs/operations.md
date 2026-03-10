# Operations Runbook

## Deploy

1. Build and publish image:
   ```bash
   docker build -t ghcr.io/example/persona0:<tag> .
   docker push ghcr.io/example/persona0:<tag>
   ```
2. Update `deploy/kubernetes/deployment.yaml` image tag.
3. Apply manifests:
   ```bash
   kubectl apply -k deploy/kubernetes
   kubectl rollout status deployment/persona0
   ```
4. Validate health:
   ```bash
   kubectl get pods -l app=persona0
   kubectl describe deployment persona0
   ```

## Rollback

1. Check rollout history:
   ```bash
   kubectl rollout history deployment/persona0
   ```
2. Roll back to previous revision:
   ```bash
   kubectl rollout undo deployment/persona0
   kubectl rollout status deployment/persona0
   ```
3. If needed, roll back to an explicit revision:
   ```bash
   kubectl rollout undo deployment/persona0 --to-revision=<N>
   ```

## Incident Response

### CrashLoopBackOff / failed probes

1. Inspect recent events and logs:
   ```bash
   kubectl describe pod <pod-name>
   kubectl logs <pod-name> --previous
   ```
2. Verify runtime config environment and overlay selection:
   ```bash
   kubectl exec <pod-name> -- env | grep PERSONA0_CONFIG_ENV
   ```
3. Validate readiness command in-cluster:
   ```bash
   kubectl exec <pod-name> -- python -m src.runtime.healthcheck --mode readiness
   ```
4. If config validation fails, patch ConfigMap or image and redeploy.

### Elevated scheduler errors

1. Confirm dead-letter growth via service logs.
2. Temporarily scale up replicas for resilience:
   ```bash
   kubectl scale deployment/persona0 --replicas=3
   ```
3. Investigate recent config or code changes and roll back if needed.
