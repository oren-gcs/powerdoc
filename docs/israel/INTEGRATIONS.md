# Israeli integrations landscape

Substance from the GTM session — **targets and sequencing**, not shipped features in `powerdoc` today.

## חשבוניות ישראל / מספר הקצאה

- Israel’s e-invoicing regime (allocation number / מספר הקצאה) is a **compliance pressure** buyers already feel.
- Session note: from **1 Jun 2026** the threshold is **₪5,000** — without an allocation number the recipient cannot deduct **18% VAT**. Treat as timing/context for CFOs / CPAs, **not** a DocFlow feature claim tonight.
- Napkin math from the session (illustrative): ~300 invoices/month at average ₪8,000 with **2%** problematic → **~₪103,680/year** exposure. Useful in the room; not a product metric in the app.
- DocFlow’s near-term commercial use of this pressure is the **invoice health check** wedge (see [COMMERCIAL_WEDGE.md](./COMMERCIAL_WEDGE.md)), not “we issue allocation numbers tonight.”

### Code gap (this repo)

`apps/api/app/classify.py` money regex is `USD|EUR|GBP|$|€` only — **no ₪**, no ח.פ., no `"חשבונית מס"`, no מספר הקצאה. The ingest pipeline exists; the Israel-specific step does not.

## BKMVDATA — read lever

- **BKMVDATA** (קובץ אחיד / open-book style dump) is the **read** path into client books.
- Session: every Israeli bookkeeping package has been required to export it since **2006** (חשבשבת, Priority, רווחית, SAP B1, iCount, …). One parser ≈ read from most systems without per-vendor APIs — including disconnected on-prem.
- Positioning: ingest / normalize / flag — **not** replace the ERP of record on day one.
- Parser / Hebrew OCR / allocation-number validation are **not** trivial stubs to ship for tomorrow’s pitch; treat as roadmap.

## Write-back order: morning / iCount → Priority OData

Recommended sequence from the session:

1. **morning** / **iCount** — lighter SMB accounting APIs; first write-back experiments.
2. **Priority** via **OData** — heavier ERP write-back once the read + routing story is trusted.

Do not open a live demo by promising Priority write-back. Say: *read + route first; write-back follows the wedge.*

## CRM / ERP / BI landscape (how to talk about it)

| Layer | Role for DocFlow |
|---|---|
| Field capture (forms, WhatsApp, photo) | **Intake** — DocFlow strength |
| Desk / routing / classification | **Product core** — “documents should move” |
| Accounting (iCount, morning, Priority, …) | **Systems of record** — integrate, don’t replace |
| CRM / BI | Downstream consumers of **clean routed events** |

Framing line: *We sit between the field and the office systems — we don’t ask the client to rip out Priority or Ramdor.*
