from datetime import datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()
ROLES = ("platform_admin", "owner", "admin", "operator", "viewer")
ROLE_RANK = {r: i for i, r in enumerate(reversed(ROLES))}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(subject: str, extra: dict[str, Any] | None = None, minutes: int | None = None) -> str:
    payload = {
        "sub": subject,
        "exp": datetime.utcnow() + timedelta(minutes=minutes or settings.access_token_expire_minutes),
        "iat": datetime.utcnow(),
        **(extra or {}),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def has_at_least(role: str, required: str) -> bool:
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(required, 0)
