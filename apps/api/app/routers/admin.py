from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require
from app.engine.rag import (
    RAG_MIN_SCORE_DEFAULT,
    RAG_MIN_SCORE_FORM_COMPOSE,
    SOURCE_KIND_FLAGS,
    enabled_source_kinds,
    rag_master_enabled,
)
from app.llm import ollama_status
from app.models import Connector, Document, FeatureFlag, KnowledgeChunk, ModelBinding, Tenant, User, WorkflowRun
from app.schemas import UserOut
from app.security import hash_password

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "operator"
    tenant_id: int | None = None


class ChunkTagsIn(BaseModel):
    tags: list[str] = Field(default_factory=list)


def _normalize_tags(tags: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        t = (raw or "").strip().lower()[:64]
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:40]


@router.get("/stats")
def stats(user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    if user.role == "platform_admin":
        return {
            "tenants": db.query(Tenant).count(),
            "users": db.query(User).count(),
            "documents": db.query(Document).count(),
            "runs": db.query(WorkflowRun).count(),
            "plans": [
                {"plan": p, "count": n}
                for p, n in db.query(Tenant.plan, func.count(Tenant.id)).group_by(Tenant.plan).all()
            ],
        }
    return {
        "tenants": 1,
        "users": db.query(User).filter(User.tenant_id == user.tenant_id).count(),
        "documents": db.query(Document).filter(Document.tenant_id == user.tenant_id).count(),
        "runs": db.query(WorkflowRun).filter(WorkflowRun.tenant_id == user.tenant_id).count(),
    }


@router.get("/users", response_model=list[UserOut])
def users(user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    q = db.query(User)
    if user.role != "platform_admin":
        q = q.filter(User.tenant_id == user.tenant_id)
    return q.order_by(User.id.asc()).all()


@router.post("/users", response_model=UserOut)
def create_user(body: UserCreate, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    tid = body.tenant_id or user.tenant_id
    if user.role != "platform_admin":
        tid = user.tenant_id
        if body.role == "platform_admin":
            raise HTTPException(403, "Cannot create platform admin")
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(409, "Email exists")
    u = User(
        email=body.email.lower(),
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=body.role,
        tenant_id=tid,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.post("/users/{user_id}/block")
def block_user(user_id: int, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target or (user.role != "platform_admin" and target.tenant_id != user.tenant_id):
        raise HTTPException(404, "User not found")
    target.is_blocked = not target.is_blocked
    db.commit()
    return {"id": target.id, "is_blocked": target.is_blocked}


@router.get("/tenants")
def tenants(user: User = Depends(require("platform_admin")), db: Session = Depends(get_db)):
    rows = db.query(Tenant).order_by(Tenant.id.asc()).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "plan": t.plan,
            "is_active": t.is_active,
            "is_suspended": t.is_suspended,
            "users": db.query(User).filter(User.tenant_id == t.id).count(),
        }
        for t in rows
    ]


@router.post("/tenants/{tenant_id}/suspend")
def suspend(tenant_id: int, user: User = Depends(require("platform_admin")), db: Session = Depends(get_db)):
    t = db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(404, "Tenant not found")
    t.is_suspended = not t.is_suspended
    db.commit()
    return {"id": t.id, "is_suspended": t.is_suspended}


@router.get("/flags")
def flags(_user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    return [{"key": f.key, "enabled": f.enabled, "description": f.description} for f in db.query(FeatureFlag).all()]


@router.post("/flags/{key}/toggle")
def toggle_flag(key: str, _user: User = Depends(require("platform_admin")), db: Session = Depends(get_db)):
    f = db.query(FeatureFlag).filter(FeatureFlag.key == key).first()
    if not f:
        raise HTTPException(404, "Flag not found")
    f.enabled = not f.enabled
    db.commit()
    return {"key": f.key, "enabled": f.enabled}


@router.get("/models")
def models(_user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    return [{"role": m.agent_role, "model": m.model_name, "provider": m.provider} for m in db.query(ModelBinding).all()]


@router.put("/models/{role}")
def set_model(role: str, model: str, provider: str = "heuristic", _user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    row = db.query(ModelBinding).filter(ModelBinding.agent_role == role).first()
    if not row:
        row = ModelBinding(agent_role=role, model_name=model, provider=provider)
        db.add(row)
    else:
        row.model_name = model
        row.provider = provider
    db.commit()
    return {"role": role, "model": model, "provider": provider}


@router.get("/health")
def health(db: Session = Depends(get_db), _user: User = Depends(require("admin"))):
    return {
        "api": "ok",
        "database": "ok",
        "users": db.query(User).count(),
        "documents": db.query(Document).count(),
        "ollama": ollama_status(),
    }


@router.get("/rag/sources")
def rag_sources(user: User = Depends(require("platform_admin")), db: Session = Depends(get_db)):
    """Cross-tenant connector / source inventory for platform RAG control."""
    tenants = {t.id: t for t in db.query(Tenant).all()}
    kinds_on = enabled_source_kinds(db)
    rows = db.query(Connector).order_by(Connector.tenant_id.asc(), Connector.id.asc()).all()
    out = []
    for c in rows:
        chunk_count = (
            db.query(KnowledgeChunk)
            .filter(KnowledgeChunk.tenant_id == c.tenant_id, KnowledgeChunk.source_type == c.kind)
            .count()
        )
        tenant = tenants.get(c.tenant_id)
        out.append(
            {
                "id": c.id,
                "tenant_id": c.tenant_id,
                "tenant_name": tenant.name if tenant else f"tenant:{c.tenant_id}",
                "kind": c.kind,
                "name": c.name,
                "status": c.status,
                "enabled": c.status != "disabled",
                "kind_enabled": c.kind in kinds_on,
                "file_count": c.file_count,
                "chunk_count": chunk_count,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            }
        )
    # Also summarize OCR / orphan knowledge source types with no connector row.
    for kind, count in (
        db.query(KnowledgeChunk.source_type, func.count(KnowledgeChunk.id))
        .group_by(KnowledgeChunk.source_type)
        .all()
    ):
        if any(r["kind"] == kind for r in out):
            continue
        out.append(
            {
                "id": None,
                "tenant_id": None,
                "tenant_name": "(all tenants)",
                "kind": kind,
                "name": f"{kind} knowledge",
                "status": "library",
                "enabled": kind in kinds_on,
                "kind_enabled": kind in kinds_on,
                "file_count": count,
                "chunk_count": count,
                "last_sync_at": None,
            }
        )
    return {
        "rag_enabled": rag_master_enabled(db),
        "sources": out,
        "connectors_href": "/app/connectors",
    }


@router.post("/rag/sources/{connector_id}/toggle")
def rag_source_toggle(connector_id: int, user: User = Depends(require("platform_admin")), db: Session = Depends(get_db)):
    c = db.get(Connector, connector_id)
    if not c:
        raise HTTPException(404, "Connector not found")
    c.status = "connected" if c.status == "disabled" else "disabled"
    db.commit()
    return {"id": c.id, "status": c.status, "enabled": c.status != "disabled"}


@router.get("/rag/chunks")
def rag_chunks(
    user: User = Depends(require("platform_admin")),
    db: Session = Depends(get_db),
    tenant_id: int | None = None,
    source_type: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    limit: int = 100,
):
    limit = max(1, min(limit, 500))
    query = db.query(KnowledgeChunk)
    if tenant_id is not None:
        query = query.filter(KnowledgeChunk.tenant_id == tenant_id)
    if source_type:
        query = query.filter(KnowledgeChunk.source_type == source_type)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter((KnowledgeChunk.title.ilike(like)) | (KnowledgeChunk.text.ilike(like)))
    rows = query.order_by(KnowledgeChunk.id.desc()).limit(limit).all()
    tenants = {t.id: t.name for t in db.query(Tenant).all()}
    items = []
    needle = (tag or "").strip().lower()
    for r in rows:
        tags = list(r.tags or [])
        if needle and needle not in [t.lower() for t in tags]:
            continue
        items.append(
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "tenant_name": tenants.get(r.tenant_id, f"tenant:{r.tenant_id}"),
                "source_type": r.source_type,
                "source_id": r.source_id,
                "title": r.title,
                "text_preview": (r.text or "")[:240],
                "locale": r.locale,
                "tags": tags,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return {"chunks": items, "count": len(items)}


@router.patch("/rag/chunks/{chunk_id}/tags")
def rag_chunk_tags(chunk_id: int, body: ChunkTagsIn, user: User = Depends(require("platform_admin")), db: Session = Depends(get_db)):
    row = db.get(KnowledgeChunk, chunk_id)
    if not row:
        raise HTTPException(404, "Chunk not found")
    row.tags = _normalize_tags(body.tags)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "tags": list(row.tags or [])}


@router.get("/rag/settings")
def rag_settings(user: User = Depends(require("platform_admin")), db: Session = Depends(get_db)):
    from app.seed import ensure_rag_flags

    ensure_rag_flags(db)
    flags = (
        db.query(FeatureFlag)
        .filter((FeatureFlag.key == "rag") | (FeatureFlag.key.like("rag_%")))
        .order_by(FeatureFlag.key.asc())
        .all()
    )
    return {
        "rag_enabled": rag_master_enabled(db),
        "enabled_source_kinds": sorted(enabled_source_kinds(db)),
        "source_kind_flags": SOURCE_KIND_FLAGS,
        "min_score": {
            "default": RAG_MIN_SCORE_DEFAULT,
            "form_compose": RAG_MIN_SCORE_FORM_COMPOSE,
            "notes": (
                "Token overlap floor in retrieve(). Default=1 for general retrieval; "
                "form compose uses min_score=3 and disables field fallback so chat stays on real knowledge."
            ),
        },
        "flags": [{"key": f.key, "enabled": f.enabled, "description": f.description} for f in flags],
        "connectors_href": "/app/connectors",
        "tenant_note": "Tenant operators sync files on Connectors; this page is platform-wide RAG control.",
    }
