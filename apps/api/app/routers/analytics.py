from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.llm import generate
from app.models import Activity, Document, Notification, User, WorkflowRun

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/summary")
def summary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    tid = None if user.role == "platform_admin" else user.tenant_id

    def scoped(model):
        q = db.query(model)
        if tid is not None and hasattr(model, "tenant_id"):
            q = q.filter(model.tenant_id == tid)
        return q

    docs = scoped(Document).count()
    ready = scoped(Document).filter(Document.status == "ready").count()
    failed = scoped(Document).filter(Document.status == "failed").count()
    runs = scoped(WorkflowRun).count()
    completed_runs = scoped(WorkflowRun).filter(WorkflowRun.status == "completed").count()
    classes = (
        scoped(Document)
        .with_entities(Document.classification, func.count(Document.id))
        .group_by(Document.classification)
        .all()
    )
    since = datetime.utcnow() - timedelta(days=14)
    acts = scoped(Activity).filter(Activity.created_at >= since).all()
    bucket: dict[str, int] = {}
    for row in acts:
        if row.created_at:
            key = row.created_at.strftime("%Y-%m-%d")
            bucket[key] = bucket.get(key, 0) + 1
    daily = sorted(bucket.items())
    digest = generate(
        "analytics",
        f"Docs={docs} ready={ready} failed={failed} runs={runs} classes={dict(classes)}",
    )
    return {
        "documents": docs,
        "ready": ready,
        "failed": failed,
        "workflow_runs": runs,
        "completed_runs": completed_runs,
        "success_rate": round((completed_runs / runs) * 100, 1) if runs else 100.0,
        "by_class": [{"label": c or "unclassified", "count": n} for c, n in classes],
        "activity_daily": [{"day": d, "count": n} for d, n in daily],
        "digest": digest["text"],
    }


@router.get("/activity")
def activity(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Activity)
    if user.role != "platform_admin":
        q = q.filter(Activity.tenant_id == user.tenant_id)
    rows = q.order_by(Activity.id.desc()).limit(80).all()
    return [
        {
            "id": r.id,
            "type": r.activity_type,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Notification).filter(Notification.tenant_id == user.tenant_id)
    rows = q.order_by(Notification.id.desc()).limit(50).all()
    return [
        {
            "id": n.id,
            "channel": n.channel,
            "subject": n.subject,
            "body": n.body,
            "status": n.status,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@router.post("/notifications/{nid}/read")
def mark_read(nid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, nid)
    if n and n.tenant_id == user.tenant_id:
        n.status = "read"
        db.commit()
    return {"ok": True}
