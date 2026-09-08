# DocFlow — production bar

DocFlow is **meant for production**. Merged `main` is the product baseline; remaining work is hardening what is still demo-grade, not treating the system as a throwaway prototype.

## Already production-shaped

- Multi-tenant auth (JWT + RBAC), signup creates a tenant
- Executable upload → OCR → classify → automation → workflow steps → activity
- Forms: compose, publish, personal recipient tokens, lock after answer, answered/digest, file upload **security scan**
- Modular monolith (`api` + `web`) — operable; MCP is optional sidecar
- Upload malware/polyglot rejection before store

## Must harden before calling a deploy “production”

| Area | Today | Production requirement |
|---|---|---|
| **Secrets** | Default `SECRET_KEY`, demo password in docs | Env/secrets manager; rotate demo creds out of public docs |
| **Email** | `channel=email` writes `Notification` only | Real SMTP / SES / SendGrid on publish & share |
| **Connectors** | Drive/365 **demo catalog** | OAuth + real file fetch; keep “demo catalog” only for local/dev |
| **RAG** | Keyword SQL search; plaintext chunks | Vector embeddings (pgvector or equiv.) + optional at-rest encryption; tenant-safe retrieval |
| **Signatures** | Canvas drawing | Policy path for qualified e-sign / evidence if sold as legal signature |
| **TLS / storage** | Local HTTP + filesystem paths | HTTPS terminate; encrypted object storage (S3/GCS) |
| **K8s / cloud** | Sketch manifests + TF | Kustomize base + overlays; image tags ≠ `:latest`; secrets not in git |
| **Architecture** | Modular monolith default | Microservices via `DOCFLOW_SERVICE` + gateway; see [`ARCHITECTURE.md`](./ARCHITECTURE.md) |
| **Observability** | Basic health | Metrics, structured logs, alert on pipeline/scan failures |
| **CI** | Playwright | Pytest + Playwright + image build on every PR |

## Production RAG (intent)

1. Keep keyword retrieve as fallback (offline / cold start).
2. Add embedding on `upsert_chunk` + ANN retrieve.
3. Encrypt sensitive chunk payloads at rest when required by customer policy.
4. Form-derived chunks (`form_submission` / digests) must remain **retrievable** under `rag_source_forms` (enabled by default).

## Deploy posture

- **Compose (monolith):** `docker compose up --build` — local / single-node.
- **Compose (microservices):** `docker compose -f docker-compose.microservices.yml up --build`.
- **K8s:** `kubectl apply -k infra/k8s/overlays/{local,aws,gcp}` after replacing Secret values.
- **Cloud:** Terraform AWS/GCP — pass `db_password`; dual path, no lock-in yet.

Everyday operator docs: [`HOW_TO_USE.md`](./HOW_TO_USE.md). Section review agents: [`REVIEW_AGENTS.md`](./REVIEW_AGENTS.md) (integrations first).
