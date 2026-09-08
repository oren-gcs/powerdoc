# How to use DocFlow (everyday)

Operator guide for the desk. For Israel GTM / investor strategy, see [`docs/israel/`](./israel/). For a short live walkthrough script, see [`GUIDE_THROUGH.md`](./GUIDE_THROUGH.md).

**Desk:** http://localhost:5173 · **API docs:** http://localhost:8000/docs  
**Demo login:** `oren@gcs-tech.org` / `DocFlow!2026`

---

## Sign in

1. Open the desk → **Sign in** (or `/login`).
2. Use your org account, or the demo credentials above.
3. Language: rail footer (en / he / ar / es / fr). Hebrew and Arabic switch the desk to RTL.

---

## Find things (search)

In the desk header, use the **search** bar. Type a name fragment to find:

- **Forms** → opens the form builder  
- **Workflows / processes** (flows + automations) → Flows or Automations  
- **Documents** → document detail  
- **Connectors** → Connectors page  

API: `GET /api/v1/search?q=…` (authenticated).

---

## Upload a document

1. **Documents** → choose a file (`.txt` invoices work well for demos).
2. Pipeline runs: extract text → classify → fields → matching automations / workflow steps.
3. Open the row for OCR text, extracted fields, and re-run a flow if needed.

---

## Forms — compose, publish, answer

1. **Forms** → **New** (Form builder), or **Form builder** in the rail.
2. Describe the form in one sentence (compose chat) or add fields manually.
3. **Send to:** add recipient emails (or desk people). Each listed recipient gets a **personal link** (`/f/{token}`).
4. **Save** (draft) → **Publish** when ready. Copy personal URLs from the publish result (no SMTP yet — share links yourself).
5. If there are **no** recipients, publish yields a shared open link.
6. After the **first answer**, the form **locks** (no edit / delete / recipient change). Use **Copy to new form** for a fresh draft.
7. **Answered** on the form: submission log, linked documents, digest actions (ingest / digest / extract / summarize / insights / create automation).
8. **Archive** (keep or drop answers) / **Unarchive** as needed.

Public fill: open the link → fill → sign → send. A personal link **closes after submit** (reuse returns closed / already received).

File / image fields: uploads are scanned (reject risky types); clean files are stored and scan results appear on the submission.

---

## Connectors (honest sandbox)

**Connectors → Drive / Microsoft 365** open a **demo catalog** (labeled as such — not live OAuth). Flow: **Browse → Source → Folder → multi-select files → Sync selected into RAG**.

**Local DB** uses the same picker against this tenant’s documents / OCR (falls back to sample rows when the library is empty).

**Ollama** on the same page is real when `ollama serve` is running: pick a model → **Use this model**. Form chat, agents, and flows then prefer that local model.

API: `GET /api/v1/connectors/{id}/browse?path=` · `POST /api/v1/connectors/{id}/sync` with `{ "paths": [...] }`.

Do not present Sync as production cloud connect. Deep integration roadmap lives under `docs/israel/`.

---

## Flows and automations

- **Flows (n8n flows):** step chips, execute against a document, recent run history, JSON export.
- **Automations:** routers (e.g. invoice/contract) with fire counts; toggle on/off.

---

## Manage, inbox, agents, admin

| Area | Everyday use |
|------|----------------|
| **Manage** | Org layers, folders, grants |
| **Inbox** | In-app notifications |
| **Agents** | Status, skills, process a document, logs |
| **Analytics** | Library / ready / run pulse |
| **Admin** | Users, block, flags, model bindings, health (incl. Ollama) |

---

## Quick tips

- Prefer the **safe compose prompts** in the walkthrough when demoing without Ollama.
- Overview digest is a fast heuristic — it does not wait on a model.
- Keep strategy and bottleneck notes in `docs/israel/`; this file is for daily desk work.
