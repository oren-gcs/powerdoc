from datetime import datetime
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require
from app.engine.formgen import compose_from_prompt, fields_from_chunks
from app.engine.orchestrator import match_automation, process_document
from app.engine.rag import retrieve, upsert_chunk
from app.llm import ollama_status
from app.models import (
    Activity,
    Automation,
    Connector,
    Document,
    Folder,
    Form,
    FormShare,
    FormSubmission,
    ModelBinding,
    Notification,
    RecordRow,
    User,
    Workflow,
)
from app.storage import storage

router = APIRouter(prefix="/api/v1/forms", tags=["forms"])
public = APIRouter(prefix="/api/v1/public/forms", tags=["public-forms"])


class FormIn(BaseModel):
    name: str
    topic: str = ""
    description: str = ""
    language: str = "en"
    fields: list[dict] = []
    layer_id: int | None = None
    folder_id: int | None = None
    workflow_id: int | None = None


class ComposeIn(BaseModel):
    prompt: str
    language: str = "en"
    use_rag: bool = True


class ShareIn(BaseModel):
    channel: str = "email"
    recipients: list[str]
    locale: str | None = None


class SubmitIn(BaseModel):
    name: str = ""
    email: str = ""
    answers: dict
    signature: str | None = None
    locale: str = "en"


def _out(f: Form) -> dict:
    return {
        "id": f.id,
        "name": f.name,
        "topic": f.topic,
        "description": f.description,
        "status": f.status,
        "language": f.language,
        "fields": (f.definition or {}).get("fields") or [],
        "folder_id": f.folder_id,
        "layer_id": f.layer_id,
        "workflow_id": f.workflow_id,
        "automation_id": f.automation_id,
        "share_token": f.share_token,
        "share_url": f"/f/{f.share_token}" if f.share_token else None,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.get("")
def list_forms(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Form).filter(Form.tenant_id == user.tenant_id).order_by(Form.id.desc()).all()
    return [_out(f) for f in rows]


@router.post("")
def create_form(body: FormIn, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    f = Form(
        tenant_id=user.tenant_id,
        created_by=user.id,
        name=body.name,
        topic=body.topic,
        description=body.description,
        language=body.language,
        definition={"fields": body.fields},
        layer_id=body.layer_id,
        folder_id=body.folder_id,
        workflow_id=body.workflow_id,
        status="draft",
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return _out(f)


@router.post("/compose")
def compose(body: ComposeIn, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    chunks = []
    extra: list[str] = []
    if body.use_rag:
        chunks = retrieve(db, user.tenant_id, body.prompt, min_score=2, fallback_fields=False)
        extra = fields_from_chunks(chunks)
    connectors = db.query(Connector).filter(Connector.tenant_id == user.tenant_id).count()
    folders = db.query(Folder).filter(Folder.tenant_id == user.tenant_id).count()
    binding = db.query(ModelBinding).filter(ModelBinding.agent_role == "form_builder", ModelBinding.provider == "ollama").first()
    if not binding:
        binding = db.query(ModelBinding).filter(ModelBinding.provider == "ollama").first()
    model = binding.model_name if binding and binding.provider == "ollama" else None
    built = compose_from_prompt(
        body.prompt,
        body.language,
        chunks=chunks,
        connector_count=connectors,
        folder_count=folders,
        use_llm=True,
        model=model,
    )
    if extra:
        for name in extra[:6]:
            label = name.replace("_", " ").title()
            if not any(f["label"].lower() == label.lower() for f in built["fields"]):
                built["fields"].insert(-1, {"id": name[:8], "type": "text", "label": label, "required": False, "options": [], "help": "From knowledge", "placeholder": "", "auto": ""})
    built["context"] = chunks[:4]
    if not built.get("ollama"):
        built["ollama"] = ollama_status()
    return built


@router.get("/{form_id}")
def get_form(form_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    return _out(f)


@router.put("/{form_id}")
def update_form(form_id: int, body: FormIn, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    f.name = body.name
    f.topic = body.topic
    f.description = body.description
    f.language = body.language
    f.definition = {"fields": body.fields}
    f.layer_id = body.layer_id
    f.folder_id = body.folder_id
    f.workflow_id = body.workflow_id
    db.commit()
    return _out(f)


@router.post("/{form_id}/publish")
def publish(form_id: int, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    auto_folder = (
        db.query(Folder)
        .filter(Folder.tenant_id == user.tenant_id, Folder.kind == "automation")
        .first()
    )
    if not auto_folder:
        auto_folder = Folder(tenant_id=user.tenant_id, name="Automation", kind="automation")
        db.add(auto_folder)
        db.flush()
    wf = db.get(Workflow, f.workflow_id) if f.workflow_id else None
    if not wf:
        wf = (
            db.query(Workflow)
            .filter(Workflow.tenant_id == user.tenant_id, Workflow.is_active.is_(True))
            .first()
        )
    if wf:
        auto = Automation(
            tenant_id=user.tenant_id,
            name=f"Live form · {f.name}",
            trigger_type="on_form_submit",
            trigger_config={"form_id": f.id},
            workflow_id=wf.id,
            is_active=True,
        )
        db.add(auto)
        db.flush()
        f.automation_id = auto.id
        f.workflow_id = wf.id
    f.folder_id = auto_folder.id
    f.status = "live"
    f.share_token = f.share_token or token_urlsafe(12)
    f.published_at = datetime.utcnow()
    db.commit()
    db.refresh(f)
    return _out(f)


@router.post("/{form_id}/share")
def share(form_id: int, body: ShareIn, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    if f.status != "live":
        raise HTTPException(400, "Publish the form first")
    sent = []
    locale = body.locale or f.language
    link = f"/f/{f.share_token}"
    for rec in body.recipients:
        db.add(FormShare(form_id=f.id, channel=body.channel, recipient=rec, locale=locale))
        target = db.query(User).filter(User.email == rec.lower()).first()
        db.add(
            Notification(
                tenant_id=user.tenant_id,
                user_id=target.id if target else None,
                channel=body.channel,
                subject=f"Please complete: {f.name}",
                body=f"Open {link} to fill and sign. Language: {locale}.",
                extra={"form_id": f.id, "link": link},
            )
        )
        sent.append(rec)
    db.commit()
    return {"sent": sent, "link": link, "channel": body.channel}


@router.get("/{form_id}/submissions")
def submissions(form_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    rows = db.query(FormSubmission).filter(FormSubmission.form_id == form_id).order_by(FormSubmission.id.desc()).all()
    return [
        {
            "id": s.id,
            "submitter_name": s.submitter_name,
            "submitter_email": s.submitter_email,
            "answers": s.answers,
            "status": s.status,
            "document_id": s.document_id,
            "locale": s.locale,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in rows
    ]


def _apply_submission(db: Session, f: Form, body: SubmitIn) -> dict:
    fields = (f.definition or {}).get("fields") or []
    missing = [
        x["label"]
        for x in fields
        if x.get("required") and x.get("type") not in ("heading", "signature") and not body.answers.get(x["id"])
    ]
    if missing:
        raise HTTPException(400, f"Missing required: {', '.join(missing)}")
    if any(x.get("type") == "signature" and x.get("required") for x in fields) and not body.signature:
        raise HTTPException(400, "Signature required")
    lines = [f"{f.name}", f"From: {body.name} <{body.email}>", ""]
    for field in fields:
        if field.get("type") == "heading":
            continue
        lines.append(f"{field.get('label')}: {body.answers.get(field['id'], '')}")
    rendered = "\n".join(lines).encode()
    key = storage.put(f.tenant_id, f"form-{f.id}-{token_urlsafe(4)}.txt", rendered)
    import hashlib

    owner = db.get(User, f.created_by) or db.query(User).filter(User.tenant_id == f.tenant_id).first()
    doc = Document(
        tenant_id=f.tenant_id,
        user_id=owner.id if owner else 1,
        filename=f"{f.name} — {body.name or 'submission'}.txt",
        content_type="text/plain",
        size_bytes=len(rendered),
        storage_key=key,
        checksum=hashlib.sha256(rendered).hexdigest(),
        status="uploaded",
        tags=["form-submission"],
    )
    db.add(doc)
    db.flush()
    sub = FormSubmission(
        form_id=f.id,
        tenant_id=f.tenant_id,
        submitter_name=body.name,
        submitter_email=body.email,
        answers=body.answers,
        signature=body.signature,
        locale=body.locale or f.language,
        document_id=doc.id,
        status="received",
    )
    db.add(sub)
    db.flush()
    db.add(RecordRow(tenant_id=f.tenant_id, form_id=f.id, submission_id=sub.id, payload=body.answers))
    upsert_chunk(db, f.tenant_id, "form_submission", str(sub.id), f.name, rendered.decode(), f.language)
    db.add(Activity(tenant_id=f.tenant_id, user_id=owner.id if owner else None, activity_type="form_submitted", details={"form_id": f.id, "submission_id": sub.id}))
    db.commit()
    db.refresh(doc)
    pipeline = process_document(db, doc, enable_workflow=bool(f.workflow_id), workflow_id=f.workflow_id)
    auto = match_automation(db, f.tenant_id, "on_form_submit", {"form_id": f.id})
    if auto and auto.workflow_id and auto.workflow_id != f.workflow_id:
        process_document(db, doc, enable_ocr=False, enable_workflow=True, workflow_id=auto.workflow_id)
    sub.status = "implemented"
    db.commit()
    return {"submission_id": sub.id, "document_id": doc.id, "status": sub.status, "pipeline": pipeline.get("status")}


@public.get("/{token}")
def public_get(token: str, db: Session = Depends(get_db)):
    f = db.query(Form).filter(Form.share_token == token, Form.status == "live").first()
    if not f:
        raise HTTPException(404, "Form is not live")
    return _out(f)


@public.post("/{token}/submit")
def public_submit(token: str, body: SubmitIn, db: Session = Depends(get_db)):
    f = db.query(Form).filter(Form.share_token == token, Form.status == "live").first()
    if not f:
        raise HTTPException(404, "Form is not live")
    return _apply_submission(db, f, body)
