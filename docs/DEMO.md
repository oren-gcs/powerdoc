# Presentation demo

For the Israel GTM / feasibility room stopwatch script, use **[docs/israel/TOMORROW_DEMO.md](./israel/TOMORROW_DEMO.md)** (landmines: [DEMO_LANDMINES.md](./israel/DEMO_LANDMINES.md)).

1. Open http://localhost:5173 — landing (“Documents should move”).
2. Sign in as `oren@gcs-tech.org` / `DocFlow!2026`.
3. Overview shows seeded invoice, contract, memo plus real analytics (digest is fast heuristic — no Ollama wait).
4. Documents → drop a `.txt` invoice → status becomes ready, class `invoice`.
5. Open the document: OCR text, fields, re-run a flow.
6. Flows: step chips and recent run history (completed steps, not a fake queue).
7. Automations: invoice/contract routers with fire counts.
10. Connectors: labeled **Demo sandbox** (fake Drive/365 files). **Ollama** is real when `ollama serve` + pull + Use this model.
11. Forms → New: safe prompt in `docs/israel/TOMORROW_DEMO.md`. Heuristic fields; desk **always replies**.
12. Admin: users, block, flags, model bindings, health (includes Ollama).

API walkthrough: http://localhost:8000/docs
