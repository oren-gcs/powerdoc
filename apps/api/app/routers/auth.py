from datetime import datetime, timedelta
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import current_user
from app.models import Activity, RefreshToken, Tenant, User
from app.schemas import LoginIn, RegisterIn, TokenPair, UserOut
from app.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _slugify(name: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    return slug[:70] or "org"


def _issue(db: Session, user: User) -> TokenPair:
    access = create_token(user.email, extra={"uid": user.id, "tid": user.tenant_id, "role": user.role})
    refresh = token_urlsafe(32)
    db.add(
        RefreshToken(
            user_id=user.id,
            token=refresh,
            expires_at=datetime.utcnow() + timedelta(days=get_settings().refresh_token_expire_days),
        )
    )
    user.last_login_at = datetime.utcnow()
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=TokenPair)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    slug = _slugify(body.organization)
    existing = db.query(Tenant).filter(Tenant.slug == slug).first()
    if existing:
        slug = f"{slug}-{token_urlsafe(3).lower()}"
    tenant = Tenant(name=body.organization, slug=slug, plan="growth")
    db.add(tenant)
    db.flush()
    user = User(
        email=body.email.lower(),
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role="owner",
        tenant_id=tenant.id,
    )
    db.add(user)
    db.flush()
    db.add(Activity(tenant_id=tenant.id, user_id=user.id, activity_type="tenant_created", details={"name": tenant.name}))
    return _issue(db, user)


@router.post("/login", response_model=TokenPair)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active or user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    tenant = db.get(Tenant, user.tenant_id)
    if tenant and (not tenant.is_active or tenant.is_suspended):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organization suspended")
    db.add(Activity(tenant_id=user.tenant_id, user_id=user.id, activity_type="login", details={}))
    return _issue(db, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    row = db.query(RefreshToken).filter(RefreshToken.token == refresh_token, RefreshToken.revoked.is_(False)).first()
    if not row or row.expires_at < datetime.utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User gone")
    row.revoked = True
    return _issue(db, user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
