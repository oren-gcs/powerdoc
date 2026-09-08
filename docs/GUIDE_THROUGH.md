# Guide-through (desk path)

Short script for demos and onboarding. Stopwatch-friendly. Strategy / ask / landmines: [`docs/israel/TOMORROW_DEMO.md`](./israel/TOMORROW_DEMO.md).

**Login:** `oren@gcs-tech.org` / `DocFlow!2026` · **Desk:** http://localhost:5173

---

## Path (≈10 minutes)

| Step | Where | Say / do |
|------|--------|----------|
| 1 | Landing → Sign in | Field info arrives shredded; DocFlow turns it into a routed form and folder. |
| 2 | Overview | Live library / ready / flow counts. Point at the **search** bar: forms, processes, documents, connectors. |
| 3 | Documents | Drop a small `.txt` invoice → **ready**, class **invoice**. Open: text + fields. |
| 4 | Form builder | Paste: `invoice approval form with vendor, invoice number, amount, date, email, signature` → fields appear. Add a recipient email under **Send to**. |
| 5 | Publish | Show personal link. Optional: open `/f/…` in a private window, fill + sign, submit once (link closes). |
| 6 | Answered | Submission log + digest actions. |
| 7 | Flows / Automations | Real run history / fire counts — not a fake queue. |
| 8 | Connectors (optional) | Label **demo sandbox** for Drive/365 sync. Show **Ollama → Use this model** only if `ollama serve` is up. |

Stop. Hand off to Q&A or the Israel runbook ask if this is a GTM room.

---

## One-liners

- **Compose without a model:** “Useful at heuristic level — AI is an upgrade, not a gate.”
- **Personal links:** “Each person gets their own link; after they answer, that link closes.”
- **Connectors:** “Sandbox feed for demos; production OAuth is roadmap. Ollama here is real.”

---

## Pre-flight

- [ ] API + web up; demo login works  
- [ ] Sample invoice `.txt` ready  
- [ ] Safe prompt on clipboard  
- [ ] Search finds a seeded form or document by name  
- [ ] If showing Connectors: say sandbox out loud  
