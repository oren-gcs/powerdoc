# Israeli integrations landscape

Substance from the GTM session — **targets and sequencing**, not shipped features in `powerdoc` today.

## חשבוניות ישראל / מספר הקצאה

- Israel’s e-invoicing regime (allocation number / מספר הקצאה) is a **compliance pressure** buyers already feel.
- Session note: **June 2026** threshold at **₪5,000** — use as timing context when speaking to CFOs / CPAs, not as a DocFlow feature claim.
- DocFlow’s near-term commercial use of this pressure is the **invoice health check** wedge (see [COMMERCIAL_WEDGE.md](./COMMERCIAL_WEDGE.md)), not “we issue allocation numbers tonight.”

## BKMVDATA — read lever

- **BKMVDATA** (accounting export / open-book style dump) is the **read** path into client books.
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
