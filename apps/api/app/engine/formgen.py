from __future__ import annotations

import re
from uuid import uuid4


FIELD_TYPES = (
    "heading",
    "text",
    "textarea",
    "number",
    "date",
    "email",
    "phone",
    "dropdown",
    "radio",
    "checkbox",
    "yesno",
    "signature",
)


def _f(type_: str, label: str, required: bool = False, options: list[str] | None = None, help_: str = "") -> dict:
    return {
        "id": uuid4().hex[:8],
        "type": type_,
        "label": label,
        "required": required,
        "options": options or [],
        "help": help_,
        "placeholder": "",
    }


TEMPLATES = {
    "en": {
        "invoice": {
            "name": "Invoice approval",
            "topic": "invoice",
            "fields": [
                _f("heading", "Invoice details"),
                _f("text", "Vendor", True),
                _f("text", "Invoice number", True),
                _f("number", "Amount due", True),
                _f("date", "Due date", True),
                _f("dropdown", "Department", True, ["Finance", "Operations", "Legal"]),
                _f("textarea", "Notes"),
                _f("signature", "Approver signature", True),
            ],
        },
        "vendor": {
            "name": "Vendor onboarding",
            "topic": "vendor",
            "fields": [
                _f("heading", "Company"),
                _f("text", "Legal name", True),
                _f("text", "Tax ID", True),
                _f("email", "Billing email", True),
                _f("phone", "Phone"),
                _f("textarea", "Address", True),
                _f("yesno", "Are you VAT registered?", True),
                _f("signature", "Authorized signature", True),
            ],
        },
        "site": {
            "name": "Site check",
            "topic": "site",
            "fields": [
                _f("heading", "Visit"),
                _f("dropdown", "Site", True, ["HQ", "Warehouse", "Client site"]),
                _f("date", "Visit date", True),
                _f("radio", "Condition", True, ["Good", "Needs work", "Unsafe"]),
                _f("textarea", "Findings", True),
                _f("signature", "Inspector sign-off", True),
            ],
        },
        "ack": {
            "name": "Policy acknowledgement",
            "topic": "ack",
            "fields": [
                _f("heading", "Acknowledgement"),
                _f("text", "Full name", True),
                _f("email", "Email", True),
                _f("yesno", "I have read the policy", True),
                _f("signature", "Signature", True),
            ],
        },
        "generic": {
            "name": "Request form",
            "topic": "general",
            "fields": [
                _f("text", "Your name", True),
                _f("email", "Email", True),
                _f("textarea", "What do you need?", True),
                _f("signature", "Signature"),
            ],
        },
    },
    "he": {
        "invoice": {
            "name": "אישור חשבונית",
            "topic": "invoice",
            "fields": [
                _f("heading", "פרטי חשבונית"),
                _f("text", "ספק", True),
                _f("text", "מספר חשבונית", True),
                _f("number", "סכום לתשלום", True),
                _f("date", "תאריך פרעון", True),
                _f("dropdown", "מחלקה", True, ["כספים", "תפעול", "משפטי"]),
                _f("textarea", "הערות"),
                _f("signature", "חתימת מאשר", True),
            ],
        },
        "vendor": {
            "name": "קליטת ספק",
            "topic": "vendor",
            "fields": [
                _f("heading", "חברה"),
                _f("text", "שם משפטי", True),
                _f("text", "ח.פ / ע.מ", True),
                _f("email", "אימייל לחשבוניות", True),
                _f("phone", "טלפון"),
                _f("textarea", "כתובת", True),
                _f("yesno", "עוסק מורשה?", True),
                _f("signature", "חתימה מורשית", True),
            ],
        },
        "generic": {
            "name": "טופס בקשה",
            "topic": "general",
            "fields": [
                _f("text", "שם מלא", True),
                _f("email", "אימייל", True),
                _f("textarea", "מה נדרש?", True),
                _f("signature", "חתימה"),
            ],
        },
    },
}


def pick_topic(prompt: str) -> str:
    p = prompt.lower()
    if any(w in p for w in ("invoice", "חשבונית", "ap ", "vendor bill")):
        return "invoice"
    if any(w in p for w in ("vendor", "ספק", "supplier", "onboard")):
        return "vendor"
    if any(w in p for w in ("site", "אתר", "inspection", "safety")):
        return "site"
    if any(w in p for w in ("policy", "ack", "acknowledge", "מדיניות")):
        return "ack"
    return "generic"


def compose_form(prompt: str, language: str = "en", context_fields: list[str] | None = None) -> dict:
    lang = language if language in TEMPLATES else "en"
    topic = pick_topic(prompt)
    pack = TEMPLATES[lang]
    tmpl = pack.get(topic) or pack.get("generic") or TEMPLATES["en"]["generic"]
    fields = [dict(f, id=uuid4().hex[:8]) for f in tmpl["fields"]]
    extra = context_fields or []
    for name in extra[:8]:
        label = name.replace("_", " ").title()
        if not any(f["label"].lower() == label.lower() for f in fields):
            fields.insert(-1, _f("text", label, False))
    if "dropdown" in prompt.lower() or "רשימה" in prompt:
        if not any(f["type"] == "dropdown" for f in fields):
            fields.insert(-1, _f("dropdown", "Choose one" if lang != "he" else "בחירה", False, ["A", "B", "C"]))
    return {
        "name": tmpl["name"],
        "topic": tmpl["topic"],
        "description": prompt.strip()[:400],
        "language": lang,
        "fields": fields,
    }


def fields_from_chunks(chunks: list[dict]) -> list[str]:
    names: list[str] = []
    blob = " ".join(c.get("text", "") for c in chunks)
    for m in re.findall(r"\b([A-Za-z][A-Za-z_ ]{2,40}):", blob):
        n = m.strip()
        if n not in names:
            names.append(n)
    for key in ("invoice_number", "amount", "vendor", "date", "governing law"):
        if key.replace("_", " ") in blob.lower() and key not in names:
            names.append(key)
    return names[:10]
