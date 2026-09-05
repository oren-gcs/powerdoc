from __future__ import annotations

import re

TYPES = (
    ("invoice", ("invoice", "tax invoice", "bill to", "amount due", "subtotal", "vat", "total due", "invoice no")),
    ("contract", ("agreement", "hereinafter", "party of the first", "terms and conditions", "governing law", "whereas")),
    ("identity", ("passport", "driver license", "date of birth", "national id", "issued by")),
    ("receipt", ("receipt", "thank you for your purchase", "change due", "cashier")),
    ("statement", ("account statement", "opening balance", "closing balance", "transaction")),
    ("memo", ("memorandum", "internal memo", "from:", "re:")),
)


def classify_document(filename: str, text: str) -> dict:
    hay = f"{filename}\n{text}".lower()
    scores: dict[str, float] = {}
    for label, keywords in TYPES:
        hits = sum(1 for k in keywords if k in hay)
        scores[label] = hits / max(len(keywords), 1)
    label, score = max(scores.items(), key=lambda kv: kv[1])
    if score < 0.12:
        return {"label": "general", "confidence": 0.4, "scores": scores}
    return {"label": label, "confidence": min(0.97, 0.45 + score), "scores": scores}


MONEY = re.compile(r"(?:USD|EUR|GBP|\$|€)\s?([0-9,]+\.\d{2})")
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
INV = re.compile(r"(?:invoice|inv)[#:\s-]+([A-Z0-9-]{4,})", re.I)


def extract_fields(text: str, classification: str) -> list[dict]:
    fields: list[dict] = []
    if m := INV.search(text):
        fields.append({"name": "invoice_number", "value": m.group(1), "confidence": 0.86})
    amounts = MONEY.findall(text)
    if amounts:
        fields.append({"name": "amount", "value": amounts[-1], "confidence": 0.8})
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
