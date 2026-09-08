# Tomorrow’s demo runbook / ראנבוק לדמו מחר

Stopwatch. Business-feasibility room (investor/partner) — not a feature dump.  
Login: `oren@gcs-tech.org` / `DocFlow!2026`

---

## Opening sentence (0:00–0:45) — memorize

**EN:** *In every organization, information is born in the field and arrives at the office shredded across WhatsApp, phone, and email. We turn it into a form that already knows the context, and route it to the right person and folder. Invoices are one example.*

**HE:** *בכל ארגון יש מידע שנוצר בשטח ומגיע למשרד מרוסק בין ווטסאפ, טלפון ומייל. אנחנו הופכים אותו לטופס שכבר יודע את ההקשר, ומנתבים אותו לאדם ולתיקייה הנכונים. חשבוניות הן דוגמה אחת.*

Shorter fallback: *Documents should move — from the field to the office — without dying in WhatsApp and Excel. Routing is the product.*

---

## Minute plan

| Min | Do / עשו | Don’t / אל |
|---|---|---|
| **0–1** | Landing → sign in. Say the opening sentence. | Don’t apologize for “early product.” |
| **1–3** | Overview: live counts (library / ready / runs). One breath on field→office. | Don’t linger on digest prose. |
| **3–5** | Documents → drop a small `.txt` invoice → status **ready**, class **invoice**. Open it: text + fields. | Don’t start a long OCR philosophy talk. |
| **5–6** | **Minute-6 moment:** Form builder → paste the **safe prompt** (below) → desk replies + fields appear **without** waiting on AI. | Don’t say “the LLM built this” if Ollama is off — say heuristic level 0–1. |
| **6–8** | Publish / mention public fill+sign + Send to. Optional: Automations / Flows chips with real run history. | Don’t open Connectors unless you label **sandbox**. |
| **8–10** | Zoom out: wedge = בדיקת בריאות חשבוניות ₪8–15k via CPAs; Ram-Control = feed, don’t compete. | Don’t promise allocation-number / BKMVDATA / Priority write-back as shipped. |
| **10–12** | **Ask** (below). Stop. | Don’t ask for money. |

---

## Safe form prompt (copy-paste) — session exact

```
invoice approval form with vendor, invoice number, amount, date, email, signature
```

Alternate (e2e-tested student day-summary):

```
day summary for students with automatic today date, email, was the student in class, which topic was best explained, rate today's class, and mandatory signature
```

---

## Minute-6 moment (script)

**EN:** *Watch — I describe the form in one sentence. The desk harvests fields immediately. That’s level 0–1: useful without a model. AI is an upgrade, not a gate.*

**HE:** *שימו לב — מתארים את הטופס במשפט אחד. השולחן שולף שדות מיד. זה רמה 0–1: שימושי בלי מודל. AI הוא שדרוג, לא תנאי.*

---

## Ask (end)

**EN:** *I’m not asking for a check today. I need **two introductions** to CPAs who would buy a paid invoice health check (בדיקת בריאות חשבוניות, ₪8–15k).*

**HE:** *לא מבקשים כסף היום. צריכים **שתי היכרות** לרואי חשבון / משרדי הנהלת חשבונות שיקנו בדיקת בריאות חשבוניות בתשלום (₪8–15 אלף).*

If they raise investment first — let them.

---

## Pre-flight checklist (30 min before)

- [ ] API + web up; seed user works
- [ ] Sample `.txt` invoice on the desktop
- [ ] Safe prompt in clipboard
- [ ] Language switcher: know that HE = 30 keys + RTL shell, not full UI
- [ ] If you must show Connectors: say **demo sandbox** out loud
- [ ] Do **not** demo `doc-power-local-k8s` gateway work — different repo
- [ ] Run this script **once** with a stopwatch the night before — then stop coding

---

## If something breaks

| Break | Recovery |
|---|---|
| Overview slow / empty | Refresh once; numbers come from DB. Digest is heuristic (no Ollama wait). |
| Compose empty fields | Re-paste the **exact** safe prompt above. |
| Connectors looks “fake” | Admit sandbox; pivot to Documents + Forms. |
| Someone asks allocation / BKMVDATA | “That’s the integration roadmap after the health-check wedge.” |
