from fastapi import APIRouter

from app.config import get_settings
from app.engine.skills import load_skills

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/health/")
@router.get("/ready")
def health():
    s = get_settings()
    return {
        "status": "healthy",
        "service": s.app_name,
        "version": s.app_version,
        "environment": s.environment,
        "cloud_provider": s.cloud_provider,
        "skills": len(load_skills()),
    }
