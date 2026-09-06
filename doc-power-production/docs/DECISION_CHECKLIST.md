# Doc-Power Decision Checklist

Short, actionable checklist for UI settings MVP, connector roadmap, and SMB sizing. Grounded in current state: backend microservices scaffold (auth, documents, OCR, workflows, notifications, analytics); **no frontend UI**, **no AD/LDAP/SSO**, **no multi-connector framework** yet.

---

## 1. UI settings MVP

Ship a settings surface before deep product chrome. Prioritize configuration IA over feature sprawl.

### Must ship
- [ ] **Appearance** — theme, density, brand/logo accents; live preview + Save / Reset
- [ ] **IA shells** — Connectors, Users, Retention sections (even if some panes are stubbed)
- [ ] **Progressive disclosure** — advanced options collapsed; defaults safe for admins
- [ ] **RBAC-gated options** — hide/disable what the role cannot change
- [ ] **a11y** — keyboard, focus, contrast, labels on all controls
- [ ] **Mobile-friendly settings** — usable on phone/tablet without a separate admin app

### Explicitly defer
- [ ] Full connector sync UI (use roadmap §2)
- [ ] AD/SSO admin wizards (identity is separate; see §2 / §3)
- [ ] Analytics dashboards and workflow builders inside settings

### Done when
- An admin can change appearance, see preview, save/reset, and navigate Connectors / Users / Retention without dead ends or ungated sensitive controls.

---

## 2. Connector roadmap

Treat **identity** and **content** as separate connector classes.

| Phase | Focus | Checklist |
| --- | --- | --- |
| **A – Framework** | Multi-connector scaffold | [ ] Connector registry + config model [ ] Health/status [ ] Job enqueue via RabbitMQ [ ] Per-tenant enable/disable |
| **B – Identity (AD)** | AuthN/AuthZ only | [ ] LDAP/LDAPS **or** Entra OIDC/SAML [ ] Group → role mapping [ ] Optional SCIM provisioning [ ] *Not* a content sync path |
| **C – Content (few active)** | Controlled concurrency | [ ] Configure many sources OK [ ] Cap **2–8 concurrent sync jobs / tenant** [ ] Respect source rate limits, OCR, I/O, worker pool |
| **D – Scale-out** | Ops levers | [ ] Per-connector concurrency knobs [ ] Backpressure / pause [ ] Retry & DLQ visibility |

### Design rules
- [ ] Many connectors **configured** ≠ many **actively syncing**
- [ ] AD/Entra = identity connector; Drive/SharePoint/email/etc. = content connectors
- [ ] OCR and RabbitMQ workers are first-class capacity limits alongside source APIs

---

## 3. Sizing sheet (~50 employees / 10 years)

### Primary storage (usable document corpus)

| Profile | Rough range |
| --- | --- |
| Light | **0.5–1 TB** |
| Typical | **1.5–2.5 TB** |
| Heavy | **4–7.5 TB** |

### Add-ons (stack on primary)
| Factor | Uplift |
| --- | --- |
| Versions + trash | **+20–50%** |
| OCR / search indexes | **+10–30%** |
| Backups / DR copies | **×2–3** |

**Planning default (typical SMB):** ~**2–3 TB usable**; ~**5–8 TB** with DR.

### Concurrent connectors & AD notes
- [ ] Plan **2–8 concurrent sync jobs per tenant**, not one-per-connector
- [ ] Size workers for OCR + I/O + queue depth, not configured connector count
- [ ] AD path: LDAP/LDAPS on-net **or** Entra OIDC/SAML; map groups→roles; SCIM optional
- [ ] Keep identity out of content sync capacity math

### Local vs cloud (pick / hybrid)

| Factor | Ask |
| --- | --- |
| Compliance / residency | Data must stay on-prem or in-region? |
| AD / network | Domain join, LDAPS reachability, private link? |
| Ops burden | Who patches K8s, Mongo, Redis, RabbitMQ? |
| Cost shape | CapEx storage vs OpEx object storage + egress |
| OCR scale | Bursty CPU/GPU — cloud easier? |
| Latency | Users near office LAN or distributed? |
| Upgrades | Who owns version cadence and rollback? |

- [ ] Document the choice (local / cloud / **hybrid** — hybrid is common)
- [ ] Align retention settings UI (§1) with the storage tier you fund here
)
