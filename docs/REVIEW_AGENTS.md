# Multi-agent review charter (DocFlow)

Launch **later** as parallel Cursor agents — one agent per section. Do **not** run the full set unless explicitly asked; this charter is the handoff.

**Priority order:** Integrations first, then forms / auth / workflows, then the rest.

Each agent should: stay in-scope, read the listed surfaces, write a short review note (gaps, honesty risks, everyday UX friction), and propose concrete fix PRs — not a rewrite.

---

## 1. Integrations / connectors — **PRIORITY #1**

| | |
|---|---|
| **Scope** | Drive, Microsoft 365, local DB, Ollama, Israeli ERP / BKMVDATA, morning / iCount, connector sync → RAG |
| **Surfaces** | `apps/api/app/routers/connectors.py`, Agents Ollama routes, Connectors UI, `docs/israel/*` integration notes |
| **Check** | Sandbox vs real OAuth honesty; sync upsert quality; Ollama “Use this model” path; roadmap claims (Priority / BKMVDATA / morning) vs shipped code; no UI that implies live cloud sync |
| **Outputs** | Gap list (sandbox vs prod), recommended UI/docs wording, staged integration milestones |

---

## 2. Forms lifecycle

| | |
|---|---|
| **Scope** | Compose → draft → publish → fill → lock → answered → digest → copy / archive |
| **Surfaces** | `apps/api/app/routers/forms.py`, FormBuilder, Forms list, FormAnswered, FillForm |
| **Check** | Lock after first answer; personal vs open links; upload fields + security scan; HE labels; confusing copy |
| **Outputs** | Lifecycle checklist, broken edge cases, everyday-operator UX notes |

---

## 3. Auth / recipients / public fill

| | |
|---|---|
| **Scope** | Login/register, roles, share tokens, per-recipient personal links, public submit |
| **Surfaces** | `auth` router, FormShare model, FillForm, share/publish APIs |
| **Check** | Token one-shot close; email matching; closed-link messaging; ACL / tenant isolation |
| **Outputs** | Security/UX findings for invite + fill path |

---

## 4. Workflows / automations / n8n

| | |
|---|---|
| **Scope** | Workflow execute, step runs, automations fire, n8n canvas/export |
| **Surfaces** | `workflows.py`, `automations.py`, `engine/workflow.py`, `engine/n8n.py`, Flows + Automations pages |
| **Check** | Real run history vs fake queues; trigger wiring on upload; export usefulness |
| **Outputs** | Reliability notes + demo-safe talking points |

---

## 5. Agents / orchestrator / RAG

| | |
|---|---|
| **Scope** | Document pipeline, agent skills, form compose RAG, knowledge chunks |
| **Surfaces** | `engine/orchestrator.py`, `engine/rag.py`, Agents UI, form compose |
| **Check** | Heuristic vs Ollama honesty; empty-RAG replies; ingest from answered forms |
| **Outputs** | When to claim “AI” vs desk heuristics; RAG quality gaps |

---

## 6. Hebrew / Israel GTM

| | |
|---|---|
| **Scope** | i18n HE/RTL, invoice heuristics (₪, חשבונית), Israel docs vs product |
| **Surfaces** | `apps/web/src/i18n.ts`, classify/OCR heuristics, `docs/israel/` |
| **Check** | Missing HE keys on desk pages; strategy docs leaking into everyday UI; GTM claims vs shipped |
| **Outputs** | i18n gap list; keep strategy in `docs/israel/`, not chrome |

---

## 7. Security / uploads

| | |
|---|---|
| **Scope** | Public multipart uploads, MIME/exe/SVG/HTML/PDF scans, storage |
| **Surfaces** | Form upload scan path, storage, public submit |
| **Check** | Reject rules, scan records, size limits, path traversal |
| **Outputs** | Hardening backlog + regression test ideas |

---

## 8. Infra / deploy

| | |
|---|---|
| **Scope** | Compose, env, seed, CI/e2e, health, local vs Docker |
| **Surfaces** | `docker-compose.yml`, `.env.example`, Makefile, GitHub Actions, README |
| **Check** | Boot path, demo seed, Playwright, Ollama optional |
| **Outputs** | Runbook fixes; env clarity for operators |

---

## How to launch later

1. Open one Cursor agent per section (start with **#1 Integrations**).
2. Point each agent at this file + its Surfaces row.
3. Ask for a short review markdown under `docs/reviews/<section>.md` (create folder when launching).
4. Prefer fix PRs that improve everyday use and integration honesty over large refactors.
