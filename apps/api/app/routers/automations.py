from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require
from app.models import Automation, User, Workflow
from app.schemas import AutomationIn

router = APIRouter(prefix="/api/v1/automations", tags=["automations"])


@router.get("")
def list_automations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Automation)
    if user.role != "platform_admin":
        q = q.filter(Automation.tenant_id == user.tenant_id)
    rows = q.order_by(Automation.id.desc()).all()
    return [_out(a) for a in rows]


@router.post("")
def create_automation(body: AutomationIn, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    wf = db.get(Workflow, body.workflow_id)
    if not wf or (user.role != "platform_admin" and wf.tenant_id != user.tenant_id):
        raise HTTPException(404, "Workflow not found")
    a = Automation(
        tenant_id=user.tenant_id,
        name=body.name,
        trigger_type=body.trigger_type,
        trigger_config=body.trigger_config,
        workflow_id=body.workflow_id,
        is_active=body.is_active,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _out(a)


@router.post("/{automation_id}/toggle")
def toggle(automation_id: int, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    a = db.get(Automation, automation_id)
    if not a or (user.role != "platform_admin" and a.tenant_id != user.tenant_id):
        raise HTTPException(404, "Automation not found")
    a.is_active = not a.is_active
    db.commit()
    return _out(a)


def _out(a: Automation) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "trigger_type": a.trigger_type,
        "trigger_config": a.trigger_config,
        "workflow_id": a.workflow_id,
        "is_active": a.is_active,
        "fire_count": a.fire_count,
        "last_fired_at": a.last_fired_at.isoformat() if a.last_fired_at else None,
    }
