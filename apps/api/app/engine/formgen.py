from __future__ import annotations

import json
import re
from uuid import uuid4

from app.llm import generate, ollama_status


def _f(type_: str, label: str, required: bool = False, options: list[str] | None = None, help_: str = "", auto: str = "") -> dict:
    return {
        "id": uuid4().hex[:8],
        "type": type_,
        "label": label,
        "required": required,
        "options": options or [],
        "help": help_,
        "placeholder": "",
        "auto": auto,
    }


def _norm(text: str) -> str:
    t = text.lower()
    for a, b in (
        ("summery", "summary"),
        ("summarry", "summary"),
        ("todat", "today"),
        ("signture", "signature"),
        ("manditory", "mandatory"),
    ):
        t = t.replace(a, b)
    return t


def split_clauses(prompt: str) -> list[str]:
    parts = re.split(r"[,;\n]|(?:\s+and\s+)", prompt)
    return [re.sub(r"\s+", " ", p).strip(" .") for p in parts if p and p.strip(" .")]


def interpret_clause(clause: str) -> tuple[dict | None, str, str]:
    raw = clause.strip()
    c = _norm(raw)
    if not c:
        return None, "", ""

    purpose = any(w in c for w in ("summary", "form for", "to students", "for students", "day summary", "class summary"))
    if purpose and not any(w in c for w in ("rate", "signature", "email", "topic", "attendance", "in class")):
        return None, f"form purpose: {raw}", ""

    if "date" in c and any(w in c for w in ("auto", "automatic", "today", "now")):
        return _f("date", "Date", True, help_="Filled automatically with today", auto="today"), "date (automatic today)", ""
    if re.search(r"\bdate\b", c) and "due" not in c:
        return _f("date", "Date", True), "date", ""

    if any(w in c for w in ("signature", "sign off", "sign-off", "חתימה")):
        return _f("signature", "Signature", True), "signature (mandatory)", ""

    if "email" in c or "e-mail" in c or "אימייל" in c:
        return _f("email", "Email", True, help_="Filled by the person completing the form"), "email (by the user)", ""

    if any(w in c for w in ("in class", "attendance", "present", "was the student", "did the student")):
        return _f("yesno", "Was the student in class?", True), "attendance (was the student in class)", ""

    if "topic" in c or "explained" in c or "lesson" in c:
        return _f("textarea", "Which topic was best explained?", True), "best-explained topic", ""

    if any(w in c for w in ("rate", "rating", "stars", "score")) and any(w in c for w in ("class", "today", "lesson", "session")):
        return _f("radio", "Rate today's class", True, ["1", "2", "3", "4", "5"]), "rate today's class (1–5)", ""
    if "rate" in c or "rating" in c:
        return _f("radio", "Rating", True, ["1", "2", "3", "4", "5"]), "rating", ""

    if "dropdown" in c or "רשימה" in c:
        return _f("dropdown", "Choose one", False, ["A", "B", "C"]), "dropdown", ""

    if any(w in c for w in ("phone", "טלפון")):
        return _f("phone", "Phone"), "phone", ""

    if len(c.split()) <= 3 and any(w in c for w in ("name", "full name", "student name")):
        return _f("text", "Student name", True), "student name", ""

    if len(c) < 8:
        return None, "", raw
    return None, "", raw


def pick_topic(prompt: str) -> str:
    p = _norm(prompt)
    if any(w in p for w in ("student", "class", "summary", "תלמיד", "שיעור")):
        return "class"
    if any(w in p for w in ("invoice", "חשבונית", "ap ", "vendor bill")):
        return "invoice"
    if any(w in p for w in ("vendor", "ספק", "supplier", "onboard")):
        return "vendor"
    if any(w in p for w in ("site", "אתר", "inspection", "safety")):
        return "site"
    if any(w in p for w in ("policy", "ack", "acknowledge", "מדיניות")):
        return "ack"
    return "generic"


def harvest_fields(prompt: str) -> tuple[list[dict], list[str]]:
    c = _norm(prompt)
    fields: list[dict] = []
    understood: list[str] = []

    def add(field: dict, note: str):
        if any(f["label"].lower() == field["label"].lower() and f["type"] == field["type"] for f in fields):
            return
        fields.append(field)
        understood.append(note)

    if any(w in c for w in ("summary", "student", "students", "class summary")):
        understood.append("form purpose: day summary for students")
    if "date" in c and any(w in c for w in ("auto", "automatic", "today", "now")):
        add(_f("date", "Date", True, help_="Filled automatically with today", auto="today"), "date (automatic today)")
    elif re.search(r"\bdate\b", c):
        add(_f("date", "Date", True), "date")
    if "email" in c or "e-mail" in c or "אימייל" in c:
        add(_f("email", "Email", True, help_="Filled by the person completing the form"), "email (by the user)")
    if any(w in c for w in ("in class", "attendance", "was the student", "did the student")):
        add(_f("yesno", "Was the student in class?", True), "attendance (was the student in class)")
    if "topic" in c or "explained" in c:
        add(_f("textarea", "Which topic was best explained?", True), "best-explained topic")
    if ("rate" in c or "rating" in c) and any(w in c for w in ("class", "today", "lesson", "session")):
        add(_f("radio", "Rate today's class", True, ["1", "2", "3", "4", "5"]), "rate today's class (1–5)")
    elif "rate" in c or "rating" in c:
        add(_f("radio", "Rating", True, ["1", "2", "3", "4", "5"]), "rating")
    if any(w in c for w in ("signature", "sign off", "sign-off", "חתימה")):
        add(_f("signature", "Signature", True), "signature (mandatory)")
    if "dropdown" in c or "department" in c or "רשימה" in c:
        add(
            _f("dropdown", "Department" if "department" in c else "Choose one", True, ["Finance", "Operations", "Legal"] if "department" in c else ["A", "B", "C"]),
            "dropdown",
        )
    if "invoice" in c or "חשבונית" in c:
        add(_f("text", "Vendor", True), "vendor")
        add(_f("text", "Invoice number", True), "invoice number")
        add(_f("number", "Amount due", True), "amount")
    return fields, understood


def guess_name(prompt: str, language: str) -> str:
    c = _norm(prompt)
    if "student" in c or "class" in c or "summary" in c:
        return "סיכום יום לתלמידים" if language == "he" else "Day summary for students"
    if "invoice" in c or "חשבונית" in c:
        return "אישור חשבונית" if language == "he" else "Invoice approval"
    words = [w for w in re.findall(r"[A-Za-z\u0590-\u05FF\u0600-\u06FF]+", prompt) if len(w) > 2][:6]
    return " ".join(words).title()[:80] or "Untitled form"


def knowledge_status(chunks: list[dict], connector_count: int, folder_count: int) -> dict:
    if chunks:
        titles = ", ".join(c.get("title") or c.get("source") or "source" for c in chunks[:3])
        return {
            "applied": True,
            "reason": f"I used {len(chunks)} knowledge hit(s): {titles}.",
            "action": "",
            "href": "/app/connectors",
            "also": "/app/manage",
        }
    bits = []
    if connector_count == 0:
        bits.append("Connect Google Drive, Microsoft 365, or the local database under Connectors.")
    else:
        bits.append("Sync Drive / Microsoft 365 / local DB so class lists and topics land in RAG.")
    bits.append("Put the class roster or lesson materials in a desk folder (Manage) and sync again.")
    _ = folder_count
    return {
        "applied": False,
        "reason": "I could not find a knowledge source for this class (roster, topics, or today's materials).",
        "action": " ".join(bits),
        "href": "/app/connectors",
        "also": "/app/manage",
    }


def compose_form(prompt: str, language: str = "en", context_fields: list[str] | None = None) -> dict:
    built = compose_from_prompt(prompt, language, chunks=[], connector_count=0, folder_count=0, use_llm=False)
    extra = context_fields or []
    fields = built["fields"]
    for name in extra[:8]:
        label = name.replace("_", " ").title()
        if not any(f["label"].lower() == label.lower() for f in fields):
            fields.insert(-1, _f("text", label, False))
    built["fields"] = fields
    return built


def compose_from_prompt(
    prompt: str,
    language: str = "en",
    chunks: list[dict] | None = None,
    connector_count: int = 0,
    folder_count: int = 0,
    use_llm: bool = True,
    model: str | None = None,
) -> dict:
    chunks = chunks or []
    fields, understood = harvest_fields(prompt)
    unclear: list[str] = []
    name = guess_name(prompt, language)
    fields = [_f("heading", name)] + fields
    keywords = ("date", "email", "signature", "rate", "class", "topic", "student", "summary", "dropdown", "invoice", "attendance")
    for clause in split_clauses(prompt):
        cl = _norm(clause)
        if clause and not any(k in cl for k in keywords) and len(clause) > 10:
            unclear.append(clause)

    knowledge = knowledge_status(chunks, connector_count, folder_count)
    provider = "heuristic"
    model_name = "heuristic"
    llm_note = ""
    status: dict | None = None

    if use_llm:
        status = ollama_status()
        if status.get("up") and status.get("models"):
            sys_prompt = (
                "You are DocFlow's form-builder assistant. Write a short chat reply (no JSON) to the manager. "
                "Confirm what you will put on the form. If a phrase is vague, say so. "
                "If no knowledge sources were applied, tell them to open Connectors (Google Drive, Microsoft 365, local DB) "
                "or Manage folders.\n\n"
                f"Prompt: {prompt}\nUnderstood: {understood}\nUnclear: {unclear}\nKnowledge: {knowledge}\n"
                f"Ollama: {status}\nFields: {[f['label'] for f in fields]}"
            )
            gen = generate("form_builder", sys_prompt, model=model)
            provider = gen.get("provider") or "heuristic"
            model_name = gen.get("model") or "heuristic"
            text = (gen.get("text") or "").strip()
            if text.startswith("{") or text.startswith("["):
                try:
                    data = json.loads(text)
                    llm_note = data.get("reply") or data.get("note") or ""
                except Exception:
                    llm_note = ""
            else:
                llm_note = text

    reply_bits = [
        f"I drafted {name} from your chat.",
        ("I understood: " + "; ".join(understood) + ".") if understood else "I could not map your sentences to fields yet. Rephrase in shorter clauses, or pick a field type on the left.",
    ]
    if unclear:
        reply_bits.append(
            "I did not fully understand: " + "; ".join(f"“{u}”" for u in unclear) + ". Say that again in a shorter phrase, or pick a field type on the left."
        )
    if knowledge["applied"]:
        reply_bits.append(knowledge["reason"])
    else:
        reply_bits.append(knowledge["reason"] + " " + knowledge["action"])
    if provider == "ollama":
        reply_bits.append(f"Local model: {model_name} (Ollama).")
    elif use_llm and status is not None:
        if not status["up"]:
            reply_bits.append(f"Ollama is not connected at {status['url']}. Start `ollama serve`, pull a model, then Connectors → Use this model.")
        elif not status["models"]:
            reply_bits.append("Ollama is running but has no models. Run `ollama pull llama3.2`, then Connectors → Use this model.")
        else:
            reply_bits.append(f"Ollama is available ({', '.join(status['models'][:3])}). Bind it on Connectors to let it write this reply.")
    else:
        reply_bits.append("Connect a local Ollama model on Connectors for a richer chat reply.")

    if llm_note and provider == "ollama":
        reply = llm_note
        extra = []
        if unclear:
            extra.append("I did not fully understand: " + "; ".join(f"“{u}”" for u in unclear) + ".")
        if not knowledge["applied"]:
            extra.append(knowledge["reason"] + " " + knowledge["action"])
        if extra:
            reply = reply + "\n\n" + " ".join(extra)
    else:
        reply = " ".join(reply_bits)

    return {
        "name": name,
        "topic": "class" if "student" in _norm(prompt) or "class" in _norm(prompt) else "general",
        "description": prompt.strip()[:400],
        "language": language if language in ("en", "he", "ar", "es", "fr") else "en",
        "fields": fields,
        "reply": reply,
        "understood": understood,
        "unclear": unclear,
        "knowledge": knowledge,
        "provider": provider,
        "model": model_name,
        "ollama": status,
    }


def fields_from_chunks(chunks: list[dict]) -> list[str]:
    names: list[str] = []
    skip = {"http", "https", "ftp", "www", "mailto"}
    blob = " ".join(c.get("text", "") for c in chunks)
    for m in re.findall(r"\b([A-Za-z][A-Za-z_ ]{2,40}):", blob):
        n = m.strip()
        if n.lower() in skip or len(n.split()) > 4:
            continue
        if n not in names:
            names.append(n)
    for key in ("invoice_number", "amount", "vendor", "date", "governing law"):
        if key.replace("_", " ") in blob.lower() and key not in names:
            names.append(key)
    return names[:10]
