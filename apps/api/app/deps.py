from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import decode_token, has_at_least

bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> User:
    token = creds.credentials if creds else None
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_token(token)
    except InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, int(payload.get("uid", 0)))
    if not user or not user.is_active or user.is_blocked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User unavailable")
    if x_user_id and str(user.id) != x_user_id and user.role != "platform_admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Impersonation denied")
    return user


def require(*roles: str):
    def _inner(user: User = Depends(current_user)) -> User:
        if user.role == "platform_admin":
            return user
        if roles and not any(has_at_least(user.role, r) for r in roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return _inner
