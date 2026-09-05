# DocFlow vs Doc-Power vs document-flow

## What existed

| Surface | `powerdoc` (this repo) | `doc-power-local-k8s` | Document flow |
|---|---|---|---|
| Goal | “Prod-ready” packaging of Doc-Power | Multi-tenant SaaS for document processing, OCR, workflow, agents | The *path* a file takes: ingest → read → decide → act |
| Backend | Seven FastAPI stubs (`/health` only) | Real auth, documents, agent pipeline; workflow was LLM-comment + unused RabbitMQ | Incomplete: no step runner, no run records |
| Frontend | None | CRA app, missing routes (`/documents`, `/workflows`, `/analytics` 404), admin stubs, inline styles | Could not show a flow |
| Tenants | Mentioned in README | Required `tenant_id=1` pre-seeded; no create-tenant API | Blocked signup |
| OCR | AWS Textract in comments | Local Ollama vision; `shared/lib` missing from git | Fragile |
| Agents / MCP | None | `mcp-ollama-agents` + admin model bindings | Not productized in UI |
| Cloud | Terraform/EKS sketches, duplicated trees | Helm/k8s/terraform present but not aligned with compose | Not demoable |

## Product decision

Build **one** platform — **DocFlow 2.0** — that completes Doc-Power’s domain and makes document-flow a first-class, executable engine.

## Completions in this codebase

- Register creates a tenant (signup no longer blocked).
- JWT + refresh + RBAC (`platform_admin`, `owner`, `admin`, `operator`, `viewer`).
- Block user / suspend tenant endpoints the old UI called but the API lacked.
- Real workflow engine with step runs persisted (extract, classify, fields, condition, tag, summarize, notify, agent, webhook).
- Automations fire the matching workflow on classify/upload.
- Orchestrator pipeline replaces the cross-service HTTP chain that drifted out of sync.
- Gateway-shaped single API so the UI can reach documents, workflows, OCR, analytics, agents, admin.
- Skills on disk + MCP server + in-app agent console; **Ollama** is the default local LLM (Connectors bind a pulled model to form builder and agents).
- Analytics from real tables, not hardcoded admin stats.
- Local SQLite *and* Compose Postgres; Terraform for AWS (VPC, ALB, ECS, RDS, S3) and GCP (Cloud Run, Cloud SQL, GCS); Kubernetes manifests.
- UI: landing, auth, overview, library, inspector, flows, automations, agents, analytics, inbox, admin — all routed and wired.

Legacy snapshot remains in `doc-power-production/` for comparison. Do not run it as the product.
