from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.models import Automation, Connector, Document, Form, User, Workflow

router = APIRouter(prefix="/api/v1/search", tags=["search"])

LIMIT_PER_KIND = 8


def _scoped(query, model, user: User):
    if user.role != "platform_admin":
        query = query.filter(model.tenant_id == user.tenant_id)
    return query


@router.get("")
def search(
    q: str = Query("", min_length=0, max_length=120),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Find forms, workflows/processes, documents, and connectors by name."""
    needle = (q or "").strip()
    if len(needle) < 1:
        return {"q": needle, "results": []}

    pattern = f"%{needle}%"
    results: list[dict] = []

    forms = (
        _scoped(db.query(Form), Form, user)
        .filter(or_(Form.name.ilike(pattern), Form.topic.ilike(pattern)))
        .order_by(Form.id.desc())
        .limit(LIMIT_PER_KIND)
        .all()
    )
    for f in forms:
        results.append(
            {
                "kind": "form",
                "id": f.id,
                "name": f.name,
                "subtitle": f.topic or f.status,
                "href": f"/app/forms/{f.id}",
            }
        )

    workflows = (
        _scoped(db.query(Workflow), Workflow, user)
        .filter(Workflow.name.ilike(pattern))
        .order_by(Workflow.id.desc())
        .limit(LIMIT_PER_KIND)
        .all()
    )
    for w in workflows:
        results.append(
            {
                "kind": "workflow",
                "id": w.id,
                "name": w.name,
                "subtitle": w.trigger or "process",
                "href": "/app/workflows",
            }
        )

    automations = (
        _scoped(db.query(Automation), Automation, user)
        .filter(Automation.name.ilike(pattern))
        .order_by(Automation.id.desc())
        .limit(LIMIT_PER_KIND)
        .all()
    )
    for a in automations:
        results.append(
            {
                "kind": "process",
                "id": a.id,
                "name": a.name,
                "subtitle": a.trigger_type or "automation",
                "href": "/app/automations",
            }
        )

    documents = (
        _scoped(db.query(Document), Document, user)
        .filter(Document.filename.ilike(pattern))
        .order_by(Document.id.desc())
        .limit(LIMIT_PER_KIND)
        .all()
    )
    for d in documents:
        results.append(
            {
                "kind": "document",
                "id": d.id,
                "name": d.filename,
                "subtitle": d.classification or d.status,
                "href": f"/app/documents/{d.id}",
            }
        )

    connectors = (
        _scoped(db.query(Connector), Connector, user)
        .filter(or_(Connector.name.ilike(pattern), Connector.kind.ilike(pattern)))
        .order_by(Connector.id.desc())
        .limit(LIMIT_PER_KIND)
        .all()
    )
    for c in connectors:
        results.append(
            {
                "kind": "connector",
                "id": c.id,
                "name": c.name,
                "subtitle": c.kind,
                "href": "/app/connectors",
            }
        )

    return {"q": needle, "results": results}
