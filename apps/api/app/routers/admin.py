from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require
from app.llm import ollama_status
from app.models import Document, FeatureFlag, ModelBinding, Tenant, User, WorkflowRun
from app.schemas import UserOut
from app.security import hash_password

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "operator"
    tenant_id: int | None = None


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
