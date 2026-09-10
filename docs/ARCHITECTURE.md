# DocFlow architecture

## Structure review

| Layer | Path | Role |
|---|---|---|
| Desk UI | `apps/web` | Vite + React desk |
| API process | `apps/api` | FastAPI; one image, many roles via `DOCFLOW_SERVICE` |
| Service catalog | `apps/api/app/service_catalog.py` | Owns path prefixes ↔ service names |
| Gateway | `DOCFLOW_SERVICE=gateway` | Edge reverse proxy to domain services |
| Shared DB (legacy SaaS) | Postgres 16 | Row-level `tenant_id` — see [`LLD-SAAS-TENANT.md`](./LLD-SAAS-TENANT.md) |
| **Dedicated cell (target)** | Cluster/ns + **DB per tenant** | [`TENANT-CELLS.md`](./TENANT-CELLS.md) · `docker-compose.tenant-cell.yml` · `infra/terraform/modules/tenant-cell` |
| Compose monolith | `docker-compose.yml` | Dev/CI: api + web + postgres |
| Compose microservices | `docker-compose.microservices.yml` | Full service mesh locally |
| Compose tenant cell | `docker-compose.tenant-cell.yml` | One project = one tenant (own DB) |
| K8s | `infra/k8s` | Kustomize base + `local` / `staging` / `aws` / `gcp` / `tenant-cell` |
| Cloud TF | `infra/terraform/{aws,gcp}` + `modules/tenant-cell` | Dual cloud; sizing contract per tenant |
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

- **Shared mode:** one Deployment set; shared Postgres with `tenant_id` (current default)
- **Dedicated mode:** one cell per tenant (own DB; namespace or cluster) — [`TENANT-CELLS.md`](../docs/TENANT-CELLS.md)
- Image tags pinned (`2.0.0`), not `:latest`
- Secrets out of git; ConfigMap for non-secret config
- Probes: startup + readiness + liveness
- NetworkPolicy default-deny ingress in namespace
- AWS/GCP overlays drop in-cluster Postgres and expect managed `DATABASE_URL`
- Default `DOCFLOW_SERVICE=monolith` so existing tests and compose keep working
- `TENANT_MODE=shared|dedicated` · `TENANT_SLUG` for cell identity
