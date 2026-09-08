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

## 3. Connectors Sync — demo catalog?

| | |
|---|---|
| **Truth** | Drive / 365 expose a **demo catalog** (`GET …/browse`) — Source → Folder → Files — not live OAuth. `POST …/sync` with `{paths}` upserts **selected** files into RAG. `local_db` browses real tenant documents / OCR (sample fallback when empty). |
| **UI** | Connectors → **Browse** opens the picker; Sync selected only after file checkboxes. Labeled **Demo catalog**. |
| **Say** | “This is a demo catalog so we can show folder/file pick. Production connects real Drive / 365.” |
| **Don’t** | Let an investor discover fake Sync filenames themselves. |

## 4. Hebrew i18n — how many keys? RTL where?

| | |
|---|---|
| **Keys** | Expanded beyond nav chrome in `apps/web/src/i18n.ts` (~130 HE keys): Forms list, FormBuilder inspector (Save / Delete / Label / Mandatory / Choices / …), FillForm, Answered, Connectors labels. |
| **RTL** | `AppShell` sets `document.documentElement.dir` for `he`/`ar` on the **whole desk**. Public `FillForm` also sets dir from `form.language`. |
| **Engine** | `classify.py` recognizes ₪/ILS, חשבונית, ח.פ., מספר הקצאה (field extraction only — **not** a live allocation API). Form compose with `language=he` yields Hebrew field labels. |
| **Say** | “Hebrew desk chrome + Forms/Builder/Fill + RTL; invoice heuristics know Israeli terms.” |
| **Don’t** | Claim full product localization or live מספר הקצאה validation / BKMVDATA. |

## Quick do / don’t

| Do | Don’t |
|---|---|
| Form builder with a **safe** prompt above | Claim full Hebrew product or live Drive OAuth |
| Upload a `.txt` invoice → ready / class invoice | Open Connectors Sync and call sandbox “production” |
| Show flows / automations run history | Spend the pitch inside Analytics digest prose |
| Ask for 2 CPA intros | Ask for a wire / LOI money close tomorrow |
