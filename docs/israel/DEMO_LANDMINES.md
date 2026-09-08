# Demo landmines — verified against `powerdoc` (this repo)

Verified on branch `cursor/docflow-production-platform-5707` against live code.  
**Out of scope:** `doc-power-local-k8s` / gateway-missing-routes (separate repo; not PR #1).

Claude’s pitch-prep HTML listed four landmines. Re-checked here:

## 1. Analytics `/analytics/summary` — slow `generate()`?

| | |
|---|---|
| **Was (session)** | `apps/api/app/routers/analytics.py` called `generate("analytics", …)` on every summary. Overview **and** Analytics both hit this on load. If Ollama is up, `generate` can block up to **~90s** (`apps/api/app/llm.py`). |
| **Now** | Digest uses **`fast_text()`** — heuristic only, **never** calls Ollama. Counts/charts still come from real tables. |
| **Say in the room** | Numbers are live from the desk DB. The one-line digest is a quick status line — not a live LLM essay. |
| **Still** | Prefer Overview over deep Analytics prose; don’t linger on the digest sentence. |

## 2. Form compose — heuristic, not full LLM

| | |
|---|---|
| **Truth** | Fields are built by `harvest_fields()` in `apps/api/app/engine/formgen.py` (regex / keyword heuristics). LLM (Ollama) only optionally rewrites the **chat reply** when `use_llm=True` and Ollama is up. |
| **Safe prompt (session exact)** | `invoice approval form with vendor, invoice number, amount, date, email, signature` — verified: harvests vendor, invoice number, amount, date, email, signature. |
| **Safe alternate (e2e-tested)** | `day summary for students with automatic today date, email, was the student in class, which topic was best explained, rate today's class, and mandatory signature` |
| **Hebrew alternate** | `טופס אישור חשבונית` — invoice-shaped fields via heuristics. |
| **Say** | “The desk drafts fields without waiting on a model. Connect Ollama later for richer chat.” |

## 3. Connectors Sync — SANDBOX fake files?

| | |
|---|---|
| **Truth** | **Yes.** `apps/api/app/routers/connectors.py` still has `SANDBOX` fake Drive/365/local titles. Sync upserts those into RAG. `local_db` prefers real OCR rows when present, else falls back to sandbox. |
| **UI** | Connectors page is labeled **Demo sandbox** so you don’t imply live OAuth. |
| **Say** | “This sync is a sandbox feed for the demo. Production connects real Drive / 365.” |
| **Don’t** | Let an investor discover fake Sync filenames themselves. |

## 4. Hebrew i18n — how many keys? RTL where?

| | |
|---|---|
| **Keys** | **30** string keys per locale in `apps/web/src/i18n.ts` (nav + form chrome). Most page body copy is still English. |
| **RTL** | **Not** public-form-only (Claude HTML was slightly stale). `AppShell` sets `document.documentElement.dir` for `he`/`ar` on the **whole desk**. Public `FillForm` also sets dir from `form.language`. |
| **Say** | “Hebrew chrome + RTL shell are on; full Hebrew product copy is still thin — 30 keys.” |
| **Don’t** | Switch the main desk to HE and claim a fully localized product. |

## Quick do / don’t

| Do | Don’t |
|---|---|
| Form builder with a **safe** prompt above | Claim full Hebrew product or live Drive OAuth |
| Upload a `.txt` invoice → ready / class invoice | Open Connectors Sync and call sandbox “production” |
| Show flows / automations run history | Spend the pitch inside Analytics digest prose |
| Ask for 2 CPA intros | Ask for a wire / LOI money close tomorrow |
