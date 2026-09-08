from sqlalchemy.orm import Session

from app.models import AccessGrant, LayerMember, User

RANK = {"view": 1, "fill": 2, "edit": 3, "manage": 4}


def layer_ids_for(db: Session, user: User) -> list[int]:
    return [m.layer_id for m in db.query(LayerMember).filter(LayerMember.user_id == user.id).all()]


def has_grant(db: Session, user: User, resource_type: str, resource_id: int, need: str = "view") -> bool:
    if user.role in ("platform_admin", "owner", "admin"):
        return True
    needed = RANK.get(need, 1)
    lids = layer_ids_for(db, user)
    grants = (
        db.query(AccessGrant)
        .filter(
            AccessGrant.tenant_id == user.tenant_id,
            AccessGrant.resource_type == resource_type,
            AccessGrant.resource_id == resource_id,
        )
        .all()
    )
    for g in grants:
        if RANK.get(g.permission, 0) < needed:
            continue
        if g.principal_type == "user" and g.principal_id == user.id:
            return True
        if g.principal_type == "layer" and g.principal_id in lids:
            return True
    return False
