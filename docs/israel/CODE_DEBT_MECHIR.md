# Code debt before “מכיר” (sellable Israel wedge)

Session estimate to a credible sellable wedge: **~10–12 weeks** total. That is the number to give if asked. Do **not** invent calendar dates beyond what the session said.

## 16-item summary (session ordering)

| Bucket | Items (session) | Rough |
|---|---|---|
| **Sales blockers** | Hebrew in the engine; מספר הקצאה | ~2 weeks + ~1 week |
| **Production blockers** | Async pipeline; Alembic; S3 storage; multi-tenant holes; config hardening | ~1 week + days |
| **Product unlocks** | Five form components (PDF, email, file field, scheduler, evidence certificate); form builder that truly uses the model | ~2 weeks + ~3 days |
| **Leverage** | BKMVDATA / קובץ אחיד parser; write-back connector (morning/iCount first) | ~1 week + ~1 week |

## Must-have before you call it מכיר (mapped to this repo)

| Area | Today (powerdoc) | Need |
|---|---|---|
| Connectors | `SANDBOX` fake Drive/365 sync | Real OAuth + file pull |
| Invoice health check | Manual demo narrative | Checklist / exposure report CPAs pay ₪8–15k for |
| Hebrew OCR / מספר הקצאה / BKMVDATA | Not shipped (`classify.py` still USD/EUR/$) | Read path that survives a CPA review |
| Write-back | None | morning/iCount first; Priority OData later |
| i18n | **30** HE keys; RTL on desk + public form | Product-copy coverage beyond nav/chrome |
| Field channels | Public web fill | WhatsApp bridge; offline PWA |
| Ram-Control | Narrative only | Read-only SQL views / feed pattern with a design partner |
| Context fill (level 2) | RAG shapes definition only | Pre-fill site / contractor / superintendent on instances |

## Explicitly later / out of scope for this PR

- Competing with Top Ramdor UI
- Claiming full חשבוניות ישראל issuance
- Gateway work from `doc-power-local-k8s` (`feature/gateway-missing-routes`) — **separate repo**, not powerdoc PR #1

## Sell ladder (keep honest)

1. **This week’s room:** feasibility + demo + ask for CPA intros  
2. **Next weeks:** paid health-check delivery kit + first real connector  
3. **Following weeks:** BKMVDATA/read lever + morning/iCount write-back experiments  

Heuristic desk (forms, flows, automations) is already demoable — that is level 0–1. “מכיר” for the Israel wedge means **paid CPA motion + real integrations**, not more screenshots.

Session closing advice for tonight: **don’t push code** — run the stopwatch script once end-to-end, then stop.
