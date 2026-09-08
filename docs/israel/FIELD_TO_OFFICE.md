# Field-to-office thesis

## Correction from the session

**Invoices are one example. Routing is the product.**

Do not let the pitch collapse into “DocFlow is an invoice OCR app.” The desk moves **any** operational document: site checklists, vendor onboarding, class summaries, AP packets, safety forms — content born in the periphery (field crews, site managers, sales agents, external affiliates, service providers, even customers) that arrives at the office shredded across WhatsApp, phone, and email.

## Opening sentence (use this)

**EN:** *In every organization, information is born in the field and arrives at the office shredded across WhatsApp, phone, and email. We turn it into a form that already knows the context, and route it to the right person and folder. Invoices are one example — with a shekel number attached.*

**HE:** *בכל ארגון יש מידע שנוצר בשטח ומגיע למשרד מרוסק בין ווטסאפ, טלפון ומייל. אנחנו הופכים אותו לטופס שכבר יודע את ההקשר, ומנתבים אותו לאדם ולתיקייה הנכונים. חשבוניות הן דוגמה אחת — עם מספר בשקלים.*

## Five layers checked in code (session)

| Layer | Session status in powerdoc |
|---|---|
| Intake | Field types exist; no file/camera/geo; **no offline / PWA / service worker** |
| Context | `auto` exists but mainly **date: today**; RAG shapes definition, does not fill instances |
| Routing | One fixed destination per form; automation match by `form_id` — no answer-based branching |
| Permissions | Tenant filter on lists; `permissions.py` written but lightly wired |
| Accumulation | Structured records exist — missing richer operator screens |

None of these gaps are architectural. Engine, multi-tenancy, evidence, and org structure exist — this is wiring.

### Form born from internal knowledge

- **Level 1** (knowledge shapes the form) — largely built.
- **Level 2** (knowledge **fills** the form — site already known, contractor, superintendent) — highest ROI gap (~a week per session).
- **Level 3** (form born from an event) — thin; `step_create_form`-class work on existing engine.

## Bridges called out

| Bridge | Session note |
|---|---|
| **WhatsApp** | Natural Israeli field channel — photo in → submission + completion link; not the demo surface for tomorrow |
| **Offline PWA** | Category table stakes (SafetyCulture / GoCanvas / Fulcrum / TrueContext all have it) — roadmap, not a claim |
| Public fill + sign | Exists in powerdoc today — good for “office receives a completed form” |

Field-app comps price ~**$24–43/user/month** vs general form builders ~**$34/org/month** — category is worth more per customer; all are foreign English SaaS → Hebrew + local install remain differentiation.

## Pitch framing

1. Open with **movement**: field content → office routing (sentence above).
2. Show **one** concrete path (form compose and/or invoice upload) as proof.
3. Bring invoices as **example #2** with the exposure number (wedge).
4. Close ask: CPA intros for the health-check wedge.
