from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require
from app.engine.workflow import execute_workflow
from app.models import Document, User, Workflow, WorkflowRun, WorkflowStepRun
from app.schemas import WorkflowIn

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


def _scope(db: Session, user: User):
    q = db.query(Workflow)
    if user.role != "platform_admin":
        q = q.filter(Workflow.tenant_id == user.tenant_id)
    return q


@router.get("")
def list_workflows(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = _scope(db, user).order_by(Workflow.id.desc()).all()
    return [_out(w) for w in rows]


@router.post("")
def create_workflow(body: WorkflowIn, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    wf = Workflow(
        tenant_id=user.tenant_id,
        name=body.name,
        description=body.description,
        trigger=body.trigger,
        is_active=body.is_active,
        definition={"steps": [s.model_dump() for s in body.steps]},
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return _out(wf)


@router.get("/{workflow_id}")
def get_workflow(workflow_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    wf = _scope(db, user).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return _out(wf)


@router.put("/{workflow_id}")
def update_workflow(workflow_id: int, body: WorkflowIn, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    wf = _scope(db, user).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(404, "Workflow not found")
    wf.name = body.name
    wf.description = body.description
    wf.trigger = body.trigger
    wf.is_active = body.is_active
    wf.definition = {"steps": [s.model_dump() for s in body.steps]}
    db.commit()
    return _out(wf)


@router.post("/{workflow_id}/execute")
def run_workflow(workflow_id: int, document_id: int, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    wf = _scope(db, user).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(404, "Workflow not found")
    doc = db.get(Document, document_id)
    if not doc or (user.role != "platform_admin" and doc.tenant_id != user.tenant_id):
        raise HTTPException(404, "Document not found")
    run = execute_workflow(db, wf, doc)
    db.commit()
    return _run_out(db, run)


@router.get("/runs/recent")
def recent_runs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(WorkflowRun)
    if user.role != "platform_admin":
        q = q.filter(WorkflowRun.tenant_id == user.tenant_id)
    runs = q.order_by(WorkflowRun.id.desc()).limit(50).all()
    return [_run_out(db, r) for r in runs]


@router.get("/runs/{run_id}")
def get_run(run_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    run = db.get(WorkflowRun, run_id)
    if not run or (user.role != "platform_admin" and run.tenant_id != user.tenant_id):
        raise HTTPException(404, "Run not found")
    return _run_out(db, run)


def _out(wf: Workflow) -> dict:
    return {
        "id": wf.id,
        "tenant_id": wf.tenant_id,
        "name": wf.name,
        "description": wf.description,
        "trigger": wf.trigger,
        "is_active": wf.is_active,
        "steps": (wf.definition or {}).get("steps") or [],
        "created_at": wf.created_at.isoformat() if wf.created_at else None,
    }


def _run_out(db: Session, run: WorkflowRun) -> dict:
    steps = db.query(WorkflowStepRun).filter(WorkflowStepRun.run_id == run.id).order_by(WorkflowStepRun.id.asc()).all()
    wf = db.get(Workflow, run.workflow_id)
    return {
        "id": run.id,
        "workflow_id": run.workflow_id,
        "workflow_name": wf.name if wf else None,
        "document_id": run.document_id,
        "status": run.status,
        "current_step": run.current_step,
        "output": run.output,
        "error": run.error,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "steps": [
            {
                "key": s.step_key,
                "type": s.step_type,
                "status": s.status,
                "output": s.output,
                "error": s.error,
            }
            for s in steps
        ],
    }
