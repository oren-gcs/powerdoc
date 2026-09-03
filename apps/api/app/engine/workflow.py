from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.classify import classify_document, extract_fields
from app.llm import generate
from app.models import (
    AgentLog,
    Document,
    ExtractedField,
    Notification,
    OCRResult,
    Workflow,
    WorkflowRun,
    WorkflowStepRun,
)
from app.ocr import extract_text, guess_language
from app.storage import storage


def _log(db: Session, role: str, action: str, summary: str, tenant_id: int | None, payload: dict | None = None, model: str = "heuristic") -> None:
    db.add(
        AgentLog(
            tenant_id=tenant_id,
            agent_role=role,
            action=action,
            model_used=model,
            status="success",
            summary=summary[:2000],
            payload=payload or {},
        )
    )


def _load_text(db: Session, document: Document) -> str:
    existing = db.query(OCRResult).filter(OCRResult.document_id == document.id).order_by(OCRResult.id.desc()).first()
    if existing and existing.text:
        return existing.text
    data = storage.get(document.storage_key)
    result = extract_text(document.filename, data)
    row = OCRResult(
        document_id=document.id,
        tenant_id=document.tenant_id,
        engine=result["engine"],
        text=result["text"],
        language=guess_language(result["text"]),
        confidence=result["confidence"],
        page_count=result["page_count"],
    )
    db.add(row)
    db.flush()
    return result["text"]


def step_extract_text(db: Session, ctx: dict, config: dict) -> dict:
    doc: Document = ctx["document"]
    text = _load_text(db, doc)
    ctx["text"] = text
    doc.status = "processing"
    return {"chars": len(text), "preview": text[:280]}


def step_classify(db: Session, ctx: dict, config: dict) -> dict:
    doc: Document = ctx["document"]
    text = ctx.get("text") or _load_text(db, doc)
    result = classify_document(doc.filename, text)
    doc.classification = result["label"]
    ctx["classification"] = result
    _log(db, "ocr", "classify", f"{doc.filename} → {result['label']}", doc.tenant_id, result)
    return result


def step_extract_fields(db: Session, ctx: dict, config: dict) -> dict:
    doc: Document = ctx["document"]
    text = ctx.get("text") or _load_text(db, doc)
    label = (ctx.get("classification") or {}).get("label") or doc.classification or "general"
    fields = extract_fields(text, label)
    db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).delete()
    for f in fields:
        db.add(ExtractedField(document_id=doc.id, name=f["name"], value=f["value"], confidence=f["confidence"]))
    ctx["fields"] = fields
    return {"fields": fields}


def step_condition(db: Session, ctx: dict, config: dict) -> dict:
    field = config.get("field", "classification")
    equals = config.get("equals")
    contains = config.get("contains")
    actual = None
    if field == "classification":
        actual = (ctx.get("classification") or {}).get("label") or ctx["document"].classification
    elif field == "filename":
        actual = ctx["document"].filename
    else:
        for f in ctx.get("fields") or []:
            if f["name"] == field:
                actual = f["value"]
    matched = True
    if equals is not None:
        matched = str(actual).lower() == str(equals).lower()
    if contains is not None:
        matched = contains.lower() in str(actual or "").lower()
    ctx["skip_remaining"] = not matched
    return {"matched": matched, "actual": actual}


def step_notify(db: Session, ctx: dict, config: dict) -> dict:
    doc: Document = ctx["document"]
    subject = config.get("subject") or f"DocFlow: {doc.filename} processed"
    body = config.get("body") or generate("notification", f"Document {doc.filename} classified as {doc.classification}")["text"]
    n = Notification(
        tenant_id=doc.tenant_id,
        user_id=doc.user_id,
        channel=config.get("channel", "in_app"),
        subject=subject,
        body=body,
        extra={"document_id": doc.id},
    )
    db.add(n)
    _log(db, "notification", "send", subject, doc.tenant_id)
    return {"subject": subject}


def step_summarize(db: Session, ctx: dict, config: dict) -> dict:
    text = ctx.get("text") or ""
    gen = generate("summarize", text[:4000])
    ctx["summary"] = gen["text"]
    _log(db, "analytics", "summarize", gen["text"][:400], ctx["document"].tenant_id, model=gen.get("model", "heuristic"))
    return {"summary": gen["text"], "provider": gen.get("provider")}


def step_agent(db: Session, ctx: dict, config: dict) -> dict:
    role = config.get("role", "workflow")
    prompt = config.get("prompt") or (
        f"Document {ctx['document'].filename} class={ctx['document'].classification}. "
        f"Fields={ctx.get('fields')}. Decide next operational action."
    )
    gen = generate(role, prompt)
    _log(db, role, "agent_step", gen["text"][:500], ctx["document"].tenant_id, model=gen.get("model", "heuristic"))
    return {"decision": gen["text"], "provider": gen.get("provider")}


def step_tag(db: Session, ctx: dict, config: dict) -> dict:
    doc: Document = ctx["document"]
    tags = list(doc.tags or [])
    for t in config.get("tags") or []:
        if t not in tags:
            tags.append(t)
    if doc.classification and doc.classification not in tags:
        tags.append(doc.classification)
    doc.tags = tags
    return {"tags": tags}


def step_webhook(db: Session, ctx: dict, config: dict) -> dict:
    # Record intended webhook without requiring outbound network in local demo.
    url = config.get("url", "")
    return {"queued": True, "url": url, "document_id": ctx["document"].id}


HANDLERS: dict[str, Callable] = {
    "extract_text": step_extract_text,
    "ocr": step_extract_text,
    "classify": step_classify,
    "extract_fields": step_extract_fields,
    "condition": step_condition,
    "notify": step_notify,
    "summarize": step_summarize,
    "agent": step_agent,
    "tag": step_tag,
    "webhook": step_webhook,
    "document_processing": step_extract_text,
}


def execute_workflow(db: Session, workflow: Workflow, document: Document) -> WorkflowRun:
    run = WorkflowRun(
        workflow_id=workflow.id,
        document_id=document.id,
        tenant_id=document.tenant_id,
        status="running",
        output={},
    )
    db.add(run)
    db.flush()
    steps = (workflow.definition or {}).get("steps") or []
    ctx: dict[str, Any] = {"document": document, "run": run}
    decision = generate(
        "workflow",
        f"Workflow '{workflow.name}' on {document.filename} with steps {[s.get('type') for s in steps]}",
    )
    _log(db, "workflow", "decide_execution", decision["text"], document.tenant_id, model=decision.get("model", "heuristic"))
    run.output["agent_decision"] = decision["text"]

    for raw in steps:
        if ctx.get("skip_remaining"):
            break
        key = raw.get("key") or raw.get("type")
        stype = raw.get("type") or "agent"
        handler = HANDLERS.get(stype)
        step = WorkflowStepRun(run_id=run.id, step_key=key, step_type=stype, status="running", input=raw.get("config") or {})
        db.add(step)
        db.flush()
        run.current_step = key
        try:
            if not handler:
                raise ValueError(f"Unknown step type: {stype}")
            out = handler(db, ctx, raw.get("config") or {})
            step.output = out
            step.status = "completed"
            step.finished_at = datetime.utcnow()
        except Exception as exc:
            step.status = "failed"
            step.error = f"{type(exc).__name__}: {exc}"
            step.finished_at = datetime.utcnow()
            run.status = "failed"
            run.error = step.error
            run.finished_at = datetime.utcnow()
            document.status = "failed"
            db.flush()
            return run

    document.status = "ready"
    run.status = "completed"
    run.finished_at = datetime.utcnow()
    run.current_step = None
    db.flush()
    return run
