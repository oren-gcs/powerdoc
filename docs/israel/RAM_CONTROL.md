# Complex systems — Ram-Control

## Stance (session)

- **Ram-Control** (Apoint Systems) = contractor / execution ops: HQ + field, safety, QA, procurement, schedule, budget, contracts, subcontractors, mobile reporting. Session price band ~**₪50–100k**; vendor scale ~15–20 people.
- Declared stack (session): **Vue | Access | SQL**. **No documented public API** — that is good news: ask for a **`db_datareader`** user + **read-only views**, then read. Easier than many cloud SaaS APIs.
- Three warnings: **read-only forever**; document the schema (it will change); get **written** confirmation from Apoint that this does not violate license.
- DocFlow does **not** compete with **Top Ramdor** (work diary + document mgmt; deep public-sector / bank footprint; publishes external interfaces). If you pitch as “construction project management,” you lose that comparison.

## Open doors

1. **Feed, don’t replace** — Ramdor / Ram-Control shine once data is tidy. They are weak **before**: crumpled delivery notes, subcontractor bookkeeping certificates, lab results, partial accounts, WhatsApp photos. Language: *we feed them*.
2. **Subcontractor / multi-prime wedge** — one sub feeds many primes, each with different document expectations. Nobody sells *to* the sub. One capture → many target-format packs; 10–50 person org, owner decision, no procurement committee.

## What to build (generic, not “Ram-Control connector”)

1. External **read** source (also covers חשבשבת + BKMVDATA)
2. **Anchor entity** (project / site / order) linking documents to external keys
3. **Output engine** in the target format

After that, each new system is ~two days of config, not a two-week project.

## Live-room language

> We integrate beside Ram-Control. We don’t rip it out. We make the documents that should already be in those views arrive clean and on time.
