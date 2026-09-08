# Presentation demo

Everyday operator docs: **[HOW_TO_USE.md](./HOW_TO_USE.md)** · short desk path: **[GUIDE_THROUGH.md](./GUIDE_THROUGH.md)**.  
For the Israel GTM / feasibility room stopwatch script, use **[docs/israel/TOMORROW_DEMO.md](./israel/TOMORROW_DEMO.md)** (landmines: [DEMO_LANDMINES.md](./israel/DEMO_LANDMINES.md)).

1. Open http://localhost:5173 — landing (field→office opening line in the Israel runbook).
2. Sign in as `oren@gcs-tech.org` / `DocFlow!2026`.
3. Overview shows seeded invoice, contract, memo plus real analytics (digest is fast heuristic — no Ollama wait).
4. Documents → drop a `.txt` invoice → status becomes ready, class `invoice`.
5. Open the document: OCR text, fields, re-run a flow.
6. Flows: step chips and recent run history (completed steps, not a fake queue).
7. Automations: invoice/contract routers with fire counts.
8. Connectors: Drive/365 sync uses demo samples (not live OAuth). **Ollama** is real when `ollama serve` + pull + Use this model. See HOW_TO_USE.
9. Forms → New: safe prompt in `docs/israel/TOMORROW_DEMO.md` (invoice approval… or student day-summary). Heuristic fields; desk **always replies**.
10. Admin: users, block, flags, model bindings, health (includes Ollama).

API walkthrough: http://localhost:8000/docs
