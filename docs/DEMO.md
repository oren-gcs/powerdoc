# Presentation demo

1. Open http://localhost:5173 — landing (“Documents should move”).
2. Sign in as `oren@gcs-tech.org` / `DocFlow!2026`.
3. Overview shows seeded invoice, contract, memo plus real analytics.
4. Documents → drop a `.txt` invoice → status becomes ready, class `invoice`.
5. Open the document: OCR text, fields, re-run a flow.
6. Flows: step chips and recent run history (completed steps, not a fake queue).
7. Automations: invoice/contract routers with fire counts.
10. Connectors: Google Drive, Microsoft 365, local DB, and **Ollama** (start `ollama serve`, pull a model, Use this model).
11. Forms → New: chat a brief (e.g. day summary for students). The desk **always replies**. Missing roster/topics → Connectors / Manage.
12. Admin: users, block, flags, model bindings, health (includes Ollama).

API walkthrough: http://localhost:8000/docs
