# DocFlow architecture

## Structure review

| Layer | Path | Role |
|---|---|---|
| Desk UI | `apps/web` | Vite + React desk |
| API process | `apps/api` | FastAPI; one image, many roles via `DOCFLOW_SERVICE` |
| Service catalog | `apps/api/app/service_catalog.py` | Owns path prefixes ↔ service names |
| Gateway | `DOCFLOW_SERVICE=gateway` | Edge reverse proxy to domain services |
| Shared DB | Postgres 16 | Persistent; StatefulSet locally, RDS/Cloud SQL on AWS/GCP |
| Compose monolith | `docker-compose.yml` | Dev/CI: api + web + postgres |
| Compose microservices | `docker-compose.microservices.yml` | Full service mesh locally |
| K8s | `infra/k8s` | Kustomize base + `local` / `aws` / `gcp` overlays |
| Cloud TF | `infra/terraform/{aws,gcp}` | VPC + managed Postgres sketches (dual, no lock-in) |
| Legacy | `doc-power-production/` | Historical stubs — not the product |

## Services

| Service | Routes |
|---|---|
| `identity` | `/api/v1/auth`, `/org`, `/admin` |
| `documents` | `/documents`, `/search`, `/connectors`, `/agent`, `/mcp` |
| `forms` | `/forms`, `/public/forms` |
| `workflow` | `/workflows`, `/automations` |
| `notify` | `/notify` |
| `analytics` | `/analytics` |
| `gateway` | proxies `/api/*` |
| `monolith` | all routers (default local/CI) |

## Conventions

- One Deployment per service; shared Postgres until schema-per-service is justified
- Image tags pinned (`2.0.0`), not `:latest`
- Secrets out of git; ConfigMap for non-secret config
- Probes: startup + readiness + liveness
- NetworkPolicy default-deny ingress in namespace
- AWS/GCP overlays drop in-cluster Postgres and expect managed `DATABASE_URL`
- Default `DOCFLOW_SERVICE=monolith` so existing tests and compose keep working
