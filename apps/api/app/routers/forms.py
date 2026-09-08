from datetime import datetime
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require
from app.engine.form_digest import (
    ensure_answered_folder,
    form_is_locked,
    form_submission_count,
    link_submission_document,
    run_submission_action,
)
from app.engine.formgen import compose_from_prompt, fields_from_chunks, relevant_chunks
from app.engine.orchestrator import match_automation, process_document
from app.engine.rag import retrieve, upsert_chunk
from app.llm import ollama_status
from app.models import (
    Activity,
    Automation,
    Connector,
    Document,
    Folder,
    FolderItem,
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
    recipients: list[str] = []
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


class DigestIn(BaseModel):
    action: str = "digest"
    workflow_id: int | None = None


class ArchiveIn(BaseModel):
    """Archive a form. keep_answers=True keeps submissions/digests under the archive package;
    keep_answers=False archives the definition only — answers stay in Answered folder / documents.
    """

    keep_answers: bool = True


def _require_unlocked(db: Session, f: Form) -> None:
    if f.status == "archived" or getattr(f, "archived_at", None):
        raise HTTPException(
            status_code=409,
            detail="Form is archived. Copy it to a new form or unarchive to continue.",
        )
    if form_is_locked(db, f):
        raise HTTPException(
            status_code=409,
            detail="Form is locked after the first answer. Definition and recipients cannot be changed; open Answered to work submissions.",
        )


def _ensure_archive_root(db: Session, tenant_id: int, layer_id: int | None) -> Folder:
    root = (
        db.query(Folder)
        .filter(Folder.tenant_id == tenant_id, Folder.kind == "archive", Folder.parent_id.is_(None))
        .first()
    )
    if root:
        return root
    root = Folder(tenant_id=tenant_id, layer_id=layer_id, name="Archive", kind="archive")
    db.add(root)
    db.flush()
    return root


def _clean_recipients(raw: list[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in raw or []:
        email = (item or "").strip().lower()
        if not email or "@" not in email or email in seen:
            continue
        seen.add(email)
        out.append(email)
    return out


def _definition(fields: list[dict], recipients: list[str] | None = None) -> dict:
    return {"fields": fields or [], "recipients": _clean_recipients(recipients)}


def _copy_definition(f: Form) -> dict:
    """Deep-copy fields/options/recipients only — never submissions or answered data."""
    src = f.definition or {}
    fields = []
    for field in src.get("fields") or []:
        if not isinstance(field, dict):
            continue
        copied = dict(field)
        if isinstance(copied.get("options"), list):
            copied["options"] = list(copied["options"])
        fields.append(copied)
    return _definition(fields, src.get("recipients") or [])


def _deactivate_form_automation(db: Session, f: Form) -> None:
    if not f.automation_id:
        return
    auto = db.get(Automation, f.automation_id)
    if auto and auto.tenant_id == f.tenant_id:
        auto.is_active = False


def _archive_form(db: Session, f: Form, *, keep_answers: bool) -> Form:
    if f.status == "archived" or getattr(f, "archived_at", None):
        raise HTTPException(409, "Form is already archived")
    _deactivate_form_automation(db, f)
    # Stop public fill immediately (public routes require status == live).
    f.status = "archived"
    f.archived_at = datetime.utcnow()
    f.archive_keep_answers = keep_answers
    f.share_token = None
    _revoke_pending_shares(db, f.id)

    if form_submission_count(db, f.id):
        folder = ensure_answered_folder(db, f)
        archive_root = _ensure_archive_root(db, f.tenant_id, f.layer_id)
        if keep_answers:
            # Keep answered package under Archive, linked to this form.
            folder.parent_id = archive_root.id
            folder.name = f"Archive · {f.name}"
            folder.kind = "archive"
            f.folder_id = archive_root.id
        else:
            # Form definition archived; answers stay orphan-safe in Answered / documents.
            folder.parent_id = folder.parent_id or f.folder_id
            folder.name = f"Answered · {f.name}"
            folder.kind = "answered"
            if f.folder_id and f.folder_id != folder.id:
                f.folder_id = None
    else:
        f.folder_id = None
    return f


def _unarchive_form(db: Session, f: Form) -> Form:
    if f.status != "archived" and not getattr(f, "archived_at", None):
        raise HTTPException(400, "Form is not archived")
    f.status = "draft"
    f.archived_at = None
    f.archive_keep_answers = None
    if f.answered_folder_id:
        folder = db.get(Folder, f.answered_folder_id)
        if folder and folder.tenant_id == f.tenant_id:
            folder.name = f"Answered · {f.name}"
            folder.kind = "answered"
    return f


def _form_recipients(f: Form) -> list[str]:
    return _clean_recipients((f.definition or {}).get("recipients") or [])


def _sends_to(db: Session, f: Form) -> list[dict]:
    """Display labels for who receives submissions (name when known, else email)."""
    emails = _form_recipients(f)
    if not emails:
        return []
    users = {
        (u.email or "").lower(): u
        for u in db.query(User).filter(User.tenant_id == f.tenant_id, User.email.in_(emails)).all()
    }
    labels: list[dict] = []
    for email in emails:
        user = users.get(email)
        name = (user.full_name or "").strip() if user else ""
        labels.append({"email": email, "name": name or None})
    return labels


def _share_link(share: FormShare) -> dict:
    email = (share.recipient or "").strip().lower()
    token = share.token or ""
    return {
        "email": email,
        "token": token or None,
        "url": f"/f/{token}" if token else None,
        "status": share.status or "pending",
        "submission_id": share.submission_id,
    }


def _recipient_links(db: Session, form_id: int) -> list[dict]:
    """Latest personal share per recipient email (operator copy list)."""
    rows = (
        db.query(FormShare)
        .filter(FormShare.form_id == form_id, FormShare.token.isnot(None))
        .order_by(FormShare.id.desc())
        .all()
    )
    seen: set[str] = set()
    links: list[dict] = []
    for share in rows:
        email = (share.recipient or "").strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        links.append(_share_link(share))
    links.sort(key=lambda x: x["email"])
    return links


def _ensure_personal_share(
    db: Session,
    f: Form,
    email: str,
    *,
    channel: str = "email",
    locale: str | None = None,
) -> FormShare:
    """One pending personal token per recipient; reuse existing pending token."""
    email = (email or "").strip().lower()
    existing = (
        db.query(FormShare)
        .filter(
            FormShare.form_id == f.id,
            FormShare.recipient == email,
            FormShare.status == "pending",
            FormShare.token.isnot(None),
        )
        .order_by(FormShare.id.desc())
        .first()
    )
    if existing:
        return existing
    share = FormShare(
        form_id=f.id,
        channel=channel,
        recipient=email,
        locale=locale or f.language,
        token=token_urlsafe(16),
        status="pending",
        submission_id=None,
    )
    db.add(share)
    db.flush()
    return share


def _out(f: Form, db: Session | None = None) -> dict:
    archived = f.status == "archived" or bool(getattr(f, "archived_at", None))
    recipients = _form_recipients(f)
    live = f.status == "live"
    # Listed recipients → personal links only (no shared open token).
    open_token = f.share_token if live and f.share_token and not recipients else None
    payload = {
        "id": f.id,
        "name": f.name,
        "topic": f.topic,
        "description": f.description,
        "status": f.status,
        "language": f.language,
        "fields": (f.definition or {}).get("fields") or [],
        "recipients": recipients,
        "folder_id": f.folder_id,
        "answered_folder_id": f.answered_folder_id,
        "layer_id": f.layer_id,
        "workflow_id": f.workflow_id,
        "automation_id": f.automation_id,
        "share_token": open_token,
        "share_url": f"/f/{open_token}" if open_token else None,
        "open_link": bool(open_token),
        "recipient_links": [],
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "archived_at": f.archived_at.isoformat() if getattr(f, "archived_at", None) else None,
        "archive_keep_answers": getattr(f, "archive_keep_answers", None),
        "archived": archived,
        "locked": False,
        "submission_count": 0,
    }
    if db is not None:
        count = form_submission_count(db, f.id)
        payload["submission_count"] = count
        # Locked means definition frozen after first answer — still true when archived.
        payload["locked"] = count > 0
        payload["sends_to"] = _sends_to(db, f)
        payload["recipient_links"] = _recipient_links(db, f.id) if live and not archived else []
    return payload


def _submission_out(db: Session, s: FormSubmission) -> dict:
    doc = db.get(Document, s.document_id) if s.document_id else None
    return {
        "id": s.id,
        "submitter_name": s.submitter_name,
        "submitter_email": s.submitter_email,
        "answers": s.answers,
        "status": s.status,
        "document_id": s.document_id,
        "document_filename": doc.filename if doc else None,
        "document_status": doc.status if doc else None,
        "document_url": f"/app/documents/{doc.id}" if doc else None,
        "locale": s.locale,
        "actions": s.actions or [],
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _notify_recipients(
    db: Session,
    f: Form,
    recipients: list[str],
    *,
    channel: str = "email",
    locale: str | None = None,
    tenant_id: int,
) -> tuple[list[str], list[dict]]:
    """Create personal share tokens and in-app notifications. No real SMTP yet."""
    sent: list[str] = []
    links: list[dict] = []
    lang = locale or f.language
    for rec in _clean_recipients(recipients):
        share = _ensure_personal_share(db, f, rec, channel=channel, locale=lang)
        link = f"/f/{share.token}"
        target = db.query(User).filter(User.email == rec).first()
        db.add(
            Notification(
                tenant_id=tenant_id,
                user_id=target.id if target else None,
                channel=channel,
                subject=f"Please complete: {f.name}",
                body=f"Open {link} to fill and sign (personal link for {rec}). Language: {lang}.",
                extra={
                    "form_id": f.id,
                    "link": link,
                    "recipient": rec,
                    "share_token": share.token,
                    "smtp": False,
                },
            )
        )
        sent.append(rec)
        links.append(_share_link(share))
    return sent, links


def _revoke_pending_shares(db: Session, form_id: int) -> None:
    rows = (
        db.query(FormShare)
        .filter(FormShare.form_id == form_id, FormShare.status == "pending")
        .all()
    )
    for share in rows:
        share.status = "revoked"


@router.get("")
def list_forms(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Form).filter(Form.tenant_id == user.tenant_id).order_by(Form.id.desc()).all()
    return [_out(f, db) for f in rows]


@router.post("")
def create_form(body: FormIn, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    f = Form(
        tenant_id=user.tenant_id,
        created_by=user.id,
        name=body.name,
        topic=body.topic,
        description=body.description,
        language=body.language,
        definition=_definition(body.fields, body.recipients),
        layer_id=body.layer_id,
        folder_id=body.folder_id,
        workflow_id=body.workflow_id,
        status="draft",
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return _out(f, db)


@router.post("/compose")
def compose(body: ComposeIn, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    chunks = []
    extra: list[str] = []
    if body.use_rag:
        chunks = retrieve(db, user.tenant_id, body.prompt, min_score=3, fallback_fields=False)
        chunks = relevant_chunks(body.prompt, chunks)
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
                built["fields"].insert(
                    -1,
                    {
                        "id": name[:8],
                        "type": "text",
                        "label": label,
                        "required": False,
                        "options": [],
                        "help": "From knowledge",
                        "placeholder": "",
                        "auto": "",
                        "default": "",
                    },
                )
    built["context"] = chunks[:4]
    if not built.get("ollama"):
        built["ollama"] = ollama_status()
    return built


@router.get("/{form_id}")
def get_form(form_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    return _out(f, db)


@router.put("/{form_id}")
def update_form(form_id: int, body: FormIn, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    _require_unlocked(db, f)
    f.name = body.name
    f.topic = body.topic
    f.description = body.description
    f.language = body.language
    f.definition = _definition(body.fields, body.recipients)
    f.layer_id = body.layer_id
    f.folder_id = body.folder_id
    f.workflow_id = body.workflow_id
    db.commit()
    return _out(f, db)


@router.delete("/{form_id}")
def delete_form(form_id: int, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    if f.status == "archived" or getattr(f, "archived_at", None):
        raise HTTPException(409, "Archived forms cannot be deleted. Unarchive first or leave in archive.")
    if form_is_locked(db, f):
        raise HTTPException(
            status_code=409,
            detail="Form is locked after the first answer and cannot be deleted.",
        )
    db.query(FormShare).filter(FormShare.form_id == form_id).delete()
    db.delete(f)
    db.commit()
    return {"ok": True, "deleted": form_id}


@router.post("/{form_id}/copy")
def copy_form(form_id: int, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    """Duplicate definition into a new unlocked draft. No submissions/answered data copied.
    Allowed for locked and archived forms.
    """
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    base_name = (f.name or "Form").strip() or "Form"
    copy_name = f"{base_name} (copy)"
    clone = Form(
        tenant_id=user.tenant_id,
        created_by=user.id,
        name=copy_name[:160],
        topic=f.topic or "",
        description=f.description or "",
        language=f.language or "en",
        definition=_copy_definition(f),
        layer_id=f.layer_id,
        folder_id=None,
        workflow_id=f.workflow_id,
        automation_id=None,
        answered_folder_id=None,
        share_token=None,
        status="draft",
        archived_at=None,
        archive_keep_answers=None,
    )
    db.add(clone)
    db.flush()
    db.add(
        Activity(
            tenant_id=user.tenant_id,
            user_id=user.id,
            activity_type="form_copied",
            details={"source_form_id": f.id, "new_form_id": clone.id},
        )
    )
    db.commit()
    db.refresh(clone)
    out = _out(clone, db)
    out["copied_from"] = f.id
    return out


@router.post("/{form_id}/archive")
def archive_form(
    form_id: int,
    body: ArchiveIn,
    user: User = Depends(require("operator")),
    db: Session = Depends(get_db),
):
    """Archive a form (including locked). keep_answers controls answered-data packaging."""
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    _archive_form(db, f, keep_answers=bool(body.keep_answers))
    db.add(
        Activity(
            tenant_id=user.tenant_id,
            user_id=user.id,
            activity_type="form_archived",
            details={"form_id": f.id, "keep_answers": bool(body.keep_answers)},
        )
    )
    db.commit()
    db.refresh(f)
    return _out(f, db)


@router.post("/{form_id}/unarchive")
def unarchive_form(form_id: int, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    _unarchive_form(db, f)
    db.add(
        Activity(
            tenant_id=user.tenant_id,
            user_id=user.id,
            activity_type="form_unarchived",
            details={"form_id": f.id},
        )
    )
    db.commit()
    db.refresh(f)
    return _out(f, db)


@router.post("/{form_id}/publish")
def publish(form_id: int, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    if f.status == "archived" or getattr(f, "archived_at", None):
        raise HTTPException(409, "Archived forms cannot be published. Copy to a new form or unarchive first.")
    if form_is_locked(db, f):
        raise HTTPException(409, "Locked forms cannot be re-published; copy to a new form instead.")
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
    recipients = _form_recipients(f)
    if recipients:
        # Listed recipients use personal tokens only — no shared open link.
        f.share_token = None
    else:
        f.share_token = f.share_token or token_urlsafe(12)
    f.published_at = datetime.utcnow()
    sent, recipient_links = _notify_recipients(db, f, recipients, tenant_id=user.tenant_id)
    db.commit()
    db.refresh(f)
    out = _out(f, db)
    out["notified"] = sent
    out["recipient_links"] = recipient_links or out.get("recipient_links") or []
    return out


@router.post("/{form_id}/share")
def share(form_id: int, body: ShareIn, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    if f.status == "archived" or getattr(f, "archived_at", None):
        raise HTTPException(409, "Archived forms cannot be shared. Copy to a new form or unarchive first.")
    if f.status != "live":
        raise HTTPException(400, "Publish the form first")
    if form_is_locked(db, f) and body.recipients:
        # Locked forms keep their recipient list; re-notify existing only.
        requested = _clean_recipients(body.recipients)
        current = _form_recipients(f)
        if requested and set(requested) != set(current):
            raise HTTPException(
                status_code=409,
                detail="Form is locked after the first answer; recipients cannot be changed.",
            )
    recipients = _clean_recipients(body.recipients) or _form_recipients(f)
    if not recipients:
        raise HTTPException(400, "Add at least one recipient")
    # Persist chosen recipients on the form so the builder preview stays in sync.
    if not form_is_locked(db, f):
        definition = dict(f.definition or {})
        definition["recipients"] = recipients
        f.definition = definition
    # With a recipient list, kill any open form-level token.
    f.share_token = None
    sent, recipient_links = _notify_recipients(
        db,
        f,
        recipients,
        channel=body.channel,
        locale=body.locale,
        tenant_id=user.tenant_id,
    )
    db.commit()
    return {
        "sent": sent,
        "link": None,
        "channel": body.channel,
        "smtp": False,
        "recipient_links": recipient_links,
    }


@router.get("/{form_id}/submissions")
def submissions(form_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    rows = db.query(FormSubmission).filter(FormSubmission.form_id == form_id).order_by(FormSubmission.id.desc()).all()
    return [_submission_out(db, s) for s in rows]


@router.get("/{form_id}/answered")
def answered_folder(form_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    folder = None
    if form_submission_count(db, f.id):
        folder = ensure_answered_folder(db, f)
        db.commit()
        db.refresh(f)
    rows = db.query(FormSubmission).filter(FormSubmission.form_id == form_id).order_by(FormSubmission.id.desc()).all()
    items = []
    if folder:
        items = (
            db.query(FolderItem)
            .filter(FolderItem.folder_id == folder.id)
            .order_by(FolderItem.id.desc())
            .all()
        )
    return {
        "form": _out(f, db),
        "folder": (
            {"id": folder.id, "name": folder.name, "kind": folder.kind, "parent_id": folder.parent_id}
            if folder
            else None
        ),
        "items": [{"id": i.id, "resource_type": i.resource_type, "resource_id": i.resource_id} for i in items],
        "submissions": [_submission_out(db, s) for s in rows],
    }


@router.post("/{form_id}/submissions/{submission_id}/digest")
def digest_submission(
    form_id: int,
    submission_id: int,
    body: DigestIn,
    user: User = Depends(require("operator")),
    db: Session = Depends(get_db),
):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    sub = db.get(FormSubmission, submission_id)
    if not sub or sub.form_id != form_id or sub.tenant_id != user.tenant_id:
        raise HTTPException(404, "Submission not found")
    try:
        return run_submission_action(db, f, sub, body.action, user, workflow_id=body.workflow_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{form_id}/submissions/{submission_id}/ingest")
def ingest_submission(
    form_id: int,
    submission_id: int,
    body: DigestIn | None = None,
    user: User = Depends(require("operator")),
    db: Session = Depends(get_db),
):
    f = db.get(Form, form_id)
    if not f or f.tenant_id != user.tenant_id:
        raise HTTPException(404, "Form not found")
    sub = db.get(FormSubmission, submission_id)
    if not sub or sub.form_id != form_id or sub.tenant_id != user.tenant_id:
        raise HTTPException(404, "Submission not found")
    try:
        return run_submission_action(
            db,
            f,
            sub,
            "ingest",
            user,
            workflow_id=(body.workflow_id if body else None),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _apply_submission(db: Session, f: Form, body: SubmitIn, share: FormShare | None = None) -> dict:
    if share is not None:
        status = (share.status or "pending").lower()
        if status == "submitted":
            raise HTTPException(409, "This personal link was already used. Submission is closed.")
        if status == "revoked":
            raise HTTPException(409, "This personal link has been revoked.")
        if status != "pending":
            raise HTTPException(409, "This personal link is no longer valid.")
        # Prefer invite email; allow override only if blank body email.
        if not (body.email or "").strip():
            body.email = share.recipient
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
        actions=[],
    )
    db.add(sub)
    db.flush()
    if share is not None:
        share.status = "submitted"
        share.submission_id = sub.id
    link_submission_document(db, f, sub)
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
    return {
        "submission_id": sub.id,
        "document_id": doc.id,
        "status": sub.status,
        "pipeline": pipeline.get("status"),
        "answered_folder_id": f.answered_folder_id,
        "locked": True,
        "share_status": share.status if share is not None else None,
        "recipient_email": share.recipient if share is not None else None,
    }


def _resolve_public_token(db: Session, token: str) -> tuple[Form, FormShare | None]:
    share = db.query(FormShare).filter(FormShare.token == token).first()
    if share:
        f = db.get(Form, share.form_id)
        if not f or f.status != "live":
            raise HTTPException(404, "Form is not live")
        return f, share
    f = db.query(Form).filter(Form.share_token == token, Form.status == "live").first()
    if not f:
        raise HTTPException(404, "Form is not live")
    # Open link only when the form has no recipient list.
    if _form_recipients(f):
        raise HTTPException(404, "Form is not live")
    return f, None


@public.get("/{token}")
def public_get(
    token: str,
    email: str | None = Query(None),
    db: Session = Depends(get_db),
):
    f, share = _resolve_public_token(db, token)
    out = _out(f, db)
    # Public fill only needs display labels next to submit — not builder config.
    out.pop("recipients", None)
    out.pop("recipient_links", None)
    if share is not None:
        already = (share.status or "").lower() == "submitted"
        revoked = (share.status or "").lower() == "revoked"
        invite_email = (share.recipient or "").strip().lower()
        hint = (email or "").strip().lower()
        email_match = None
        if hint:
            email_match = hint == invite_email
        out["personal"] = True
        out["recipient_email"] = invite_email
        out["share_status"] = share.status
        out["already_submitted"] = already
        out["link_closed"] = already or revoked
        out["submission_id"] = share.submission_id
        out["email_hint"] = hint or None
        out["email_match"] = email_match
        if already or revoked:
            # Still return metadata so UI can show closed state without exposing fields to re-fill.
            out["fields"] = []
    else:
        out["personal"] = False
        out["recipient_email"] = None
        out["share_status"] = None
        out["already_submitted"] = False
        out["link_closed"] = False
        out["submission_id"] = None
        out["email_hint"] = None
        out["email_match"] = None
    return out


@public.post("/{token}/submit")
def public_submit(token: str, body: SubmitIn, db: Session = Depends(get_db)):
    f, share = _resolve_public_token(db, token)
    return _apply_submission(db, f, body, share=share)
