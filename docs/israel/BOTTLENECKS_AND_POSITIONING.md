# Bottlenecks, AI ladder, positioning

## Bottlenecks (session)

1. **Field → office handoff** — photos, WhatsApp, paper, and ad-hoc Excel never become a routed desk object.
2. **Invoice / compliance noise** — missing fields, missing allocation context, no health signal before the CPA sees the mess.
3. **Integration theater** — Monday/Zapier-style wiring without a document-native ingest → classify → route engine.
4. **Demo honesty** — claiming “AI” where the desk is still heuristic, or “connectors” where sync is sandbox (see [DEMO_LANDMINES.md](./DEMO_LANDMINES.md)).

### Session stats (cite carefully)

- ERP implementations: **68%** fail; **189%** budget overrun; three causes ≈ **75%** of failures — change mgmt **42%**, data migration **38%**, inexperienced team **35%** (Panorama 2026, per session).
- AI projects: RAND **80.3%** deliver no value; Gartner **60%** may shut by end-2026 for data-foundation reasons (per session).
- Session punchline: **none of the top failure causes are “the code”** — good news if you sell process + gatekeepers, not magic models.

### #1 technical bottleneck (Israel)

**Entity identity.** `"א.ב. שיווק בע״מ"` / `"א.ב שיווק"` / ח.פ. with a missing digit → four vendors instead of one. Rule: **ח.פ. as unique key with check-digit validation** — never name-match alone.

### #1 business bottleneck (Israel)

The **CPA / bookkeeper is the gatekeeper** — they hold the system, not the end client. Recruit them as an ally in meeting one (see [COMMERCIAL_WEDGE.md](./COMMERCIAL_WEDGE.md)).

## AI ladder — sell levels 0–1 first

| Level | What it is | Demo / sell posture |
|---|---|---|
| **0** | Deterministic routing, folders, forms, workflow steps | Ship and show |
| **1** | Heuristic compose / classify (no LLM required) | **Sell this first** — form builder `harvest_fields` already works offline |
| **2+** | Local Ollama / richer agents | Optional depth; never block the pitch on it |

Session rule: **heuristic works without AI.** `_heuristic` in `apps/api/app/llm.py` is level 0. If Ollama is down, the desk still drafts forms and runs flows. Say that out loud. Most failures come from trying to sell level 4.

## vs Monday / Zapier

- **Monday** — work boards; a document is an attachment on a row — not a document ingest → OCR → classify → executable flow product.
- **Zapier** — glue between apps; brittle for Hebrew docs, signatures, desk ACLs, and “who owns this file now”; data often leaves to a foreign cloud.
- **DocFlow** — document-flow as the product: ingest → read → decide → act, with a desk UI operators can run live.

Session line: *Monday manages your tasks. We manage the documents behind them — in Hebrew, on your server, with an audit trail for every decision.*
