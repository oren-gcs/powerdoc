from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.migrate import ensure_sqlite_columns
from app.routers import (
    admin,
    agents,
    analytics,
    auth,
    automations,
    connectors,
    documents,
    forms,
    health,
    mcp_http,
    notify,
    org,
    search,
    workflows,
)
from app.seed import ensure_rag_flags, seed_extensions, seed_if_needed
from app.service_catalog import SERVICES, resolve_service_name

settings = get_settings()
SERVICE = resolve_service_name(settings.docflow_service)

ROUTER_MAP = {
    "auth": auth.router,
    "org": org.router,
    "admin": admin.router,
    "documents": documents.router,
    "search": search.router,
    "connectors": connectors.router,
    "agents": agents.router,
    "mcp_http": mcp_http.router,
    "forms": forms.router,
    "forms_public": forms.public,
    "workflows": workflows.router,
    "automations": automations.router,
    "notify": notify.router,
    "analytics": analytics.router,
}


def _should_seed() -> bool:
    if SERVICE == "monolith":
        return True
    spec = SERVICES.get(SERVICE)
    return bool(spec and spec.runs_seed)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if SERVICE != "gateway":
        Base.metadata.create_all(bind=engine)
        ensure_sqlite_columns(engine)
        db = SessionLocal()
        try:
            if settings.seed_demo and _should_seed():
                seed_if_needed(db)
                seed_extensions(db)
            ensure_rag_flags(db)
        finally:
            db.close()
    yield


title = "DocFlow API" if SERVICE == "monolith" else f"DocFlow · {SERVICE}"
app = FastAPI(title=title, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)

if SERVICE == "gateway":
    from app.gateway import router as gateway_router

    app.include_router(gateway_router)
elif SERVICE == "monolith":
    for key in ROUTER_MAP:
        app.include_router(ROUTER_MAP[key])
else:
    for key in SERVICES[SERVICE].routers:
        app.include_router(ROUTER_MAP[key])


@app.get("/")
def root():
    return {
        "name": "DocFlow",
        "service": SERVICE,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
