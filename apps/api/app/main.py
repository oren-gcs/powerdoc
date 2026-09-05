from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.migrate import ensure_sqlite_columns
from app.routers import admin, agents, analytics, auth, automations, connectors, documents, forms, health, mcp_http, org, workflows
from app.seed import seed_extensions, seed_if_needed

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_columns(engine)
    if settings.seed_demo:
        db = SessionLocal()
        try:
            seed_if_needed(db)
            seed_extensions(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="DocFlow API",
    version=settings.app_version,
    description="Production document intelligence platform — successor to Doc-Power.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(workflows.router)
app.include_router(automations.router)
app.include_router(agents.router)
app.include_router(analytics.router)
app.include_router(admin.router)
app.include_router(org.router)
app.include_router(forms.router)
app.include_router(forms.public)
app.include_router(connectors.router)
app.include_router(mcp_http.router)


@app.get("/")
def root():
    return {
        "name": "DocFlow",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
