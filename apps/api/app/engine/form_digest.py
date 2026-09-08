"""Ingest / digest / extract / summarize / insights for answered form submissions."""

from __future__ import annotations

import hashlib
from datetime import datetime
from secrets import token_urlsafe

from sqlalchemy.orm import Session

from app.engine.orchestrator import process_document
from app.engine.rag import upsert_chunk
from app.engine.skills import get_skill
from app.llm import generate
from app.models import (
    Activity,
    AgentLog,
    Automation,
    Document,
    Folder,
    FolderItem,
    Form,
    FormSubmission,
    Notification,
    User,
    Workflow,
)
from app.storage import storage


def form_submission_count(db: Session, form_id: int) -> int:
    return db.query(FormSubmission).filter(FormSubmission.form_id == form_id).count()


def form_is_locked(db: Session, form: Form) -> bool:
    return form_submission_count(db, form.id) > 0


def ensure_answered_folder(db: Session, form: Form) -> Folder:
    """Ensure a per-form Answered subfolder exists and is linked on the form."""
    fid = getattr(form, "answered_folder_id", None)
    if fid:
        existing = db.get(Folder, fid)
        if existing and existing.tenant_id == form.tenant_id:
            return existing
    folder = Folder(
        tenant_id=form.tenant_id,
        layer_id=form.layer_id,
        parent_id=form.folder_id,
        name=f"Answered · {form.name}",
        kind="answered",
    )
    db.add(folder)
    db.flush()
    form.answered_folder_id = folder.id
    return folder


def link_submission_document(db: Session, form: Form, sub: FormSubmission) -> None:
    if not sub.document_id:
        return
    folder = ensure_answered_folder(db, form)
    exists = (
        db.query(FolderItem)
        .filter(
            FolderItem.folder_id == folder.id,
            FolderItem.resource_type == "document",
            FolderItem.resource_id == sub.document_id,
        )
        .first()
    )
    if not exists:
        db.add(FolderItem(folder_id=folder.id, resource_type="document", resource_id=sub.document_id))
    exists_sub = (
        db.query(FolderItem)
        .filter(
            FolderItem.folder_id == folder.id,
            FolderItem.resource_type == "form_submission",
            FolderItem.resource_id == sub.id,
        )
        .first()
    )
    if not exists_sub:
        db.add(FolderItem(folder_id=folder.id, resource_type="form_submission", resource_id=sub.id))


def _answers_text(form: Form, sub: FormSubmission) -> str:
    fields = (form.definition or {}).get("fields") or []
    lines = [
        f"Form: {form.name}",
        f"Submitter: {sub.submitter_name} <{sub.submitter_email}>",
        f"Submitted: {sub.created_at.isoformat() if sub.created_at else ''}",
        "",
    ]
    by_id = {f.get("id"): f for f in fields}
    for key, value in (sub.answers or {}).items():
        label = (by_id.get(key) or {}).get("label") or key
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def _record_action(db: Session, sub: FormSubmission, action: str, result: dict, user: User | None) -> dict:
    entry = {
        "action": action,
        "at": datetime.utcnow().isoformat() + "Z",
        "status": result.get("status", "ok"),
        "summary": (result.get("summary") or "")[:800],
        "document_id": result.get("document_id"),
        "automation_id": result.get("automation_id"),
        "provider": result.get("provider"),
    }
    history = list(sub.actions or [])
    history.append(entry)
    sub.actions = history[-40:]
    db.add(
        AgentLog(
            tenant_id=sub.tenant_id,
            agent_role="form_digest" if action != "insights" else "form_insights",
            action=action,
            model_used=result.get("model", "orchestrator"),
            status=entry["status"],
            summary=entry["summary"],
            payload={"form_id": sub.form_id, "submission_id": sub.id, **{k: v for k, v in result.items() if k != "summary"}},
        )
    )
    db.add(
        Activity(
            tenant_id=sub.tenant_id,
            user_id=user.id if user else None,
            activity_type=f"form_{action}",
            details={"form_id": sub.form_id, "submission_id": sub.id, "action": action},
        )
    )
    return entry


def run_submission_action(
    db: Session,
    form: Form,
    sub: FormSubmission,
    action: str,
    user: User,
    *,
    workflow_id: int | None = None,
) -> dict:
    action = (action or "").strip().lower()
    allowed = {"ingest", "digest", "extract", "summarize", "insights", "automate"}
    if action not in allowed:
        raise ValueError(f"Unknown action '{action}'. Use one of: {', '.join(sorted(allowed))}")

    text = _answers_text(form, sub)
    result: dict = {"status": "ok", "action": action}

    if action == "ingest":
        upsert_chunk(
            db,
            form.tenant_id,
            "form_submission",
            str(sub.id),
            f"{form.name} · {sub.submitter_name or sub.submitter_email or sub.id}",
            text,
            sub.locale or form.language,
        )
        link_submission_document(db, form, sub)
        pipeline = None
        if sub.document_id:
            doc = db.get(Document, sub.document_id)
            if doc:
                pipeline = process_document(
                    db,
                    doc,
                    enable_workflow=bool(form.workflow_id or workflow_id),
                    workflow_id=workflow_id or form.workflow_id,
                )
        result["summary"] = "Submission ingested into knowledge and answered folder."
        result["pipeline"] = (pipeline or {}).get("status")
        result["model"] = "orchestrator"

    elif action == "digest":
        skill = get_skill("invoice-extraction") or get_skill("summarize")
        instructions = (skill or {}).get("instructions") or "Structure the intake into labeled fields."
        prompt = (
            f"{instructions}\n\nProduce a structured intake digest (JSON-like bullets) for this form answer:\n\n{text}"
        )
        gen = generate("orchestrator", prompt)
        digest_body = gen.get("text") or ""
        upsert_chunk(
            db,
            form.tenant_id,
            "form_digest",
            str(sub.id),
            f"Digest · {form.name} #{sub.id}",
            digest_body,
            sub.locale or form.language,
        )
        result["summary"] = digest_body[:800]
        result["provider"] = gen.get("provider")
        result["model"] = gen.get("model", "heuristic")
        result["digest"] = digest_body

    elif action == "extract":
        rendered = text.encode()
        key = storage.put(form.tenant_id, f"extract-form-{form.id}-{sub.id}-{token_urlsafe(4)}.txt", rendered)
        doc = Document(
            tenant_id=form.tenant_id,
            user_id=user.id,
            filename=f"Extract · {form.name} — {sub.submitter_name or 'submission'}.txt",
            content_type="text/plain",
            size_bytes=len(rendered),
            storage_key=key,
            checksum=hashlib.sha256(rendered).hexdigest(),
            status="uploaded",
            tags=["form-extract", f"form:{form.id}", f"submission:{sub.id}"],
        )
        db.add(doc)
        db.flush()
        folder = ensure_answered_folder(db, form)
        db.add(FolderItem(folder_id=folder.id, resource_type="document", resource_id=doc.id))
        pipeline = process_document(db, doc, enable_workflow=bool(workflow_id or form.workflow_id), workflow_id=workflow_id or form.workflow_id)
        result["document_id"] = doc.id
        result["summary"] = f"Extracted document #{doc.id} from submission."
        result["pipeline"] = pipeline.get("status")
        result["model"] = "orchestrator"

    elif action == "summarize":
        skill = get_skill("summarize")
        instructions = (skill or {}).get("instructions") or "Summarize in four bullets."
        gen = generate("summarize", f"{instructions}\n\n{text}")
        summary = gen.get("text") or ""
        upsert_chunk(
            db,
            form.tenant_id,
            "form_summary",
            str(sub.id),
            f"Summary · {form.name} #{sub.id}",
            summary,
            sub.locale or form.language,
        )
        db.add(
            Notification(
                tenant_id=form.tenant_id,
                user_id=user.id,
                channel="in_app",
                subject=f"Summary · {form.name}",
                body=summary[:1200],
                extra={"form_id": form.id, "submission_id": sub.id, "action": "summarize"},
            )
        )
        result["summary"] = summary[:800]
        result["provider"] = gen.get("provider")
        result["model"] = gen.get("model", "heuristic")

    elif action == "insights":
        skill = get_skill("docflow-operator") or get_skill("summarize")
        instructions = (skill or {}).get("instructions") or "Provide operational insights."
        prompt = (
            "You are the DocFlow form-insights agent under the main orchestrator.\n"
            f"{instructions}\n\n"
            "Give actionable insights on this received form data: risks, follow-ups, "
            "missing fields, and suggested next workflow.\n\n"
            f"{text}"
        )
        gen = generate("orchestrator", prompt)
        insights = gen.get("text") or ""
        upsert_chunk(
            db,
            form.tenant_id,
            "form_insights",
            str(sub.id),
            f"Insights · {form.name} #{sub.id}",
            insights,
            sub.locale or form.language,
        )
        db.add(
            Notification(
                tenant_id=form.tenant_id,
                user_id=user.id,
                channel="in_app",
                subject=f"Insights · {form.name}",
                body=insights[:1200],
                extra={"form_id": form.id, "submission_id": sub.id, "action": "insights"},
            )
        )
        result["summary"] = insights[:800]
        result["provider"] = gen.get("provider")
        result["model"] = gen.get("model", "heuristic")
        result["insights"] = insights

    elif action == "automate":
        wf = db.get(Workflow, workflow_id) if workflow_id else None
        if not wf:
            wf = db.get(Workflow, form.workflow_id) if form.workflow_id else None
        if not wf:
            wf = (
                db.query(Workflow)
                .filter(Workflow.tenant_id == form.tenant_id, Workflow.is_active.is_(True))
                .order_by(Workflow.id.asc())
                .first()
            )
        if not wf:
            result["status"] = "error"
            result["summary"] = "No active workflow available to bind an automation."
        else:
            auto = Automation(
                tenant_id=form.tenant_id,
                name=f"Answered · {form.name} · sub {sub.id}",
                trigger_type="on_form_submit",
                trigger_config={"form_id": form.id, "submission_id": sub.id, "source": "answered_folder"},
                workflow_id=wf.id,
                is_active=True,
            )
            db.add(auto)
            db.flush()
            if not form.automation_id:
                form.automation_id = auto.id
            if not form.workflow_id:
                form.workflow_id = wf.id
            result["automation_id"] = auto.id
            result["workflow_id"] = wf.id
            result["summary"] = f"Automation #{auto.id} created on workflow '{wf.name}'."
            result["model"] = "orchestrator"
            if sub.document_id:
                doc = db.get(Document, sub.document_id)
                if doc:
                    process_document(db, doc, enable_ocr=False, enable_workflow=True, workflow_id=wf.id)

    entry = _record_action(db, sub, action, result, user)
    db.commit()
    db.refresh(sub)
    return {
        "action": action,
        "submission_id": sub.id,
        "form_id": form.id,
        "entry": entry,
        "result": {k: v for k, v in result.items() if k not in ("digest", "insights") or True},
        "actions": sub.actions or [],
        "answered_folder_id": form.answered_folder_id,
    }
