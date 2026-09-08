from __future__ import annotations

import re

TYPES = (
    (
        "invoice",
        (
            "invoice",
            "tax invoice",
            "bill to",
            "amount due",
            "subtotal",
            "vat",
            "total due",
            "invoice no",
            # Israeli / Hebrew invoice cues (lowercase haystack; Hebrew case-folds as itself)
            "חשבונית",
            "חשבונית מס",
            "מספר הקצאה",
            "הקצאה",
            "ח.פ",
            "ח.פ.",
            "עוסק מורשה",
            "מע\"מ",
            "מעמ",
            "ils",
            "₪",
        ),
    ),
    ("contract", ("agreement", "hereinafter", "party of the first", "terms and conditions", "governing law", "whereas", "הסכם", "חוזה")),
    ("identity", ("passport", "driver license", "date of birth", "national id", "issued by", "תעודת זהות", "דרכון")),
    ("receipt", ("receipt", "thank you for your purchase", "change due", "cashier", "קבלה")),
    ("statement", ("account statement", "opening balance", "closing balance", "transaction", "דף חשבון")),
    ("memo", ("memorandum", "internal memo", "from:", "re:", "מזכר")),
)


def classify_document(filename: str, text: str) -> dict:
    hay = f"{filename}\n{text}".lower()
    scores: dict[str, float] = {}
    for label, keywords in TYPES:
        hits = sum(1 for k in keywords if k.lower() in hay)
        scores[label] = hits / max(len(keywords), 1)
    label, score = max(scores.items(), key=lambda kv: kv[1])
    if score < 0.12:
        return {"label": "general", "confidence": 0.4, "scores": scores}
    return {"label": label, "confidence": min(0.97, 0.45 + score), "scores": scores}


# USD/EUR/GBP plus Israeli shekel (₪ / ILS / NIS)
MONEY = re.compile(
    r"(?:USD|EUR|GBP|ILS|NIS|\$|€|₪)\s?([0-9,]+\.?\d{0,2})|"
    r"([0-9,]+\.?\d{0,2})\s?(?:USD|EUR|GBP|ILS|NIS|₪)",
    re.I,
)
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
INV = re.compile(
    r"(?:invoice|inv)[#:\s-]+([A-Z0-9-]{4,})|"
    r"(?:מספר\s*(?:ה)?חשבונית)\s*[:#\-]?\s*([A-Z0-9-]{3,})|"
    r"חשבונית\s*(?:מס\s*)?(?:מספר|#|:)\s*([A-Z0-9-]{3,})",
    re.I,
)
COMPANY_ID = re.compile(r"(?:ח\.?\s*פ\.?|חפ|מספר\s*עוסק)\s*[:#]?\s*(\d{8,9})", re.I)
ALLOCATION = re.compile(r"(?:מספר\s*הקצאה|הקצאה|allocation\s*(?:no|number|#)?)\s*[:#]?\s*([A-Z0-9-]{5,})", re.I)


def extract_fields(text: str, classification: str) -> list[dict]:
    fields: list[dict] = []
    if m := INV.search(text):
        inv_val = next((g for g in m.groups() if g), None)
        if inv_val:
            fields.append({"name": "invoice_number", "value": inv_val, "confidence": 0.86})
    amounts: list[str] = []
    for m in MONEY.finditer(text):
        val = m.group(1) or m.group(2)
        if val:
            amounts.append(val)
    if amounts:
        fields.append({"name": "amount", "value": amounts[-1], "confidence": 0.8})
    if m := COMPANY_ID.search(text):
        fields.append({"name": "company_id", "value": m.group(1), "confidence": 0.88})
    if m := ALLOCATION.search(text):
        # Recognition only — not a live allocation API / validation claim
        fields.append({"name": "allocation_number", "value": m.group(1), "confidence": 0.82})
    dates = DATE.findall(text)
    if dates:
        fields.append({"name": "date", "value": dates[0], "confidence": 0.75})
    emails = EMAIL.findall(text)
    if emails:
        fields.append({"name": "counterparty_email", "value": emails[0], "confidence": 0.9})
    if classification == "contract":
        fields.append({"name": "document_kind", "value": "contract", "confidence": 0.7})
    if not fields:
        first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "untitled")
        fields.append({"name": "title", "value": first[:120], "confidence": 0.5})
    return fields
