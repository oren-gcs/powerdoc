# DocFlow Kubernetes

Kustomize layout (current convention):

```
infra/k8s/
  base/                 # shared Deployments, StatefulSet Postgres PVC, Ingress, NetworkPolicy, HPA
  overlays/
    local/              # in-cluster Postgres + seed
    aws/                # no in-cluster Postgres — use RDS DATABASE_URL in Secret
    gcp/                # no in-cluster Postgres — use Cloud SQL DATABASE_URL in Secret
```

## Apply

```bash
# render
kubectl kustomize infra/k8s/overlays/local

# apply (after replacing Secret values)
kubectl apply -k infra/k8s/overlays/local
```

Pin image tags in `base/kustomization.yaml` / overlay `images:`. Never deploy `:latest`.

Secrets: replace `REPLACE_ME` via Sealed Secrets, External Secrets Operator, or `kubectl create secret` — do not commit real credentials.
