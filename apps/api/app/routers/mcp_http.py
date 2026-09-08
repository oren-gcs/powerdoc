from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.engine.skills import load_skills
from app.models import Document, User, Workflow

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


@router.get("/manifest")
def manifest(_: User = Depends(current_user)):
    return {
        "name": "docflow",
        "version": "2.0.0",
        "tools": [
            "health",
            "list_documents",
            "list_workflows",
            "list_skills",
            "platform_stats",
        ],
    }


@router.get("/snapshot")
def snapshot(user: User = Depends(current_user), db: Session = Depends(get_db)):
    qdocs = db.query(Document)
    qw = db.query(Workflow)
    if user.role != "platform_admin":
        qdocs = qdocs.filter(Document.tenant_id == user.tenant_id)
        qw = qw.filter(Workflow.tenant_id == user.tenant_id)
    return {
        "tenant_id": user.tenant_id,
        "documents": qdocs.count(),
        "workflows": qw.count(),
        "skills": [s["id"] for s in load_skills()],
    }
