# DocFlow — High-Level Design (HLD)

![DocFlow HLD](./diagrams/docflow-hld.png)

## Diagram

```mermaid
flowchart TB
  subgraph Users
    Desk["Desk UI<br/>React + Vite"]
  end

  subgraph Edge
    Ingress["Ingress / TLS"]
    GW["API Gateway<br/>DOCFLOW_SERVICE=gateway"]
  end

  subgraph Domain["Domain services — one Deployment each"]
    ID["Identity<br/>auth · org · admin"]
    DOC["Documents<br/>ingest · OCR · search · connectors"]
    FRM["Forms<br/>compose · publish · public fill"]
    WF["Workflow<br/>automations · step runner"]
    NTF["Notify<br/>SMTP · notification log"]
    AN["Analytics<br/>summary · digest"]
  end

  subgraph Data
    PG[("Postgres 16<br/>persistent")]
  end

  subgraph CICD["CI/CD — staging first"]
    PR["GitHub PR"] --> CI["GitHub Actions<br/>pytest · build · Playwright"]
    CI --> GHCR["GHCR images<br/>api · web @ sha"]
    GHCR --> STG["Staging cluster<br/>kustomize overlay"]
  end

  Desk --> Ingress --> GW
  GW --> ID & DOC & FRM & WF & NTF & AN
  ID & DOC & FRM & WF & NTF & AN --> PG
```

## Scope

| Concern | Choice |
|---|---|
| Product surface | Desk UI + public form fill |
| Edge | Ingress → Gateway |
| Domains | identity, documents, forms, workflow, notify, analytics |
| Data | One persistent Postgres (shared DB until schema split is justified) |
| Local/CI default | `DOCFLOW_SERVICE=monolith` (same image, all routers) |
| Deploy | Kustomize overlays: `local` → **staging** → `aws` / `gcp` |
| Cloud | Dual path; no lock-in |

## Out of HLD

- Local process/module layout → [`LLD-LOCAL.md`](./LLD-LOCAL.md)
- SaaS row-level multi-tenant → [`LLD-SAAS-TENANT.md`](./LLD-SAAS-TENANT.md)
- **Dedicated cluster + DB per tenant (compute)** → [`TENANT-CELLS.md`](./TENANT-CELLS.md)

## Related

- [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- [`PRODUCTION.md`](./PRODUCTION.md)
- K8s: `infra/k8s/`
