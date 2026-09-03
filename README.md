# DocFlow

Production document intelligence platform — the completed successor to **Doc-Power**, with **document flow** as an executable engine rather than a message nobody consumes.

**Desk:** http://localhost:5173  
**API:** http://localhost:8000/docs  
**Demo:** `oren@gcs-tech.org` / `DocFlow!2026`

## Why this exists

`doc-power-production` in this repo was a 400-file *package* whose seven services only returned `/health`. The real lineage lives in [doc-power-local-k8s](https://github.com/oren-gcs/doc-power-local-k8s): multi-tenant ingest, OCR, an agent orchestrator, and an admin model console. That stack still had blocking gaps — no tenant signup, workflows that did not execute steps, missing gateway proxies, placeholder UI routes, and cloud charts that did not match the running compose file.

DocFlow keeps that product goal and finishes the path:

**upload → extract text → classify → match automation → run workflow steps → notify → analytics**

See [docs/COMPARISON.md](docs/COMPARISON.md).

## Local (no Docker)

```bash
python3 -m pip install -r apps/api/requirements.txt
cd apps/api && PYTHONPATH=. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# other terminal
cd apps/web && npm install && npm run dev
```

Optional LLM: run Ollama locally or set `OPENAI_API_KEY`. Without either, heuristic agents still complete the pipeline (good for demos and CI).

## Docker / Compose

```bash
docker compose up --build
```

UI on `:5173`, API on `:8000`, Postgres on `:5432`.

## Tests

API (pytest):

```bash
cd apps/api && PYTHONPATH=. python3 -m pytest -q tests
```

### Playwright — local

Install the web app plus a local Chromium for Playwright (one-time on a laptop):

```bash
make e2e-install
# same as:
# cd apps/web && npm install && npx playwright install --with-deps chromium
```

Run against API + Vite on this machine (reuses servers if they are already up):

```bash
make e2e
# or: cd apps/web && npm run test:e2e
```

Headed (see the browser): `cd apps/web && npm run test:e2e:headed`

### Playwright — cloud

Against a **deployed** desk (AWS / GCP / k8s). Do not start local servers:

```bash
export PLAYWRIGHT_BASE_URL=https://your-docflow.example
export PLAYWRIGHT_DEMO_EMAIL=oren@gcs-tech.org
export PLAYWRIGHT_DEMO_PASSWORD='DocFlow!2026'
cd apps/web && npm run test:e2e:cloud
```

On GitHub Actions: every push/PR boots the local stack on `ubuntu-latest`. To hit a cloud URL, run the **Playwright** workflow with `workflow_dispatch` and the `base_url` input (optional secrets `PLAYWRIGHT_DEMO_EMAIL` / `PLAYWRIGHT_DEMO_PASSWORD`).

## MCP

```json
{
  "mcpServers": {
    "docflow": {
      "command": "python",
      "args": ["apps/mcp/server.py"],
      "env": { "DOCFLOW_API": "http://127.0.0.1:8000" }
    }
  }
}
```

Tools: `health`, `list_documents`, `list_workflows`, `list_skills`, `analytics_summary`, `run_skill`.

## Cloud

| Target | Path |
|---|---|
| Kubernetes | `infra/k8s/docflow.yaml` |
| AWS (VPC, ALB, ECS, RDS, S3) | `infra/terraform/aws` |
| GCP (Cloud Run, Cloud SQL, GCS) | `infra/terraform/gcp` |

Set `CLOUD_PROVIDER=aws|gcp` and a Postgres `DATABASE_URL` in production. Replace the RDS/Cloud SQL demo password before `terraform apply`.

## Architecture

```
React desk (Vite)
    → FastAPI DocFlow API
        → Auth / tenants / RBAC
        → Documents + local/object storage
        → OCR (pypdf / tesseract / text)
        → Classifier + field extraction
        → Workflow engine (persisted step runs)
        → Automations
        → Agents + skills
        → Notifications + analytics
    → MCP stdio server
```

## Skills

`skills/*/SKILL.md` — invoice extraction, contract review, KYC, summarize, compliance, operator playbook.
