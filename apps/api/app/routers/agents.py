from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require
from app.engine.orchestrator import process_document
from app.engine.skills import get_skill, load_skills
from app.llm import generate
from app.models import AgentLog, Document, ModelBinding, User
from app.storage import storage

router = APIRouter(prefix="/api/v1/agent", tags=["agents"])


@router.get("/status")
def agent_status(user: User = Depends(current_user), db: Session = Depends(get_db)):
    bindings = db.query(ModelBinding).all()
    return {
        "orchestrator": "ready",
        "skills": len(load_skills()),
        "bindings": [{"role": b.agent_role, "model": b.model_name, "provider": b.provider} for b in bindings],
    }


@router.post("/process-document")
async def process(
    file: UploadFile = File(...),
    enable_ocr: bool = Form(True),
    enable_workflow: bool = Form(True),
    enable_notification: bool = Form(True),
    enable_analytics: bool = Form(True),
    workflow_id: int | None = Form(None),
    user: User = Depends(require("operator")),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    import hashlib

    key = storage.put(user.tenant_id, file.filename or "untitled", data)
    doc = Document(
        tenant_id=user.tenant_id,
        user_id=user.id,
        filename=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        storage_key=key,
        checksum=hashlib.sha256(data).hexdigest(),
        status="uploaded",
        tags=[],
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return process_document(
        db,
        doc,
        enable_ocr=enable_ocr,
        enable_workflow=enable_workflow,
        enable_notification=enable_notification,
        enable_analytics=enable_analytics,
        workflow_id=workflow_id,
    )


@router.get("/logs")
def logs(user: User = Depends(current_user), db: Session = Depends(get_db), limit: int = 80):
    q = db.query(AgentLog)
    if user.role != "platform_admin":
        q = q.filter((AgentLog.tenant_id == user.tenant_id) | (AgentLog.tenant_id.is_(None)))
    rows = q.order_by(AgentLog.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "agent_role": r.agent_role,
            "action": r.action,
            "model_used": r.model_used,
            "status": r.status,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/skills")
def skills(_user: User = Depends(current_user)):
    return load_skills()


@router.post("/skills/{skill_id}/run")
def run_skill(skill_id: str, prompt: str, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    skill = get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    gen = generate(skill_id, f"{skill['instructions']}\n\nUSER:\n{prompt}")
    db.add(
        AgentLog(
            tenant_id=user.tenant_id,
            agent_role=skill_id,
            action="run_skill",
            model_used=gen.get("model", "heuristic"),
            status="success",
            summary=gen["text"][:500],
        )
    )
    db.commit()
    return {"skill": skill_id, "result": gen["text"], "provider": gen.get("provider")}
