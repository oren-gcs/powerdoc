# Bottlenecks, AI ladder, positioning

## Bottlenecks (session)

1. **Field → office handoff** — photos, WhatsApp, paper, and ad-hoc Excel never become a routed desk object.
2. **Invoice / compliance noise** — missing fields, missing allocation context, no health signal before the CPA sees the mess.
3. **Integration theater** — Monday/Zapier-style wiring without a document-native ingest → classify → route engine.
4. **Demo honesty** — claiming “AI” where the desk is still heuristic, or “connectors” where sync is sandbox (see [DEMO_LANDMINES.md](./DEMO_LANDMINES.md)).

## AI ladder — sell levels 0–1 first

| Level | What it is | Demo / sell posture |
|---|---|---|
| **0** | Deterministic routing, folders, forms, workflow steps | Ship and show |
| **1** | Heuristic compose / classify (no LLM required) | **Sell this first** — form builder `harvest_fields` already works offline |
| **2+** | Local Ollama / richer agents | Optional depth; never block the pitch on it |

Session rule: **heuristic works without AI.** If Ollama is down, the desk still drafts forms and runs flows. Say that out loud.

## vs Monday / Zapier

- **Monday** — work boards; not a document ingest → OCR → classify → executable flow product.
- **Zapier** — glue between apps; brittle for Hebrew docs, signatures, desk ACLs, and “who owns this file now.”
- **DocFlow** — document-flow as the product: ingest → read → decide → act, with a desk UI operators can run live.

One sentence: *We’re not another board or another zap — we’re the pipe that moves the document from the field into the office system of record.*
