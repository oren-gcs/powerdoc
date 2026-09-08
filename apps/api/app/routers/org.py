from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require
from app.models import AccessGrant, Folder, Layer, LayerMember, User
from app.security import hash_password

router = APIRouter(prefix="/api/v1/org", tags=["organization"])


class LayerIn(BaseModel):
    name: str
    kind: str = "team"
    parent_id: int | None = None
    locale: str = "en"


class MemberIn(BaseModel):
    user_id: int | None = None
    email: str | None = None
    full_name: str | None = None
    password: str = "DocFlow!2026"
    role: str = "viewer"
    title: str = "member"
    can_manage: bool = False


class GrantIn(BaseModel):
    principal_type: str
    principal_id: int
    resource_type: str
    resource_id: int
    permission: str = "view"


class FolderIn(BaseModel):
    name: str
    kind: str = "files"
    layer_id: int | None = None
    parent_id: int | None = None


def _tid(user: User) -> int:
    return user.tenant_id


@router.get("/tree")
def tree(user: User = Depends(current_user), db: Session = Depends(get_db)):
    layers = db.query(Layer).filter(Layer.tenant_id == _tid(user)).order_by(Layer.id.asc()).all()
    folders = db.query(Folder).filter(Folder.tenant_id == _tid(user)).all()
    members = db.query(LayerMember).all()
    users = {u.id: u for u in db.query(User).filter(User.tenant_id == _tid(user)).all()}
    grants = db.query(AccessGrant).filter(AccessGrant.tenant_id == _tid(user)).all()
    by_layer: dict[int, list] = {}
    for m in members:
        u = users.get(m.user_id)
        by_layer.setdefault(m.layer_id, []).append(
            {
                "membership_id": m.id,
                "user_id": m.user_id,
                "title": m.title,
                "can_manage": m.can_manage,
                "email": u.email if u else "",
                "full_name": u.full_name if u else "",
                "role": u.role if u else "",
            }
        )
    return {
        "layers": [
            {
                "id": l.id,
                "parent_id": l.parent_id,
                "name": l.name,
                "kind": l.kind,
                "locale": l.locale,
                "members": by_layer.get(l.id, []),
            }
            for l in layers
        ],
        "folders": [{"id": f.id, "parent_id": f.parent_id, "layer_id": f.layer_id, "name": f.name, "kind": f.kind} for f in folders],
        "grants": [
            {
                "id": g.id,
                "principal_type": g.principal_type,
                "principal_id": g.principal_id,
                "resource_type": g.resource_type,
                "resource_id": g.resource_id,
                "permission": g.permission,
            }
            for g in grants
        ],
        "users": [
            {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "locale": getattr(u, "locale", "en")}
            for u in users.values()
        ],
    }


@router.post("/layers")
def create_layer(body: LayerIn, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    row = Layer(tenant_id=_tid(user), name=body.name, kind=body.kind, parent_id=body.parent_id, locale=body.locale)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "kind": row.kind, "parent_id": row.parent_id}


@router.post("/layers/{layer_id}/members")
def add_member(layer_id: int, body: MemberIn, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    layer = db.get(Layer, layer_id)
    if not layer or layer.tenant_id != _tid(user):
        raise HTTPException(404, "Layer not found")
    target = db.get(User, body.user_id) if body.user_id else None
    if not target and body.email:
        target = db.query(User).filter(User.email == body.email.lower()).first()
        if not target:
            target = User(
                email=body.email.lower(),
                full_name=body.full_name or body.email.split("@")[0],
                hashed_password=hash_password(body.password),
                role=body.role,
                tenant_id=_tid(user),
            )
            db.add(target)
            db.flush()
    if not target:
        raise HTTPException(400, "Need user_id or email")
    existing = db.query(LayerMember).filter(LayerMember.layer_id == layer_id, LayerMember.user_id == target.id).first()
    if existing:
        existing.title = body.title
        existing.can_manage = body.can_manage
    else:
        db.add(LayerMember(layer_id=layer_id, user_id=target.id, title=body.title, can_manage=body.can_manage))
    db.commit()
    return {"ok": True, "user_id": target.id}


@router.post("/folders")
def create_folder(body: FolderIn, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    row = Folder(tenant_id=_tid(user), name=body.name, kind=body.kind, layer_id=body.layer_id, parent_id=body.parent_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "kind": row.kind}


@router.post("/grants")
def grant(body: GrantIn, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    row = AccessGrant(
        tenant_id=_tid(user),
        principal_type=body.principal_type,
        principal_id=body.principal_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        permission=body.permission,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}


@router.delete("/grants/{grant_id}")
def revoke(grant_id: int, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    row = db.get(AccessGrant, grant_id)
    if row and row.tenant_id == _tid(user):
        db.delete(row)
        db.commit()
    return {"ok": True}
